<?php

namespace App\Http\Controllers;

use App\Http\Controllers\Concerns\PaginatesQueries;
use App\Models\AuditLog;
use App\Models\Event;
use App\Models\Page;
use App\Services\CuratorCommandService;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Pagination\LengthAwarePaginator;
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
    use PaginatesQueries;

    private const STATUSES = ['published', 'draft', 'dropped'];

    /**
     * The 15 canonical enrichment themes (Curator ADR-0032 item 1; was 8 under
     * ADR-0027). Mirrors Curator's `_VALID_THEMES`. Used both to render the
     * moderation theme dropdown and to whitelist the ?theme= filter.
     */
    private const THEMES = [
        'politics', 'world', 'business', 'technology', 'science', 'health',
        'sports', 'culture', 'entertainment', 'environment', 'crime',
        'education', 'lifestyle', 'religion', 'disaster',
    ];

    /** Event columns the moderation list may sort on. */
    private const SORTABLE = ['status', 'topic', 'language', 'source_count', 'article_count', 'last_updated_at'];

    public function __construct(private readonly CuratorCommandService $commands)
    {
    }

    public function index(Request $request): Response
    {
        [$sort, $dir] = $this->resolveSort($request, self::SORTABLE, 'last_updated_at', 'desc');
        $perPage = $this->resolvePerPage($request, 25);
        $status = (string) $request->query('status', '');
        $q = trim((string) $request->query('q', ''));
        // Taxonomy filters (ADR-0027 / 6c). theme + category match events with
        // ≥1 article carrying that value; topic is a contains-search on article
        // topics. All filter via public.articles (theme/category/topic live
        // there, not on events).
        $theme = (string) $request->query('theme', '');
        $category = trim((string) $request->query('category', ''));
        $topic = trim((string) $request->query('topic', ''));

        // Read Curator's pipeline tables cross-schema (search_path =
        // backoffice,public). Defensive: if `public.events`/`public.pages` are
        // unreachable (a non-Postgres test DB, or Curator's schema not yet
        // migrated) we render an empty paginator rather than 500-ing — mirrors
        // the cost dashboard's read-only fallback.
        try {
            $query = Event::query()->with('page');

            // Filter by event status (published / draft / dropped).
            if (in_array($status, self::STATUSES, true)) {
                $query->where('status', $status);
            }

            // Search by PAGE HEADLINE — a correlated EXISTS against public.pages
            // keeps the read defensive (no hard JOIN that 500s if the schema is
            // absent) while still narrowing to events whose page matches.
            if ($q !== '') {
                $needle = '%'.$q.'%';
                $query->whereHas('page', fn ($p) => $p->where('headline', 'like', $needle));
            }

            // Taxonomy filters — correlated EXISTS against public.articles, same
            // defensive style as the headline search (no hard JOIN that 500s if
            // the public schema is absent).
            if (in_array($theme, self::THEMES, true)) {
                $query->whereExists(fn ($sub) => $sub->selectRaw('1')
                    ->from('public.articles as a')
                    ->whereColumn('a.event_id', 'public.events.id')
                    ->where('a.theme', $theme));
            }
            if ($category !== '') {
                $query->whereExists(fn ($sub) => $sub->selectRaw('1')
                    ->from('public.articles as a')
                    ->whereColumn('a.event_id', 'public.events.id')
                    ->where('a.article_category', $category));
            }
            if ($topic !== '') {
                $topicNeedle = '%'.$topic.'%';
                $query->whereExists(fn ($sub) => $sub->selectRaw('1')
                    ->from('public.articles as a')
                    ->whereColumn('a.event_id', 'public.events.id')
                    ->where('a.topic', 'like', $topicNeedle));
            }

            $this->applySort($query, $sort, $dir);

            $events = $query
                ->paginate($perPage)
                ->withQueryString()
                ->through(fn (Event $event): array => $this->present($event));

            $stats = [
                'event_count' => Event::query()->count(),
                'page_count' => Page::query()->count(),
                'published_count' => Page::query()->whereNotNull('published_at')->count(),
            ];
        } catch (Throwable $e) {
            // No public schema (test DB / fresh pipeline): hand-build an empty
            // paginator so the page renders the same shape as a live read.
            $events = new LengthAwarePaginator([], 0, $perPage, 1, [
                'path' => $request->url(),
                'query' => $request->query(),
            ]);
            $stats = ['event_count' => 0, 'page_count' => 0, 'published_count' => 0];
        }

        return Inertia::render('Moderation/Index', [
            'events' => $events,
            'stats' => $stats,
            'filters' => $this->listState($request, $sort, $dir, $perPage) + [
                'status' => in_array($status, self::STATUSES, true) ? $status : '',
                'theme' => in_array($theme, self::THEMES, true) ? $theme : '',
                'category' => $category,
                'topic' => $topic,
            ],
            'statuses' => self::STATUSES,
            'themes' => self::THEMES,
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
