<?php

namespace App\Http\Controllers;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Inertia\Inertia;
use Inertia\Response;

/**
 * HealthController — unified pipeline health dashboard (B6).
 *
 * One screen answering "is the whole pipeline alive?": Postgres, Curator API,
 * Messor API, RabbitMQ (+ key queue depths) and the last harvest.
 *
 * Read-only observability — accessible to ALL authenticated roles (no `role`
 * middleware in routes/web.php). It performs no mutations and exposes no
 * secrets: each component is built server-side and only statuses / metrics /
 * queue depths reach the client. RabbitMQ credentials and the authenticated
 * management URL stay in config and never enter the Inertia props.
 *
 * Every external call is independently DEFENSIVE: a short ~2s timeout plus a
 * try/catch so a single down/slow service degrades to status `down` /
 * `unreachable` rather than throwing a 500 or hanging the page. Postgres reads
 * are cross-schema (ADR-0003, read-only) and likewise wrapped.
 */
class HealthController extends Controller
{
    /** Per-component external call budget (seconds). Keeps the page snappy. */
    private const TIMEOUT = 2;

    /**
     * Messor gets a more generous budget. It's a single uvicorn process that
     * shares the GIL with its scraping threads, so during an active harvest
     * (now frequent: the 5-min breaking pulse + the cycle, Messor ADR-0017)
     * even a trivial health route can take >2s to get CPU. A short timeout made
     * the dashboard flap to "unreachable" mid-scrape even though harvesting was
     * healthy. 6s rides over those windows without making the page sluggish.
     */
    private const MESSOR_TIMEOUT = 6;

    /** Queues we care about for the Messor -> Curator pipeline. */
    private const KEY_QUEUES = [
        'curator.articles-scraped',
        'articles-scraped',
        'curator.commands',
    ];

    public function index(): Response
    {
        $postgres = $this->postgres();

        return Inertia::render('Health/Index', [
            'health' => [
                'postgres' => $postgres,
                'curator' => $this->curator(),
                'messor' => $this->messor(),
                'rabbitmq' => $this->rabbitmq(),
                'last_harvest' => $postgres['last_harvest'] ?? null,
                'checked_at' => now()->toIso8601String(),
            ],
        ]);
    }

    /**
     * Postgres: connectivity + pipeline counts + last harvest. Cross-schema
     * reads of Curator's `public.*` are allowed read-only (ADR-0003).
     *
     * @return array<string, mixed>
     */
    private function postgres(): array
    {
        $started = microtime(true);

        try {
            $counts = [
                'articles' => (int) DB::scalar('SELECT count(*) FROM public.articles'),
                'enriched' => (int) DB::scalar('SELECT count(*) FROM public.articles WHERE enriched_at IS NOT NULL'),
                'events' => (int) DB::scalar('SELECT count(*) FROM public.events'),
                'pages' => (int) DB::scalar('SELECT count(*) FROM public.pages'),
                'pages_published' => (int) DB::scalar('SELECT count(*) FROM public.pages WHERE published_at IS NOT NULL'),
            ];

            return [
                'status' => 'up',
                'latency_ms' => $this->elapsedMs($started),
                'counts' => $counts,
                'last_harvest' => DB::scalar('SELECT MAX(scraped_at) FROM public.articles'),
            ];
        } catch (\Throwable $e) {
            return [
                'status' => 'down',
                'latency_ms' => $this->elapsedMs($started),
                'error' => 'Postgres unreachable',
            ];
        }
    }

    /**
     * Curator FastAPI: GET /status (200 JSON) with a /healthz fallback.
     *
     * @return array<string, mixed>
     */
    private function curator(): array
    {
        $base = rtrim((string) config('services.curator.url'), '/');
        $started = microtime(true);

        try {
            $response = Http::timeout(self::TIMEOUT)->acceptJson()->get($base.'/status');

            if (! $response->successful()) {
                return [
                    'status' => 'down',
                    'latency_ms' => $this->elapsedMs($started),
                    'error' => "HTTP {$response->status()}",
                ];
            }

            $json = $response->json() ?? [];

            return [
                'status' => 'up',
                'latency_ms' => $this->elapsedMs($started),
                'metrics' => [
                    'articles_total' => $json['articles_total'] ?? null,
                    'events_total' => $json['events_total'] ?? null,
                    'pages_published' => $json['pages_published'] ?? null,
                ],
            ];
        } catch (\Throwable $e) {
            return [
                'status' => 'unreachable',
                'latency_ms' => $this->elapsedMs($started),
                'error' => 'Curator unreachable',
            ];
        }
    }

    /**
     * Messor FastAPI: no /health endpoint, so probe a cheap read
     * (GET /api/scrapesessions?page=1&limit=1 -> 200) for reachability.
     *
     * @return array<string, mixed>
     */
    private function messor(): array
    {
        $base = rtrim((string) config('services.messor.url'), '/');
        $started = microtime(true);

        try {
            // Hit the lightweight root liveness route, not /api/scrapesessions
            // (which does session work) — we only need "is the API serving?".
            $response = Http::timeout(self::MESSOR_TIMEOUT)
                ->acceptJson()
                ->get($base.'/');

            return [
                'status' => $response->successful() ? 'up' : 'down',
                'latency_ms' => $this->elapsedMs($started),
                'error' => $response->successful() ? null : "HTTP {$response->status()}",
            ];
        } catch (\Throwable $e) {
            return [
                'status' => 'unreachable',
                'latency_ms' => $this->elapsedMs($started),
                'error' => 'Messor unreachable',
            ];
        }
    }

    /**
     * RabbitMQ management API: GET /api/overview for reachability + GET
     * /api/queues for per-queue depth. Reuses the RABBITMQ_* creds via config
     * (same as CuratorCommandService); credentials are used server-side only and
     * are NOT part of the returned payload.
     *
     * @return array<string, mixed>
     */
    private function rabbitmq(): array
    {
        $cfg = config('services.curator.rabbitmq');
        $base = rtrim((string) ($cfg['management_url'] ?? ''), '/');
        $started = microtime(true);

        try {
            $overview = $this->rabbitClient($cfg)->get($base.'/api/overview');

            if (! $overview->successful()) {
                return [
                    'status' => 'down',
                    'latency_ms' => $this->elapsedMs($started),
                    'error' => "HTTP {$overview->status()}",
                    'queues' => [],
                ];
            }

            $queues = $this->rabbitClient($cfg)->get($base.'/api/queues');
            $rows = $queues->successful() ? ($queues->json() ?? []) : [];

            // Index by queue name; surface only depth for the key queues.
            $byName = [];
            foreach ($rows as $q) {
                if (isset($q['name'])) {
                    $byName[$q['name']] = (int) ($q['messages'] ?? 0);
                }
            }

            $depths = [];
            foreach (self::KEY_QUEUES as $name) {
                $depths[] = [
                    'name' => $name,
                    'messages' => $byName[$name] ?? null,
                    'present' => array_key_exists($name, $byName),
                ];
            }

            return [
                'status' => 'up',
                'latency_ms' => $this->elapsedMs($started),
                'queues' => $depths,
            ];
        } catch (\Throwable $e) {
            return [
                'status' => 'unreachable',
                'latency_ms' => $this->elapsedMs($started),
                'error' => 'RabbitMQ unreachable',
                'queues' => [],
            ];
        }
    }

    /**
     * Authenticated, short-timeout client for the RabbitMQ management API.
     * Basic-auth creds live in config and never leave the server.
     */
    private function rabbitClient(array $cfg): PendingRequest
    {
        return Http::withBasicAuth($cfg['user'] ?? '', $cfg['password'] ?? '')
            ->timeout(self::TIMEOUT)
            ->acceptJson();
    }

    /**
     * Curator pipeline live status — JSON endpoint for the admin status modal.
     *
     * Proxies Curator GET /status (which now includes synths_in_flight, LLM
     * tier, and articles_pending) and returns the full payload as JSON.
     * Defensive: returns a structured error shape if Curator is unreachable so
     * the modal can show a graceful "offline" state instead of crashing.
     */
    public function curatorPipeline(): JsonResponse
    {
        $base    = rtrim((string) config('services.curator.url'), '/');
        $started = microtime(true);

        try {
            $response = Http::timeout(self::TIMEOUT)->acceptJson()->get($base.'/status');

            if (! $response->successful()) {
                return response()->json([
                    'reachable'   => false,
                    'latency_ms'  => $this->elapsedMs($started),
                    'error'       => "HTTP {$response->status()}",
                ], 200);
            }

            return response()->json(array_merge(
                $response->json() ?? [],
                ['reachable' => true, 'latency_ms' => $this->elapsedMs($started)],
            ));
        } catch (\Throwable) {
            return response()->json([
                'reachable'   => false,
                'latency_ms'  => $this->elapsedMs($started),
                'error'       => 'Curator unreachable',
            ], 200);
        }
    }

    private function elapsedMs(float $started): int
    {
        return (int) round((microtime(true) - $started) * 1000);
    }
}
