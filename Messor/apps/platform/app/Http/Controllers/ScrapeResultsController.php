<?php

namespace App\Http\Controllers;

use App\Http\Controllers\Concerns\PaginatesQueries;
use App\Models\ScrapeSession;
use Illuminate\Http\Request;
use Illuminate\Pagination\LengthAwarePaginator;
use Inertia\Inertia;
use Inertia\Response;
use Throwable;

/**
 * ScrapeResultsController — per-session, per-outlet harvest results (B12.2).
 *
 * READ-ONLY over Curator's `public.scrape_sessions` (ADR-0003 cross-schema read;
 * ADR-0006). This is the one feature the legacy :5174 Messor client had that the
 * Backoffice lacked — folding it in here makes the B12.3 decommission safe.
 *
 * Each row is a durable, run-level record of a Messor harvest (one per run
 * across all outlets) with the per-outlet breakdown in `outlets[]`. Messor emits
 * the data; Curator persists it; the Backoffice only displays it.
 *
 * Accessible to ALL authenticated roles (no `role` middleware in
 * routes/web.php): it performs no mutations and exposes no secrets.
 *
 * DEFENSIVE: the cross-schema read is wrapped in try/catch. If
 * `public.scrape_sessions` is unreachable (a non-Postgres test DB, or Curator's
 * schema not yet migrated) we render an empty paginator rather than 500-ing —
 * mirrors EventModerationController's read-only fallback. The table is currently
 * empty (no real harvest has emitted a session yet), so the page must also look
 * right with zero rows.
 */
class ScrapeResultsController extends Controller
{
    use PaginatesQueries;

    /** Session columns the list may sort on. */
    private const SORTABLE = ['started_at', 'success_rate', 'total_articles', 'total_outlets'];

    /** Harvest lanes (Messor ADR-0017): 5-min RSS pulse vs the full cycle. */
    private const LANES = ['cycle', 'pulse'];

    public function index(Request $request): Response
    {
        [$sort, $dir] = $this->resolveSort($request, self::SORTABLE, 'started_at', 'desc');
        $perPage = $this->resolvePerPage($request, 25);
        $q = trim((string) $request->query('q', ''));
        // Lane filter (Messor ADR-0017): the pulse lane emits ~120 mostly-dup
        // sessions/hour that bury the full-cycle runs; let the user filter them.
        $lane = (string) $request->query('lane', '');

        $reachable = true;
        $daily = [];

        try {
            $query = ScrapeSession::query();

            // Search by session id (no LIKE over the jsonb `outlets` here — a
            // text search inside JSON differs across Postgres/SQLite; the model
            // resolves the per-outlet breakdown on the detail view instead).
            $this->applySearch($query, $q, ['session_id']);
            if (in_array($lane, self::LANES, true)) {
                $query->where('lane', $lane);
            }
            $this->applySort($query, $sort, $dir);

            $sessions = $query
                ->paginate($perPage)
                ->withQueryString()
                ->through(fn (ScrapeSession $s): array => $this->presentRow($s));

            $stats = [
                'session_count' => ScrapeSession::query()->count(),
            ];

            // Daily new-article rollup (last 7 days) — the number that actually
            // reflects intake health, summed across BOTH lanes so the pulse
            // noise in the row list doesn't hide the real daily total.
            $daily = ScrapeSession::query()
                ->selectRaw("date_trunc('day', started_at)::date AS day")
                ->selectRaw('SUM(successful_articles) AS new_articles')
                ->selectRaw('COUNT(*) AS sessions')
                ->whereNotNull('started_at')
                ->where('started_at', '>=', now()->subDays(7))
                ->groupByRaw("date_trunc('day', started_at)::date")
                ->orderByRaw("date_trunc('day', started_at)::date DESC")
                ->get()
                ->map(fn ($r): array => [
                    'day' => (string) $r->day,
                    'new_articles' => (int) $r->new_articles,
                    'sessions' => (int) $r->sessions,
                ])
                ->all();
        } catch (Throwable $e) {
            // No public schema (test DB / fresh pipeline): hand-build an empty
            // paginator so the page renders the same shape as a live read.
            $reachable = false;
            $sessions = new LengthAwarePaginator([], 0, $perPage, 1, [
                'path' => $request->url(),
                'query' => $request->query(),
            ]);
            $stats = ['session_count' => 0];
        }

        return Inertia::render('ScrapeResults/Index', [
            'sessions' => $sessions,
            'stats' => $stats,
            'daily' => $daily,
            'reachable' => $reachable,
            'lanes' => self::LANES,
            'filters' => $this->listState($request, $sort, $dir, $perPage) + [
                'lane' => in_array($lane, self::LANES, true) ? $lane : '',
            ],
        ]);
    }

    /**
     * Per-session detail — the `outlets[]` breakdown for one run. Returned as a
     * JSON payload the page fetches lazily (modal/expand) so the list stays
     * lean. Defensive: a missing schema / unknown id returns a 404-style empty
     * payload rather than throwing.
     */
    public function show(Request $request, string $session)
    {
        try {
            $row = ScrapeSession::query()->find($session);
        } catch (Throwable $e) {
            $row = null;
        }

        if ($row === null) {
            return response()->json(['session' => null], 404);
        }

        return response()->json(['session' => $this->presentDetail($row)]);
    }

    /**
     * Normalise one session into the list-row shape the page consumes.
     *
     * @return array<string, mixed>
     */
    private function presentRow(ScrapeSession $s): array
    {
        $successful  = (int) $s->successful_articles;
        $total       = (int) $s->total_articles;
        $duplicates  = (int) $s->duplicates_total;

        // Messor counts duplicates as "failed", so the stored success_rate
        // (successful / total) is misleading — a session with 90% duplicates
        // and perfect parse success would show ~10% success.
        //
        // Real parse success = successful / (total − duplicates).
        // This answers: "of articles we hadn't seen before, how many did we save?"
        $trueNew  = max(0, $total - $duplicates);
        $realRate = $trueNew > 0 ? $successful / $trueNew : null;

        return [
            'session_id'          => $s->session_id,
            'started_at'          => $s->started_at?->toIso8601String(),
            'ended_at'            => $s->ended_at?->toIso8601String(),
            'total_articles'      => $total,
            'successful_articles' => $successful,
            'failed_articles'     => (int) $s->failed_articles,
            'duplicates_total'    => $duplicates,
            'success_rate'        => $realRate,
            'success_rate_pct'    => $realRate !== null ? round($realRate * 100, 1) : null,
            'duration_seconds'    => $s->duration_seconds !== null ? (float) $s->duration_seconds : null,
            'total_outlets'       => (int) $s->total_outlets,
            'lane'                => $s->lane ?? 'cycle',
        ];
    }

    /**
     * The full per-session detail, including the per-outlet breakdown.
     *
     * @return array<string, mixed>
     */
    private function presentDetail(ScrapeSession $s): array
    {
        $outlets = is_array($s->outlets) ? $s->outlets : [];

        return $this->presentRow($s) + [
            'outlets' => array_map(function ($o): array {
                $saved   = (int) ($o['successful'] ?? 0);
                $dupes   = (int) ($o['duplicates'] ?? 0);
                $failed  = (int) ($o['failed'] ?? 0);
                // true new = failed - dupes (Messor counts dupes as failed)
                $trueNew = max(0, $failed - $dupes);
                $pct     = ($saved + $trueNew) > 0
                    ? round($saved / ($saved + $trueNew) * 100, 1)
                    : null;
                return [
                    'name'        => (string) ($o['name'] ?? ''),
                    'slug'        => (string) ($o['slug'] ?? ''),
                    'articles'    => (int) ($o['articles'] ?? 0),
                    'successful'  => $saved,
                    'failed'      => $failed,
                    'duplicates'  => $dupes,
                    'parse_success_pct' => $pct,
                ];
            }, array_values($outlets)),
        ];
    }
}
