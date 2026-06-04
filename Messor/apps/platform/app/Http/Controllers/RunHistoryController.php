<?php

namespace App\Http\Controllers;

use Illuminate\Support\Facades\Http;
use Inertia\Inertia;
use Inertia\Response;

/**
 * RunHistoryController — recent scraping run history / time-series (B4).
 *
 * Read-only observability over Messor's scrape sessions: a table of recent
 * runs, summary cards, and a dependency-free articles-per-run + success-rate
 * sparkline (rendered client-side from the mapped data — no charting library).
 *
 * Accessible to ALL authenticated roles (no `role` middleware in
 * routes/web.php): it performs no mutations and exposes no secrets.
 *
 * DATA SOURCE: Messor FastAPI `GET /api/scrapesessions?page&limit`
 * ({data:[...], meta:{pagination}}). This is LIVE, RECENT history bounded by
 * Messor's staging retention — not a durable long-range time-series. Durable
 * history would need persistence (future, Messor-side). There is also NO
 * dedup-ratio field in this payload; we surface only the fields present
 * (articles total/successful/failed, success_rate, outlets, duration).
 *
 * The external call is DEFENSIVE (short timeout + try/catch): if Messor is
 * down/slow the page renders an empty state with an "unreachable" notice rather
 * than throwing a 500 or hanging.
 */
class RunHistoryController extends Controller
{
    /** External call budget (seconds). Keeps the page snappy. */
    private const TIMEOUT = 3;

    /** How many recent sessions to pull (one reasonable window). */
    private const WINDOW = 50;

    public function index(): Response
    {
        $fetched = $this->fetchSessions();

        $runs = array_map(
            fn (array $session): array => $this->mapSession($session),
            $fetched['sessions'],
        );

        return Inertia::render('RunHistory/Index', [
            'runHistory' => [
                'runs' => $runs,
                'summary' => $this->summarize($runs),
                'reachable' => $fetched['reachable'],
                'error' => $fetched['error'],
                'window' => self::WINDOW,
                'checked_at' => now()->toIso8601String(),
            ],
        ]);
    }

    /**
     * Fetch the latest sessions from Messor, defensively.
     *
     * @return array{sessions: array<int, array<string, mixed>>, reachable: bool, error: ?string}
     */
    private function fetchSessions(): array
    {
        $base = rtrim((string) config('services.messor.url'), '/');

        try {
            $response = Http::timeout(self::TIMEOUT)
                ->acceptJson()
                ->get($base.'/api/scrapesessions', [
                    'page' => 1,
                    'limit' => self::WINDOW,
                ]);

            if (! $response->successful()) {
                return [
                    'sessions' => [],
                    'reachable' => false,
                    'error' => "Messor API returned HTTP {$response->status()}",
                ];
            }

            $data = $response->json('data');

            return [
                'sessions' => is_array($data) ? $data : [],
                'reachable' => true,
                'error' => null,
            ];
        } catch (\Throwable $e) {
            return [
                'sessions' => [],
                'reachable' => false,
                'error' => 'Messor API unreachable',
            ];
        }
    }

    /**
     * Normalise one Messor session into the shape the page consumes. Only the
     * fields Messor actually exposes are mapped (no fabricated dedup ratio).
     *
     * @param  array<string, mixed>  $s
     * @return array<string, mixed>
     */
    private function mapSession(array $s): array
    {
        $outlets = is_array($s['outlets'] ?? null) ? $s['outlets'] : [];

        // success_rate arrives as a 0..1 fraction; carry both the fraction and
        // a 0..100 percent for convenience on the client.
        $rate = isset($s['success_rate']) ? (float) $s['success_rate'] : null;

        return [
            'id' => (string) ($s['id'] ?? ''),
            'start_time' => $s['start_time'] ?? null,
            'end_time' => $s['end_time'] ?? null,
            'total_articles' => (int) ($s['total_articles'] ?? 0),
            'successful_articles' => (int) ($s['successful_articles'] ?? 0),
            'failed_articles' => (int) ($s['failed_articles'] ?? 0),
            'success_rate' => $rate,
            'success_rate_pct' => $rate !== null ? round($rate * 100, 1) : null,
            'duration' => isset($s['duration']) ? (float) $s['duration'] : null,
            'total_outlets' => (int) ($s['total_outlets'] ?? count($outlets)),
            'outlet_summary' => isset($s['outlet']) ? (string) $s['outlet'] : null,
            'outlets' => array_map(fn ($o): array => [
                'name' => (string) ($o['name'] ?? ''),
                'slug' => (string) ($o['slug'] ?? ''),
                'articles' => (int) ($o['articles'] ?? 0),
            ], $outlets),
        ];
    }

    /**
     * Roll the mapped runs up into the summary-card metrics.
     *
     * @param  array<int, array<string, mixed>>  $runs
     * @return array<string, mixed>
     */
    private function summarize(array $runs): array
    {
        $totalRuns = count($runs);

        if ($totalRuns === 0) {
            return [
                'total_runs' => 0,
                'total_articles' => 0,
                'avg_success_rate_pct' => null,
                'last_run_at' => null,
            ];
        }

        $totalArticles = array_sum(array_column($runs, 'total_articles'));

        $rates = array_filter(
            array_column($runs, 'success_rate'),
            fn ($r) => $r !== null,
        );
        $avgRate = count($rates) > 0
            ? round((array_sum($rates) / count($rates)) * 100, 1)
            : null;

        // Sessions arrive newest-first from Messor; the most recent start_time is
        // the freshest run regardless of ordering assumptions.
        $startTimes = array_filter(array_column($runs, 'start_time'));
        $lastRunAt = ! empty($startTimes) ? max($startTimes) : null;

        return [
            'total_runs' => $totalRuns,
            'total_articles' => $totalArticles,
            'avg_success_rate_pct' => $avgRate,
            'last_run_at' => $lastRunAt,
        ];
    }
}
