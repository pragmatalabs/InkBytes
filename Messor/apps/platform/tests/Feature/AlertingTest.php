<?php

namespace Tests\Feature;

use App\Models\Alert;
use App\Models\AuditLog;
use App\Models\CuratorSetting;
use App\Models\ModelUsage;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

/**
 * B11 — Alerting.
 *
 * The scheduled evaluator (`alerts:evaluate`) probes the B3/B4/B5/B6 signal
 * sources and UPSERTS open alerts keyed on dedup_key. Operators+ acknowledge
 * them (status flip, audited B1); viewers are forbidden.
 *
 * SQLite caveat (same as OutletImportExportTest): the test DB is SQLite and has
 * no `public` schema, but the stale_outlet / pipeline_stalled rules read
 * public.outlets / public.articles. We ATTACH an in-memory `public` schema +
 * those tables so the evaluator runs against the real cross-schema reads exactly
 * as it would hit Postgres. DatabaseMigrations (not RefreshDatabase) because
 * ATTACH cannot run inside the per-test transaction RefreshDatabase wraps.
 *
 * Messor's HTTP probe (scrape_low_success / queue backlog) is faked, never live.
 */
class AlertingTest extends TestCase
{
    use DatabaseMigrations;

    protected function setUp(): void
    {
        parent::setUp();

        DB::statement("ATTACH DATABASE ':memory:' AS public");
        DB::statement('CREATE TABLE public.outlets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            url TEXT NOT NULL,
            region TEXT NOT NULL,
            language TEXT NOT NULL,
            vertical TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            priority INTEGER NOT NULL DEFAULT 2,
            created_at DATETIME,
            updated_at DATETIME
        )');
        DB::statement('CREATE TABLE public.articles (
            id TEXT PRIMARY KEY,
            outlet_id TEXT,
            scraped_at DATETIME
        )');

        // No real HTTP escapes the suite. We do NOT register a catch-all stub
        // here: Laravel MERGES successive Http::fake() calls and earlier stubs
        // win, so a per-test fake must be the FIRST fake registered for its
        // patterns to take effect. Each test therefore registers exactly the
        // probe responses it needs (unreachable = a 500 stub).
        Http::preventStrayRequests();
    }

    /** Make every external probe look unreachable (the common default). */
    private function fakeAllUnreachable(): void
    {
        Http::fake(['*' => Http::response([], 500)]);
    }

    private function seedOutlet(string $id, bool $active = true): void
    {
        DB::table('public.outlets')->insert([
            'id' => $id,
            'name' => $id,
            'display_name' => strtoupper($id),
            'url' => "https://{$id}.example.com/",
            'region' => 'global',
            'language' => 'en',
            'vertical' => 'general',
            'active' => $active ? 1 : 0,
            'priority' => 2,
        ]);
    }

    // ── over_budget (flagship) ────────────────────────────────────────────────

    public function test_over_budget_fires_and_dedups(): void
    {
        $this->fakeAllUnreachable();
        // Recent harvest + no stale/active outlets so only over_budget can fire.
        DB::table('public.articles')->insert([
            'id' => 'a1', 'outlet_id' => null, 'scraped_at' => now()->toDateTimeString(),
        ]);

        CuratorSetting::current()->update(['monthly_budget_usd' => 0.001]);
        ModelUsage::query()->create([
            'call_label' => 'synth', 'model' => 'claude-haiku-4-5',
            'input_tokens' => 100, 'output_tokens' => 50, 'cost_usd' => 1.50,
            'event_id' => null, 'created_at' => now(),
        ]);

        $this->artisan('alerts:evaluate')->assertExitCode(0);

        $alerts = Alert::query()->where('type', Alert::TYPE_OVER_BUDGET)->get();
        $this->assertCount(1, $alerts);
        $this->assertSame(Alert::SEVERITY_CRITICAL, $alerts->first()->severity);
        $this->assertSame(Alert::STATUS_OPEN, $alerts->first()->status);

        // Re-run: still one (deduped, refreshed not duplicated).
        $this->artisan('alerts:evaluate')->assertExitCode(0);
        $this->assertSame(1, Alert::query()->where('type', Alert::TYPE_OVER_BUDGET)->count());
    }

    public function test_over_budget_skipped_when_no_budget(): void
    {
        $this->fakeAllUnreachable();
        CuratorSetting::current()->update(['monthly_budget_usd' => null]);
        ModelUsage::query()->create([
            'call_label' => 'synth', 'model' => 'm',
            'input_tokens' => 1, 'output_tokens' => 1, 'cost_usd' => 99.0,
            'event_id' => null, 'created_at' => now(),
        ]);

        $this->artisan('alerts:evaluate');

        $this->assertSame(0, Alert::query()->where('type', Alert::TYPE_OVER_BUDGET)->count());
    }

    // ── stale_outlet ──────────────────────────────────────────────────────────

    public function test_stale_outlet_fires_per_outlet_never_scraped(): void
    {
        $this->fakeAllUnreachable();
        $this->seedOutlet('bbc', active: true);
        $this->seedOutlet('cnn', active: true);
        // An inactive outlet must NOT raise an alert.
        $this->seedOutlet('old', active: false);

        $this->artisan('alerts:evaluate');

        $this->assertSame(2, Alert::query()->where('type', Alert::TYPE_STALE_OUTLET)->count());
        $this->assertSame(1, Alert::query()->where('dedup_key', 'stale_outlet:bbc')->count());
        $this->assertSame(0, Alert::query()->where('dedup_key', 'stale_outlet:old')->count());
    }

    public function test_fresh_outlet_does_not_alert(): void
    {
        $this->fakeAllUnreachable();
        $this->seedOutlet('bbc', active: true);
        DB::table('public.articles')->insert([
            'id' => 'a1', 'outlet_id' => 'bbc', 'scraped_at' => now()->subHour()->toDateTimeString(),
        ]);

        $this->artisan('alerts:evaluate');

        $this->assertSame(0, Alert::query()->where('type', Alert::TYPE_STALE_OUTLET)->count());
    }

    public function test_stale_outlet_dedups_across_runs(): void
    {
        $this->fakeAllUnreachable();
        $this->seedOutlet('bbc', active: true);

        $this->artisan('alerts:evaluate');
        $this->artisan('alerts:evaluate');

        $this->assertSame(1, Alert::query()->where('dedup_key', 'stale_outlet:bbc')->count());
    }

    // ── scrape_low_success (faked Messor) ──────────────────────────────────────

    public function test_scrape_low_success_fires_below_threshold(): void
    {
        // Fresh harvest so pipeline_stalled stays quiet; fake a bad latest session.
        DB::table('public.articles')->insert([
            'id' => 'a1', 'outlet_id' => null, 'scraped_at' => now()->toDateTimeString(),
        ]);

        // This is the FIRST fake registered, so the specific pattern wins.
        Http::fake([
            '*/api/scrapesessions*' => Http::response([
                'data' => [[
                    'id' => 's1', 'success_rate' => 0.10,
                    'total_articles' => 100, 'failed_articles' => 90,
                ]],
            ], 200),
            '*' => Http::response([], 500),
        ]);

        $this->artisan('alerts:evaluate');

        $this->assertSame(1, Alert::query()->where('type', Alert::TYPE_SCRAPE_LOW_SUCCESS)->count());
    }

    public function test_scrape_low_success_skipped_when_messor_unreachable(): void
    {
        $this->fakeAllUnreachable();
        DB::table('public.articles')->insert([
            'id' => 'a1', 'outlet_id' => null, 'scraped_at' => now()->toDateTimeString(),
        ]);
        // Messor "unreachable" (500) — must NOT raise an alert.

        $this->artisan('alerts:evaluate');

        $this->assertSame(0, Alert::query()->where('type', Alert::TYPE_SCRAPE_LOW_SUCCESS)->count());
    }

    // ── pipeline_stalled ───────────────────────────────────────────────────────

    public function test_pipeline_stalled_fires_when_no_recent_harvest(): void
    {
        $this->fakeAllUnreachable();
        DB::table('public.articles')->insert([
            'id' => 'a1', 'outlet_id' => null,
            'scraped_at' => now()->subHours(48)->toDateTimeString(),
        ]);

        $this->artisan('alerts:evaluate');

        $this->assertSame(1, Alert::query()->where('type', Alert::TYPE_PIPELINE_STALLED)->count());
    }

    // ── Each rule independently try/caught ─────────────────────────────────────

    public function test_one_failing_probe_does_not_abort_the_others(): void
    {
        $this->fakeAllUnreachable();
        // Drop public.articles so the stale_outlet + pipeline rules throw, but
        // over_budget (no public dependency) must still fire.
        DB::statement('DROP TABLE public.articles');
        CuratorSetting::current()->update(['monthly_budget_usd' => 0.001]);
        ModelUsage::query()->create([
            'call_label' => 'synth', 'model' => 'm',
            'input_tokens' => 1, 'output_tokens' => 1, 'cost_usd' => 5.0,
            'event_id' => null, 'created_at' => now(),
        ]);

        $this->artisan('alerts:evaluate')->assertExitCode(0);

        $this->assertSame(1, Alert::query()->where('type', Alert::TYPE_OVER_BUDGET)->count());
    }

    // ── Page + acknowledge + RBAC + audit ──────────────────────────────────────

    public function test_alerts_page_paginates_for_any_role(): void
    {
        Alert::query()->create([
            'type' => Alert::TYPE_OVER_BUDGET, 'severity' => 'critical',
            'title' => 'x', 'message' => 'y', 'dedup_key' => 'over_budget',
            'status' => 'open',
        ]);

        $viewer = User::factory()->viewer()->create();
        $this->actingAs($viewer)
            ->get('/alerts')
            ->assertOk()
            ->assertInertia(fn ($p) => $p
                ->component('Alerts/Index')
                ->has('alerts.data', 1)
                ->where('openCount', 1));
    }

    public function test_acknowledge_flips_status_and_audits_operator(): void
    {
        $operator = User::factory()->operator()->create();
        $alert = Alert::query()->create([
            'type' => Alert::TYPE_STALE_OUTLET, 'severity' => 'warning',
            'title' => 'x', 'message' => 'y', 'dedup_key' => 'stale_outlet:bbc',
            'status' => 'open',
        ]);

        $this->actingAs($operator)
            ->post("/alerts/{$alert->id}/acknowledge")
            ->assertRedirect();

        $alert->refresh();
        $this->assertSame(Alert::STATUS_ACKNOWLEDGED, $alert->status);
        $this->assertNotNull($alert->acknowledged_at);
        $this->assertSame($operator->id, $alert->acknowledged_by);

        $this->assertSame(1, AuditLog::query()
            ->where('action', 'alert.acknowledged')
            ->where('target_id', (string) $alert->id)
            ->count());
    }

    public function test_acknowledge_is_forbidden_for_viewer(): void
    {
        $viewer = User::factory()->viewer()->create();
        $alert = Alert::query()->create([
            'type' => Alert::TYPE_OVER_BUDGET, 'severity' => 'critical',
            'title' => 'x', 'message' => 'y', 'dedup_key' => 'over_budget',
            'status' => 'open',
        ]);

        $this->actingAs($viewer)
            ->post("/alerts/{$alert->id}/acknowledge")
            ->assertForbidden();

        $this->assertSame(Alert::STATUS_OPEN, $alert->refresh()->status);
    }

    public function test_acknowledge_a_second_time_is_a_noop(): void
    {
        $admin = User::factory()->admin()->create();
        $alert = Alert::query()->create([
            'type' => Alert::TYPE_OVER_BUDGET, 'severity' => 'critical',
            'title' => 'x', 'message' => 'y', 'dedup_key' => 'over_budget',
            'status' => 'acknowledged', 'acknowledged_at' => now(),
        ]);

        $this->actingAs($admin)
            ->post("/alerts/{$alert->id}/acknowledge")
            ->assertRedirect();

        // No second audit row written for an already-acknowledged alert.
        $this->assertSame(0, AuditLog::query()->where('action', 'alert.acknowledged')->count());
    }
}
