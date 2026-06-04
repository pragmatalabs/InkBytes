<?php

namespace Tests\Feature;

use App\Jobs\RunScrapingWorker;
use App\Models\AuditLog;
use App\Models\Outlet;
use App\Models\ScrapingJob;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\DB;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\TestCase;

/**
 * Per-run scrape options — outlet subset + limit (branch backend/scrape-run-options).
 *
 * Three layers:
 *  1. RunScrapingWorker::composeScrapeArgs — the safe arg builder (pure, no DB).
 *  2. ScrapingJobController@trigger — validation (slug allowlist + limit range),
 *     options persistence, and audit. Injection attempts are rejected at
 *     validation and never reach the builder.
 *  3. ScrapingJobController@index — the active outlet catalogue for the UI.
 *
 * DatabaseMigrations (not RefreshDatabase) because ATTACH cannot run inside the
 * per-test transaction RefreshDatabase wraps everything in. The Outlet model is
 * bound to `public.outlets`, mirrored here as an in-memory attached schema.
 */
class ScrapeRunOptionsTest extends TestCase
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
    }

    private function seedOutlet(array $overrides = []): Outlet
    {
        return Outlet::query()->create(array_merge([
            'id' => 'bbc',
            'name' => 'bbc',
            'display_name' => 'BBC',
            'url' => 'https://www.bbc.com/',
            'region' => 'global',
            'language' => 'en',
            'vertical' => 'general',
            'active' => true,
            'priority' => 1,
        ], $overrides));
    }

    // ── 1. Safe arg builder (composeScrapeArgs) ───────────────────────────────

    public function test_arg_builder_no_options_scrapes_all(): void
    {
        $this->assertSame('--scrape', RunScrapingWorker::composeScrapeArgs(null));
        $this->assertSame('--scrape', RunScrapingWorker::composeScrapeArgs([]));
    }

    public function test_arg_builder_limit_only(): void
    {
        $this->assertSame(
            '--scrape=--limit=3',
            RunScrapingWorker::composeScrapeArgs(['limit' => 3])
        );
    }

    public function test_arg_builder_outlets_only_is_escaped(): void
    {
        $this->assertSame(
            "--scrape='--outlets=apnews,bbc'",
            RunScrapingWorker::composeScrapeArgs(['outlet_slugs' => ['apnews', 'bbc']])
        );
    }

    public function test_arg_builder_outlets_and_limit(): void
    {
        $this->assertSame(
            "--scrape='--outlets=bbc,cnbc --limit=5'",
            RunScrapingWorker::composeScrapeArgs([
                'outlet_slugs' => ['bbc', 'cnbc'],
                'limit' => 5,
            ])
        );
    }

    public function test_arg_builder_drops_malicious_slug_defensively(): void
    {
        // Defence-in-depth: even if a bad slug somehow reached the builder, the
        // SLUG_PATTERN drops it — nothing dangerous is emitted into the command.
        $args = RunScrapingWorker::composeScrapeArgs([
            'outlet_slugs' => ['bbc', 'bbc; rm -rf /'],
        ]);

        $this->assertSame("--scrape='--outlets=bbc'", $args);
        $this->assertStringNotContainsString('rm -rf', $args);
    }

    public function test_arg_builder_rejects_out_of_range_limit(): void
    {
        $this->assertSame('--scrape', RunScrapingWorker::composeScrapeArgs(['limit' => 0]));
        $this->assertSame('--scrape', RunScrapingWorker::composeScrapeArgs(['limit' => 9999]));
    }

    // ── 2. Trigger: validation + persistence + audit ──────────────────────────

    public function test_trigger_rejects_unknown_outlet_slug_with_422(): void
    {
        Bus::fake();
        config(['scraping.command' => 'echo {SCRAPE_ARGS}']);
        $operator = User::factory()->operator()->create();
        $this->seedOutlet(['id' => 'bbc']);

        $this->actingAs($operator)
            ->postJson('/scraping/trigger', [
                'outlet_slugs' => ['bbc', 'not-a-real-outlet'],
            ])
            ->assertStatus(422)
            ->assertJsonValidationErrors(['outlet_slugs']);

        $this->assertDatabaseCount('scraping_jobs', 0);
        Bus::assertNothingDispatched();
    }

    public function test_trigger_rejects_injection_attempt_slug_with_422(): void
    {
        Bus::fake();
        config(['scraping.command' => 'echo {SCRAPE_ARGS}']);
        $operator = User::factory()->operator()->create();
        $this->seedOutlet(['id' => 'bbc']);

        $this->actingAs($operator)
            ->postJson('/scraping/trigger', [
                'outlet_slugs' => ['bbc; rm -rf /'],
            ])
            ->assertStatus(422)
            ->assertJsonValidationErrors(['outlet_slugs.0']);

        $this->assertDatabaseCount('scraping_jobs', 0);
        Bus::assertNothingDispatched();
    }

    public function test_trigger_rejects_out_of_range_limit_with_422(): void
    {
        Bus::fake();
        config(['scraping.command' => 'echo {SCRAPE_ARGS}']);
        $operator = User::factory()->operator()->create();

        $this->actingAs($operator)
            ->postJson('/scraping/trigger', ['limit' => 9999])
            ->assertStatus(422)
            ->assertJsonValidationErrors(['limit']);

        $this->actingAs($operator)
            ->postJson('/scraping/trigger', ['limit' => 0])
            ->assertStatus(422)
            ->assertJsonValidationErrors(['limit']);
    }

    public function test_trigger_stores_options_and_audits(): void
    {
        Bus::fake();
        config(['scraping.command' => 'echo {SCRAPE_ARGS}']);
        $operator = User::factory()->operator()->create();
        $this->seedOutlet(['id' => 'bbc']);
        $this->seedOutlet([
            'id' => 'apnews', 'name' => 'apnews', 'display_name' => 'AP News',
            'url' => 'https://apnews.com/', 'priority' => 2,
        ]);

        $this->actingAs($operator)
            ->postJson('/scraping/trigger', [
                'name' => 'Subset run',
                'limit' => 4,
                'outlet_slugs' => ['bbc', 'apnews'],
            ])
            ->assertStatus(201);

        $job = ScrapingJob::query()->latest('id')->firstOrFail();
        $this->assertSame(['limit' => 4, 'outlet_slugs' => ['bbc', 'apnews']], $job->options);

        Bus::assertDispatched(RunScrapingWorker::class);

        $this->assertDatabaseHas('audit_logs', [
            'action' => 'scraping.triggered',
            'target_type' => 'scraping_job',
            'target_id' => (string) $job->id,
        ]);
        $audit = AuditLog::query()->where('action', 'scraping.triggered')->firstOrFail();
        $this->assertSame(['limit' => 4, 'outlet_slugs' => ['bbc', 'apnews']], $audit->after['options']);
    }

    public function test_trigger_with_no_options_stores_null_and_scrapes_all(): void
    {
        Bus::fake();
        config(['scraping.command' => 'echo {SCRAPE_ARGS}']);
        $operator = User::factory()->operator()->create();

        $this->actingAs($operator)
            ->postJson('/scraping/trigger', [])
            ->assertStatus(201);

        $job = ScrapingJob::query()->latest('id')->firstOrFail();
        $this->assertNull($job->options);

        // Backward-compat: the builder for a no-options job is the all-outlets default.
        $this->assertSame('--scrape', RunScrapingWorker::composeScrapeArgs($job->options));
    }

    public function test_trigger_remains_operator_gated(): void
    {
        Bus::fake();
        config(['scraping.command' => 'echo {SCRAPE_ARGS}']);
        $viewer = User::factory()->viewer()->create();

        $this->actingAs($viewer)
            ->postJson('/scraping/trigger', [])
            ->assertForbidden();

        $this->assertDatabaseCount('scraping_jobs', 0);
    }

    // ── 3. Index exposes the active outlet catalogue ──────────────────────────

    public function test_index_exposes_active_outlets_for_the_selector(): void
    {
        $user = User::factory()->create();
        $this->seedOutlet(['id' => 'bbc', 'display_name' => 'BBC']);
        $this->seedOutlet([
            'id' => 'inactive', 'name' => 'inactive', 'display_name' => 'Inactive',
            'url' => 'https://x/', 'active' => false,
        ]);

        $this->actingAs($user)
            ->get('/scraping')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('ScrapingJobs/Index')
                ->where('outlets', fn ($outlets) => collect($outlets)->pluck('id')->all() === ['bbc'])
            );
    }
}
