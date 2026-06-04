<?php

namespace App\Http\Controllers;

use App\Http\Controllers\Concerns\PaginatesQueries;
use App\Models\CuratorSetting;
use App\Models\ModelUsage;
use Carbon\CarbonImmutable;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Inertia\Inertia;
use Inertia\Response;
use Symfony\Component\HttpFoundation\StreamedResponse;
use Throwable;

/**
 * Read-only cost dashboard over `backoffice.model_usage` (Phase 2.2; B5 upgrades).
 *
 * Aggregates Curator's persisted LLM-call rows into spend by model, by skill,
 * by day, projected per 1000 articles, and per published page. The per-1000 and
 * per-page figures are derived from live `public` counts (articles / pages) —
 * all reads, no writes. This controller never mutates usage data; there is no
 * create/edit/delete surface (ADR-0003: Curator writes, Backoffice reads).
 *
 * B5 adds:
 *   - a from/to date-range filter that scopes ALL aggregates (default last 30d);
 *   - a CSV export of the filtered rows (streamed);
 *   - a configurable monthly budget (curator_settings.monthly_budget_usd) with a
 *     month-to-date spend-vs-budget widget + over-budget alert;
 *   - a by-event drill-down (synth rows grouped by event_id, joined to
 *     public.pages for the headline; enrich/event_id-NULL rows aggregated apart).
 *
 * DEFERRED (data not captured): per-OUTLET and per-API-KEY cost. `model_usage`
 * carries neither `outlet_id` nor `api_key_id`, so those breakdowns would need
 * Curator to start writing those columns first — see gap-analysis B5.
 */
class ModelUsageController extends Controller
{
    use PaginatesQueries;

    public function index(Request $request): Response
    {
        [$from, $to] = $this->resolveRange($request);

        // Live denominators from Curator's public pipeline tables. The Backoffice
        // reads across the schema line (search_path = backoffice,public).
        // Defensive: if the public tables are unreachable (e.g. a non-Postgres
        // test DB, or Curator's schema not yet migrated) we fall back to 0 so
        // the read-only dashboard still renders rather than 500-ing.
        $articleCount = $this->publicCount('public.articles');
        $pageCount = $this->publicCount('public.pages');

        // Filtered base query — every aggregate below derives from this range.
        $scoped = fn () => ModelUsage::query()
            ->where('created_at', '>=', $from)
            ->where('created_at', '<=', $to);

        $totalCost = (float) $scoped()->sum('cost_usd');
        $totalInputTokens = (int) $scoped()->sum('input_tokens');
        $totalOutputTokens = (int) $scoped()->sum('output_tokens');
        $totalCalls = (int) $scoped()->count();

        $byModel = $scoped()
            ->selectRaw('model,
                count(*) as calls,
                sum(input_tokens) as input_tokens,
                sum(output_tokens) as output_tokens,
                sum(cost_usd) as cost_usd')
            ->groupBy('model')
            ->orderByDesc('cost_usd')
            ->get()
            ->map(fn ($row): array => [
                'model' => $row->model,
                'calls' => (int) $row->calls,
                'input_tokens' => (int) $row->input_tokens,
                'output_tokens' => (int) $row->output_tokens,
                'cost_usd' => round((float) $row->cost_usd, 6),
            ])
            ->values();

        // Per-call-label breakdown (enrich vs synthesize) — useful context.
        $byLabel = $scoped()
            ->selectRaw('call_label,
                count(*) as calls,
                sum(cost_usd) as cost_usd')
            ->groupBy('call_label')
            ->orderByDesc('cost_usd')
            ->get()
            ->map(fn ($row): array => [
                'call_label' => $row->call_label,
                'calls' => (int) $row->calls,
                'cost_usd' => round((float) $row->cost_usd, 6),
            ])
            ->values();

        // Day bucket expression. Postgres (prod) has date_trunc; SQLite (tests)
        // does not, so fall back to strftime. Both yield a sortable date string.
        $dayExpr = $this->dayExpr();

        $byDay = $scoped()
            ->selectRaw("$dayExpr as day,
                count(*) as calls,
                sum(input_tokens) as input_tokens,
                sum(output_tokens) as output_tokens,
                sum(cost_usd) as cost_usd")
            ->groupByRaw($dayExpr)
            ->orderByRaw("$dayExpr desc")
            ->limit(60)
            ->get()
            ->map(fn ($row): array => [
                'day' => $row->day ? substr((string) $row->day, 0, 10) : null,
                'calls' => (int) $row->calls,
                'input_tokens' => (int) $row->input_tokens,
                'output_tokens' => (int) $row->output_tokens,
                'cost_usd' => round((float) $row->cost_usd, 6),
            ])
            ->values();

        return Inertia::render('ModelUsage/Index', [
            'filters' => [
                'from' => $from->toDateString(),
                'to' => $to->toDateString(),
            ],
            'summary' => [
                'total_cost_usd' => round($totalCost, 6),
                'total_calls' => $totalCalls,
                'total_input_tokens' => $totalInputTokens,
                'total_output_tokens' => $totalOutputTokens,
                'article_count' => $articleCount,
                'page_count' => $pageCount,
                // Projected spend per 1000 articles / per published page.
                // Null when the denominator is 0 so the UI can show "—".
                'cost_per_1000_articles' => $articleCount > 0
                    ? round($totalCost / $articleCount * 1000, 4)
                    : null,
                'cost_per_page' => $pageCount > 0
                    ? round($totalCost / $pageCount, 4)
                    : null,
            ],
            'budget' => $this->budgetWidget(),
            'byModel' => $byModel,
            'byLabel' => $byLabel,
            'byDay' => $byDay,
            'byEvent' => $this->byEvent($request, $from, $to),
        ]);
    }

    /**
     * Stream the filtered usage rows as CSV (B5). Same access as the cost page
     * (all authenticated roles) and honours the same from/to range so the
     * export matches what the dashboard shows.
     */
    public function export(Request $request): StreamedResponse
    {
        [$from, $to] = $this->resolveRange($request);

        $filename = sprintf(
            'model-usage_%s_to_%s.csv',
            $from->toDateString(),
            $to->toDateString(),
        );

        $columns = [
            'created_at',
            'call_label',
            'model',
            'input_tokens',
            'output_tokens',
            'cost_usd',
            'event_id',
        ];

        return response()->streamDownload(function () use ($from, $to, $columns): void {
            $out = fopen('php://output', 'w');
            // Explicit escape arg: its default changes in PHP 8.4 (deprecation).
            // "" keeps CSV values literal (RFC 4180-style quoting only).
            fputcsv($out, $columns, ',', '"', '');

            // Stream in id order to keep memory flat regardless of row count.
            ModelUsage::query()
                ->where('created_at', '>=', $from)
                ->where('created_at', '<=', $to)
                ->orderBy('created_at')
                ->orderBy('id')
                ->chunk(1000, function ($rows) use ($out): void {
                    foreach ($rows as $row) {
                        fputcsv($out, [
                            $row->created_at?->toIso8601String(),
                            $row->call_label,
                            $row->model,
                            (int) $row->input_tokens,
                            (int) $row->output_tokens,
                            // Full precision in the export, not the rounded UI value.
                            number_format((float) $row->cost_usd, 6, '.', ''),
                            $row->event_id,
                        ], ',', '"', '');
                    }
                });

            fclose($out);
        }, $filename, [
            'Content-Type' => 'text/csv',
            'Cache-Control' => 'no-store, no-cache',
        ]);
    }

    /**
     * Resolve the from/to range from the request. Defaults to the last 30 days
     * (inclusive of today). `from` is taken at start-of-day, `to` at end-of-day
     * so a single-day range captures that whole day. Invalid input falls back
     * to the default rather than erroring the read-only view.
     *
     * @return array{0: CarbonImmutable, 1: CarbonImmutable}
     */
    private function resolveRange(Request $request): array
    {
        $to = $this->parseDate($request->query('to')) ?? CarbonImmutable::now();
        $from = $this->parseDate($request->query('from'))
            ?? $to->subDays(29);

        // Guard against an inverted range (from after to): swap them.
        if ($from->greaterThan($to)) {
            [$from, $to] = [$to, $from];
        }

        return [$from->startOfDay(), $to->endOfDay()];
    }

    private function parseDate(?string $value): ?CarbonImmutable
    {
        if ($value === null || $value === '') {
            return null;
        }

        try {
            return CarbonImmutable::parse($value);
        } catch (Throwable $e) {
            return null;
        }
    }

    /**
     * Day-bucket SQL expression for the active connection (Postgres vs SQLite).
     */
    private function dayExpr(): string
    {
        $driver = ModelUsage::query()->getConnection()->getDriverName();

        return $driver === 'pgsql'
            ? "to_char(date_trunc('day', created_at), 'YYYY-MM-DD')"
            : "strftime('%Y-%m-%d', created_at)";
    }

    /**
     * Month-to-date spend vs the configured monthly budget. Returns null when
     * no budget is set so the UI hides the widget entirely.
     *
     * @return array{budget_usd: float, mtd_spend_usd: float, pct: float, over_budget: bool, month_start: string}|null
     */
    private function budgetWidget(): ?array
    {
        $budget = CuratorSetting::current()->monthly_budget_usd;

        if ($budget === null) {
            return null;
        }

        $budget = (float) $budget;
        $monthStart = CarbonImmutable::now()->startOfMonth();

        $mtdSpend = (float) ModelUsage::query()
            ->where('created_at', '>=', $monthStart)
            ->sum('cost_usd');

        return [
            'budget_usd' => round($budget, 4),
            'mtd_spend_usd' => round($mtdSpend, 6),
            // Percent of budget consumed; 0 budget → 100% (any spend is over).
            'pct' => $budget > 0
                ? round($mtdSpend / $budget * 100, 1)
                : ($mtdSpend > 0 ? 100.0 : 0.0),
            'over_budget' => $mtdSpend > $budget,
            'month_start' => $monthStart->toDateString(),
        ];
    }

    /**
     * By-event drill-down (B5; B7 paginates it). Groups synth rows (event_id NOT
     * NULL) within the range by event_id with cost + token totals, joined
     * defensively to public.pages for the headline. Enrich calls (event_id NULL)
     * carry no event and are surfaced separately by the UI via the by-skill table
     * — here we only return the per-event synth rows (now SERVER-PAGINATED so the
     * table scales as model_usage grows) plus an aggregate of the NULL-event rows.
     *
     * Uses its own `event_page` page name so it never collides with other lists.
     * The headline join only resolves the current page's event ids.
     *
     * @return array{events: array<string, mixed>, unattributed: array<string, mixed>}
     */
    private function byEvent(Request $request, CarbonImmutable $from, CarbonImmutable $to): array
    {
        $perPage = $this->resolvePerPage($request, 25);

        // Per-event totals (synth rows), paginated. The aggregate is grouped by
        // event_id; Laravel paginates the grouped result and runs an accurate
        // count of the distinct groups.
        $paginator = ModelUsage::query()
            ->whereNotNull('event_id')
            ->where('created_at', '>=', $from)
            ->where('created_at', '<=', $to)
            ->selectRaw('event_id,
                count(*) as calls,
                sum(input_tokens) as input_tokens,
                sum(output_tokens) as output_tokens,
                sum(cost_usd) as cost_usd')
            ->groupBy('event_id')
            ->orderByDesc('cost_usd')
            ->paginate($perPage, ['*'], 'event_page')
            ->withQueryString();

        // Headline join for the current page only (defensive: missing
        // public.pages degrades to null headlines instead of 500-ing).
        $headlines = $this->headlinesFor($paginator->getCollection()->pluck('event_id')->all());

        $paginator->through(fn ($row): array => [
            'event_id' => $row->event_id,
            'headline' => $headlines[$row->event_id] ?? null,
            'calls' => (int) $row->calls,
            'input_tokens' => (int) $row->input_tokens,
            'output_tokens' => (int) $row->output_tokens,
            'cost_usd' => round((float) $row->cost_usd, 6),
        ]);

        // Aggregate of rows with no event (enrich calls run pre-clustering).
        $unattributed = ModelUsage::query()
            ->whereNull('event_id')
            ->where('created_at', '>=', $from)
            ->where('created_at', '<=', $to)
            ->selectRaw('count(*) as calls,
                sum(input_tokens) as input_tokens,
                sum(output_tokens) as output_tokens,
                sum(cost_usd) as cost_usd')
            ->first();

        return [
            'events' => $paginator,
            'unattributed' => [
                'calls' => (int) ($unattributed->calls ?? 0),
                'input_tokens' => (int) ($unattributed->input_tokens ?? 0),
                'output_tokens' => (int) ($unattributed->output_tokens ?? 0),
                'cost_usd' => round((float) ($unattributed->cost_usd ?? 0), 6),
            ],
        ];
    }

    /**
     * Map event_id → page headline via a read-only cross-schema join on
     * public.pages. Defensive: returns [] if public.pages is unreachable.
     *
     * @param  array<int, string>  $eventIds
     * @return array<string, string|null>
     */
    private function headlinesFor(array $eventIds): array
    {
        $eventIds = array_values(array_filter($eventIds, fn ($id) => $id !== null && $id !== ''));

        if ($eventIds === []) {
            return [];
        }

        try {
            return DB::table('public.pages')
                ->whereIn('event_id', $eventIds)
                ->pluck('headline', 'event_id')
                ->all();
        } catch (Throwable $e) {
            return [];
        }
    }

    /**
     * Count rows in a Curator-owned `public` table, returning 0 if the table
     * is unreachable. Keeps the dashboard rendering when reading across the
     * schema line is not possible (non-Postgres test DB, fresh pipeline).
     */
    private function publicCount(string $table): int
    {
        try {
            return (int) DB::table($table)->count();
        } catch (Throwable $e) {
            return 0;
        }
    }
}
