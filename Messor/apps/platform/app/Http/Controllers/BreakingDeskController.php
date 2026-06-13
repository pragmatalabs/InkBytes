<?php

namespace App\Http\Controllers;

use App\Models\Event;
use App\Services\CuratorCommandService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Inertia\Inertia;
use Inertia\Response;
use Throwable;

/**
 * On-Demand Breaking Desk (Curator ADR-0029).
 *
 * The editor enters a title or a URL; Messor searches Google News + scrapes the
 * coverage on demand at AMQP priority 9. The resulting articles flow through the
 * normal Curator pipeline under an `ondemand-<slug>` outlet brand. This screen
 * polls for the resulting events and exposes the manual gate actions
 * (mark breaking / force publish) via the Curator command bus.
 */
class BreakingDeskController extends Controller
{
    public function __construct(private readonly CuratorCommandService $commands) {}

    public function index(): Response
    {
        return Inertia::render('BreakingDesk/Index');
    }

    /**
     * Kick an on-demand scrape (title search or direct URL) on Messor.
     * Returns immediately with the brand; results stream in via results().
     */
    public function search(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'query' => ['nullable', 'string', 'max:300'],
            'url'   => ['nullable', 'url', 'max:2000'],
            'lang'  => ['nullable', 'in:en,es'],
            'limit' => ['nullable', 'integer', 'between:1,25'],
        ]);

        if (empty($data['query']) && empty($data['url'])) {
            return back()->with('error', 'Enter a title to search or a URL to scrape.');
        }

        $base = rtrim((string) config('services.messor.url'), '/');
        try {
            $resp = Http::timeout(15)->acceptJson()->post($base.'/api/scrape/on-demand', [
                'query' => $data['query'] ?? null,
                'url'   => $data['url'] ?? null,
                'lang'  => $data['lang'] ?? 'en',
                'limit' => $data['limit'] ?? 10,
            ]);
            if (! $resp->successful()) {
                return back()->with('error', "Messor returned HTTP {$resp->status()}.");
            }
            $brand = $resp->json('brand');
            return back()->with('success',
                "Scrape started ({$brand}). Results appear below as Curator processes them — usually under a minute.");
        } catch (Throwable $e) {
            Log::warning('On-demand scrape trigger failed: '.$e->getMessage());
            return back()->with('error', 'Could not reach Messor to start the scrape.');
        }
    }

    /**
     * JSON: events produced by on-demand scrapes (outlet brand 'ondemand-%')
     * in the recent window, newest first. Polled by the screen.
     */
    public function results(Request $request): JsonResponse
    {
        $hours = (int) $request->integer('hours', 6);
        $hours = max(1, min($hours, 72));

        try {
            $events = Event::query()
                ->with('page')
                ->whereExists(fn ($sub) => $sub->selectRaw('1')
                    ->from('public.articles as a')
                    ->whereColumn('a.event_id', 'public.events.id')
                    ->where('a.outlet_name', 'like', 'ondemand-%'))
                ->where('last_updated_at', '>=', now()->subHours($hours))
                ->orderByDesc('last_updated_at')
                ->limit(50)
                ->get()
                ->map(fn (Event $e) => $this->present($e))
                ->all();
        } catch (Throwable $e) {
            $events = [];
        }

        return response()->json(['events' => $events]);
    }

    public function markBreaking(string $event): RedirectResponse
    {
        return $this->dispatch(fn () => $this->commands->markBreaking($event),
            "Marked event {$event} as breaking.");
    }

    public function clearBreaking(string $event): RedirectResponse
    {
        return $this->dispatch(fn () => $this->commands->clearBreaking($event),
            "Cleared breaking flag on event {$event}.");
    }

    public function forcePublish(string $event): RedirectResponse
    {
        return $this->dispatch(fn () => $this->commands->forcePublish($event),
            "Force-publish command sent for event {$event}.");
    }

    private function dispatch(callable $fn, string $message): RedirectResponse
    {
        try {
            $fn();
            return back()->with('success', $message);
        } catch (Throwable $e) {
            return back()->with('error', 'Command failed: '.$e->getMessage());
        }
    }

    private function present(Event $event): array
    {
        $page = $event->page;

        return [
            'id' => $event->id,
            'status' => $event->status,
            'topic' => $event->topic,
            'language' => $event->language,
            'source_count' => (int) $event->source_count,
            'article_count' => (int) $event->article_count,
            'last_updated_at' => $event->last_updated_at?->toIso8601String(),
            'breaking_at' => $event->breaking_at?->toIso8601String(),
            'breaking_until' => $event->breaking_until?->toIso8601String(),
            'is_breaking' => $event->breaking_until !== null
                && $event->breaking_until->isFuture(),
            'page' => $page ? [
                'id' => $page->id,
                'headline' => $page->headline,
                'is_published' => $page->published_at !== null,
                'published_at' => $page->published_at?->toIso8601String(),
            ] : null,
        ];
    }
}
