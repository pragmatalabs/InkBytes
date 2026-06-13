<?php

namespace App\Console\Commands;

use App\Models\Alert;
use App\Models\CuratorSetting;
use App\Models\ModelUsage;
use Carbon\CarbonImmutable;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Throwable;

/**
 * alerts:evaluate — the scheduled alert evaluator (B11).
 *
 * Runs each rule against the EXISTING signal sources (no new probes invented):
 *   - over_budget       — MTD backoffice.model_usage cost vs
 *                         curator_settings.monthly_budget_usd (B5). Flagship,
 *                         fully deterministic (no external call).
 *   - stale_outlet      — active public.outlets whose latest scrape
 *                         (public.articles.scraped_at) is older than the
 *                         threshold, or never scraped (B3).
 *   - scrape_low_success— latest Messor /api/scrapesessions success_rate below
 *                         the threshold (B4; defensive HTTP — Messor being
 *                         unreachable does NOT alert here).
 *   - pipeline_stalled  — no harvest in N hours (MAX public.articles.scraped_at)
 *                         OR RabbitMQ key-queue depth over the backlog
 *                         threshold (B6).
 *
 * DEDUP: every rule UPSERTS by `dedup_key` via {@see raise()} — a still-firing
 * condition refreshes the existing OPEN alert's message/context instead of
 * creating a duplicate. There is no auto-resolve: once a condition clears the
 * OPEN alert stays for a human to acknowledge (an explicit decision — a cleared
 * alert is still operationally interesting; auto-closing would hide flapping).
 *
 * EACH rule is independently try/caught so one failing probe (e.g. Postgres
 * down) never aborts the others. The command always exits 0 — it is a
 * background evaluator, not a health gate.
 *
 * CHANNEL: in-app only for v0 (rows land in `alerts`; the bell + page render
 * them). {@see raise()} is the single place a future Notification/email channel
 * would hook in — fan out there on first-open.
 */
class EvaluateAlerts extends Command
{
    protected $signature = 'alerts:evaluate';

    protected $description = 'Evaluate operational alert rules and upsert open alerts (B11).';

    /** External probe budget (seconds). Mirrors HealthController. */
    private const TIMEOUT = 3;

    /** Queues whose combined depth counts toward the pipeline backlog (B6). */
    private const KEY_QUEUES = [
        'curator.articles-scraped',
        'curator.commands',
    ];

    public function handle(): int
    {
        $rules = [
            'over_budget' => fn () => $this->evaluateOverBudget(),
            'stale_outlet' => fn () => $this->evaluateStaleOutlets(),
            'scrape_low_success' => fn () => $this->evaluateScrapeLowSuccess(),
            'pipeline_stalled' => fn () => $this->evaluatePipelineStalled(),
        ];

        $raised = 0;

        foreach ($rules as $name => $rule) {
            try {
                $raised += (int) $rule();
            } catch (Throwable $e) {
                // One failing probe must never abort the rest of the sweep.
                Log::warning("alerts:evaluate rule [{$name}] failed", [
                    'error' => $e->getMessage(),
                ]);
                $this->warn("Rule [{$name}] failed: {$e->getMessage()}");
            }
        }

        $this->info("alerts:evaluate complete — {$raised} alert(s) open/refreshed.");

        return self::SUCCESS;
    }

    // ── Rules ────────────────────────────────────────────────────────────────

    /**
     * over_budget (flagship, deterministic). MTD model_usage cost vs the
     * configured monthly budget. Skipped when no budget is set.
     */
    private function evaluateOverBudget(): int
    {
        $budget = CuratorSetting::current()->monthly_budget_usd;

        if ($budget === null) {
            return 0;
        }

        $budget = (float) $budget;
        $monthStart = CarbonImmutable::now()->startOfMonth();

        $mtdSpend = (float) ModelUsage::query()
            ->where('created_at', '>=', $monthStart)
            ->sum('cost_usd');

        if ($mtdSpend <= $budget) {
            return 0;
        }

        $over = round($mtdSpend - $budget, 6);

        $this->raise(
            type: Alert::TYPE_OVER_BUDGET,
            severity: Alert::SEVERITY_CRITICAL,
            dedupKey: 'over_budget',
            title: 'Monthly LLM budget exceeded',
            message: sprintf(
                'Month-to-date spend $%s exceeds the $%s budget (over by $%s).',
                number_format($mtdSpend, 2),
                number_format($budget, 2),
                number_format($over, 2),
            ),
            context: [
                'budget_usd' => round($budget, 4),
                'mtd_spend_usd' => round($mtdSpend, 6),
                'over_usd' => $over,
                'month_start' => $monthStart->toDateString(),
            ],
        );

        return 1;
    }

    /**
     * stale_outlet. Active outlets whose newest article is older than the
     * threshold (or never scraped). One alert per outlet. Read-only cross-schema
     * (ADR-0003). Skips entirely if public.* is unreachable (handled by the
     * caller's try/catch).
     */
    private function evaluateStaleOutlets(): int
    {
        $hours = (int) config('curator.alerts.stale_outlet_hours', 24);
        $cutoff = CarbonImmutable::now()->subHours($hours);

        // Active outlets + their latest scrape, joined cross-schema read-only.
        $outlets = DB::table('public.outlets as o')
            ->leftJoin('public.articles as a', 'a.outlet_id', '=', 'o.id')
            ->where('o.active', true)
            ->groupBy('o.id', 'o.display_name')
            ->select('o.id', 'o.display_name')
            ->selectRaw('max(a.scraped_at) as last_scraped')
            ->get();

        $raised = 0;

        foreach ($outlets as $outlet) {
            $last = $outlet->last_scraped ? CarbonImmutable::parse($outlet->last_scraped) : null;

            if ($last !== null && $last->greaterThanOrEqualTo($cutoff)) {
                continue; // fresh
            }

            $never = $last === null;

            $this->raise(
                type: Alert::TYPE_STALE_OUTLET,
                severity: Alert::SEVERITY_WARNING,
                dedupKey: 'stale_outlet:'.$outlet->id,
                title: 'Outlet stale: '.($outlet->display_name ?? $outlet->id),
                message: $never
                    ? "Active outlet \"{$outlet->id}\" has never been scraped."
                    : sprintf(
                        'Active outlet "%s" last scraped %s (> %dh ago).',
                        $outlet->id,
                        $last->toIso8601String(),
                        $hours,
                    ),
                context: [
                    'outlet_id' => $outlet->id,
                    'display_name' => $outlet->display_name,
                    'last_scraped' => $last?->toIso8601String(),
                    'threshold_hours' => $hours,
                ],
            );

            $raised++;
        }

        return $raised;
    }

    /**
     * scrape_low_success. Latest Messor session success_rate below the
     * threshold. Defensive HTTP: if Messor is unreachable or returns no
     * sessions we DO NOT alert (we don't fault our own inability to reach it).
     */
    private function evaluateScrapeLowSuccess(): int
    {
        $minRate = (float) config('curator.alerts.low_success_rate', 0.5);
        $base = rtrim((string) config('services.messor.url'), '/');

        $response = Http::timeout(self::TIMEOUT)
            ->acceptJson()
            ->get($base.'/api/scrapesessions', ['page' => 1, 'limit' => 1]);

        if (! $response->successful()) {
            return 0; // unreachable / error — not our alert to raise
        }

        $sessions = $response->json('data');

        if (! is_array($sessions) || $sessions === []) {
            return 0;
        }

        $latest = $sessions[0];
        $rate = isset($latest['success_rate']) ? (float) $latest['success_rate'] : null;

        if ($rate === null || $rate >= $minRate) {
            return 0;
        }

        $this->raise(
            type: Alert::TYPE_SCRAPE_LOW_SUCCESS,
            severity: Alert::SEVERITY_WARNING,
            // Singleton: there is one "latest run is unhealthy" state. A new bad
            // run refreshes it; the open alert reflects the most recent run.
            dedupKey: 'scrape_low_success',
            title: 'Low scrape success rate',
            message: sprintf(
                'Latest harvest succeeded on %.1f%% of articles (below the %.1f%% floor).',
                $rate * 100,
                $minRate * 100,
            ),
            context: [
                'success_rate' => round($rate, 4),
                'success_rate_pct' => round($rate * 100, 1),
                'threshold_pct' => round($minRate * 100, 1),
                'session_id' => isset($latest['id']) ? (string) $latest['id'] : null,
                'total_articles' => (int) ($latest['total_articles'] ?? 0),
                'failed_articles' => (int) ($latest['failed_articles'] ?? 0),
            ],
        );

        return 1;
    }

    /**
     * pipeline_stalled. Fires when there has been no harvest in N hours
     * (MAX public.articles.scraped_at), OR the combined RabbitMQ key-queue depth
     * is above the backlog threshold. Either symptom maps to the same singleton
     * alert (the message names whichever tripped). RabbitMQ is probed
     * defensively — unreachable RabbitMQ does not by itself raise this rule.
     */
    private function evaluatePipelineStalled(): int
    {
        $stallHours = (int) config('curator.alerts.pipeline_stalled_hours', 6);
        $backlog = (int) config('curator.alerts.queue_backlog', 1000);

        $reasons = [];
        $context = [
            'stall_hours' => $stallHours,
            'backlog_threshold' => $backlog,
        ];

        // No-harvest check (read-only cross-schema).
        $lastHarvest = DB::scalar('SELECT MAX(scraped_at) FROM public.articles');
        $last = $lastHarvest ? CarbonImmutable::parse($lastHarvest) : null;
        $cutoff = CarbonImmutable::now()->subHours($stallHours);

        $context['last_harvest'] = $last?->toIso8601String();

        if ($last === null) {
            $reasons[] = 'no articles have ever been harvested';
        } elseif ($last->lessThan($cutoff)) {
            $reasons[] = sprintf('no harvest since %s (> %dh)', $last->toIso8601String(), $stallHours);
        }

        // Queue-backlog check (defensive: unreachable RabbitMQ is skipped, not
        // faulted). Counted across the key pipeline queues.
        $depth = $this->queueBacklog();
        if ($depth !== null) {
            $context['queue_backlog'] = $depth;
            if ($depth > $backlog) {
                $reasons[] = sprintf('RabbitMQ backlog %d messages (> %d)', $depth, $backlog);
            }
        }

        if ($reasons === []) {
            return 0;
        }

        $this->raise(
            type: Alert::TYPE_PIPELINE_STALLED,
            severity: Alert::SEVERITY_CRITICAL,
            dedupKey: 'pipeline_stalled',
            title: 'Pipeline stalled',
            message: 'Pipeline stalled: '.implode('; ', $reasons).'.',
            context: $context,
        );

        return 1;
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    /**
     * Combined depth of the key pipeline queues via the RabbitMQ management API
     * (same creds/pattern as HealthController). Returns null when RabbitMQ is
     * unreachable so the caller can SKIP the backlog symptom rather than alert
     * on our own probe failure.
     */
    private function queueBacklog(): ?int
    {
        $cfg = config('services.curator.rabbitmq');
        $base = rtrim((string) ($cfg['management_url'] ?? ''), '/');

        try {
            $queues = Http::withBasicAuth($cfg['user'] ?? '', $cfg['password'] ?? '')
                ->timeout(self::TIMEOUT)
                ->acceptJson()
                ->get($base.'/api/queues');

            if (! $queues->successful()) {
                return null;
            }

            $rows = $queues->json() ?? [];
            $total = 0;

            foreach ($rows as $q) {
                if (isset($q['name']) && in_array($q['name'], self::KEY_QUEUES, true)) {
                    $total += (int) ($q['messages'] ?? 0);
                }
            }

            return $total;
        } catch (Throwable $e) {
            return null;
        }
    }

    /**
     * UPSERT an open alert by dedup_key. If an OPEN alert with this key exists
     * it is refreshed (message/context/severity) so a persistent condition does
     * not duplicate; otherwise a new OPEN row is created. This is the single
     * funnel where a future email/Notification channel would fire on first-open.
     *
     * @param  array<string, mixed>  $context
     */
    private function raise(
        string $type,
        string $severity,
        string $dedupKey,
        string $title,
        string $message,
        array $context = [],
    ): void {
        $existing = Alert::query()
            ->where('dedup_key', $dedupKey)
            ->where('status', Alert::STATUS_OPEN)
            ->first();

        if ($existing !== null) {
            $existing->update([
                'type' => $type,
                'severity' => $severity,
                'title' => $title,
                'message' => $message,
                'context' => $context,
            ]);

            return;
        }

        Alert::query()->create([
            'type' => $type,
            'severity' => $severity,
            'title' => $title,
            'message' => $message,
            'context' => $context,
            'dedup_key' => $dedupKey,
            'status' => Alert::STATUS_OPEN,
        ]);

        // FUTURE: dispatch a Notification (email/Slack) here on first-open only.
    }
}
