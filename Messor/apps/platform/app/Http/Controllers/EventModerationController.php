<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use App\Models\Event;
use App\Models\Page;
use App\Services\CuratorCommandService;
use Illuminate\Http\RedirectResponse;
use Inertia\Inertia;
use Inertia\Response;
use Throwable;

/**
 * Events / Pages moderation (Phase 2.3).
 *
 * READ-ONLY over Curator's `public.events` / `public.pages` (ADR-0003) for the
 * review list, plus command actions that publish RabbitMQ messages via
 * CuratorCommandService. The Backoffice NEVER writes events/pages directly —
 * Curator consumes the command and performs the toggle / skill re-run.
 *
 * Actions:
 *   publish/unpublish/drop  → on a page id
 *   resynthesize/recluster  → on an event id
 */
class EventModerationController extends Controller
{
    public function __construct(private readonly CuratorCommandService $commands)
    {
    }

    public function index(): Response
    {
        // Read Curator's pipeline tables cross-schema (search_path =
        // backoffice,public). Defensive: if `public.events`/`public.pages` are
        // unreachable (a non-Postgres test DB, or Curator's schema not yet
        // migrated) we render an empty list rather than 500-ing — mirrors the
        // cost dashboard's read-only fallback.
        try {
            $events = Event::query()
                ->with('page')
                ->orderByDesc('last_updated_at')
                ->limit(500)
                ->get()
                ->map(fn (Event $event): array => $this->present($event))
                ->values();

            $stats = [
                'event_count' => Event::query()->count(),
                'page_count' => Page::query()->count(),
                'published_count' => Page::query()->whereNotNull('published_at')->count(),
            ];
        } catch (Throwable $e) {
            $events = collect();
            $stats = ['event_count' => 0, 'page_count' => 0, 'published_count' => 0];
        }

        return Inertia::render('Moderation/Index', [
            'events' => $events,
            'stats' => $stats,
        ]);
    }

    public function publishPage(string $page): RedirectResponse
    {
        return $this->dispatch(fn () => $this->commands->publishPage($page),
            "Publish command sent for page {$page}.", 'page.published', 'page', $page);
    }

    public function unpublishPage(string $page): RedirectResponse
    {
        return $this->dispatch(fn () => $this->commands->unpublishPage($page),
            "Unpublish command sent for page {$page}.", 'page.unpublished', 'page', $page);
    }

    public function dropPage(string $page): RedirectResponse
    {
        return $this->dispatch(fn () => $this->commands->dropPage($page),
            "Drop command sent for page {$page}.", 'page.dropped', 'page', $page);
    }

    public function resynthesizeEvent(string $event): RedirectResponse
    {
        return $this->dispatch(fn () => $this->commands->resynthesizeEvent($event),
            "Re-synthesize command sent for event {$event}.", 'event.resynthesize', 'event', $event);
    }

    public function reclusterEvent(string $event): RedirectResponse
    {
        return $this->dispatch(fn () => $this->commands->reclusterEvent($event),
            "Re-cluster command sent for event {$event}.", 'event.recluster', 'event', $event);
    }

    /**
     * Run a command publish and flash success/error. The command is async —
     * Curator applies it shortly after; we report that it was *sent*, not that
     * the DB already changed. On a successful send we audit the action (these
     * are async commands, so we record intent — there is no before/after row to
     * diff here).
     */
    private function dispatch(
        callable $action,
        string $okMessage,
        string $auditAction,
        string $targetType,
        string $targetId,
    ): RedirectResponse {
        try {
            $action();
        } catch (Throwable $e) {
            return redirect()
                ->route('moderation.index')
                ->with('error', 'Command could not be sent: '.$e->getMessage());
        }

        AuditLog::record($auditAction, $targetType, $targetId);

        return redirect()
            ->route('moderation.index')
            ->with('success', $okMessage);
    }

    /**
     * @return array<string, mixed>
     */
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
            'page' => $page ? [
                'id' => $page->id,
                'headline' => $page->headline,
                // Source count for the page = entries on the evidence rail.
                'evidence_count' => is_array($page->evidence_rail) ? count($page->evidence_rail) : 0,
                'freshness_at' => $page->freshness_at?->toIso8601String(),
                'published_at' => $page->published_at?->toIso8601String(),
                'is_published' => $page->published_at !== null,
                'cost_cents' => $page->cost_cents,
            ] : null,
        ];
    }
}
