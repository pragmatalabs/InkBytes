<?php

namespace App\Http\Controllers;

use App\Models\ModelUsage;
use Illuminate\Support\Facades\DB;
use Inertia\Inertia;
use Inertia\Response;
use Throwable;

/**
 * Read-only cost dashboard over `backoffice.model_usage` (Phase 2.2).
 *
 * Aggregates Curator's persisted LLM-call rows into spend by model, by day,
 * projected per 1000 articles, and per published page. The per-1000 and
 * per-page figures are derived from live `public` counts (articles / pages) —
 * all reads, no writes. This controller never mutates usage data; there is no
 * create/edit/delete surface (ADR-0003: Curator writes, Backoffice reads).
 */
class ModelUsageController extends Controller
{
    public function index(): Response
    {
        $totalCost = (float) ModelUsage::query()->sum('cost_usd');
        $totalInputTokens = (int) ModelUsage::query()->sum('input_tokens');
        $totalOutputTokens = (int) ModelUsage::query()->sum('output_tokens');
        $totalCalls = (int) ModelUsage::query()->count();

        // Live denominators from Curator's public pipeline tables. The Backoffice
        // reads across the schema line (search_path = backoffice,public).
        // Defensive: if the public tables are unreachable (e.g. a non-Postgres
        // test DB, or Curator's schema not yet migrated) we fall back to 0 so
        // the read-only dashboard still renders rather than 500-ing.
        $articleCount = $this->publicCount('public.articles');
        $pageCount = $this->publicCount('public.pages');

        $byModel = ModelUsage::query()
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
        $byLabel = ModelUsage::query()
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
        $driver = ModelUsage::query()->getConnection()->getDriverName();
        $dayExpr = $driver === 'pgsql'
            ? "to_char(date_trunc('day', created_at), 'YYYY-MM-DD')"
            : "strftime('%Y-%m-%d', created_at)";

        $byDay = ModelUsage::query()
            ->selectRaw("$dayExpr as day,
                count(*) as calls,
                sum(input_tokens) as input_tokens,
                sum(output_tokens) as output_tokens,
                sum(cost_usd) as cost_usd")
            ->groupByRaw($dayExpr)
            ->orderByRaw("$dayExpr desc")
            ->limit(30)
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
            'byModel' => $byModel,
            'byLabel' => $byLabel,
            'byDay' => $byDay,
        ]);
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
