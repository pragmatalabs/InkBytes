<?php

namespace Tests\Feature;

use App\Models\AuditLog;
use App\Models\Outlet;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Illuminate\Support\Facades\DB;
use Inertia\Testing\AssertableInertia;
use Tests\TestCase;

/**
 * B7 — pagination / search / sort / bulk.
 *
 * Covers the shared list mechanics applied to the three growth-prone lists:
 *   - Moderation: server pagination metadata + headline search + status filter
 *   - Outlets: search narrows, an allowlisted column sorts, bulk deactivate
 *     flips `active` and writes a B1 audit row
 *
 * SQLite caveat (same as OutletImportExportTest): the test DB has no `public`
 * schema. The Event/Page/Outlet models bind to `public.*`, which Eloquent
 * compiles to "public"."table" — matching Postgres. We ATTACH an in-memory
 * `public` database and create the Curator-owned tables there so the reads/
 * writes run against the REAL Eloquent models. DatabaseMigrations (not
 * RefreshDatabase) because ATTACH cannot run inside a per-test transaction.
 */
class PaginationSearchBulkTest extends TestCase
{
    use DatabaseMigrations;

    protected function setUp(): void
    {
        parent::setUp();

        DB::statement("ATTACH DATABASE ':memory:' AS public");

        // Curator-owned columns (test scaffolding only — no DDL is shipped).
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

        DB::statement('CREATE TABLE public.events (
            id TEXT PRIMARY KEY,
            created_at DATETIME,
            first_seen_at DATETIME,
            last_updated_at DATETIME,
            source_count INTEGER NOT NULL DEFAULT 1,
            article_count INTEGER NOT NULL DEFAULT 1,
            language TEXT NOT NULL,
            topic TEXT,
            status TEXT NOT NULL DEFAULT \'draft\'
        )');

        DB::statement('CREATE TABLE public.pages (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            headline TEXT NOT NULL,
            synthesis_md TEXT,
            evidence_rail TEXT,
            entities TEXT,
            freshness_at DATETIME,
            published_at DATETIME,
            cost_cents INTEGER
        )');
        // public.articles is read by the outlet stats join; an empty table keeps
        // that defensive read happy instead of degrading to the catch path.
        DB::statement('CREATE TABLE public.articles (
            id TEXT PRIMARY KEY,
            outlet_id TEXT,
            event_id TEXT,
            scraped_at DATETIME
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

    private function seedEvent(string $id, string $status, ?string $headline = null, string $updatedAt = '2026-06-01 10:00:00'): void
    {
        DB::table('public.events')->insert([
            'id' => $id,
            'created_at' => $updatedAt,
            'first_seen_at' => $updatedAt,
            'last_updated_at' => $updatedAt,
            'source_count' => 2,
            'article_count' => 3,
            'language' => 'en',
            'topic' => 'world',
            'status' => $status,
        ]);

        if ($headline !== null) {
            DB::table('public.pages')->insert([
                'id' => $id,
                'event_id' => $id,
                'headline' => $headline,
                'synthesis_md' => 'body',
                'evidence_rail' => json_encode([['source' => 's', 'url' => 'u', 'quote' => 'q']]),
                'entities' => json_encode([]),
                'freshness_at' => $updatedAt,
                'published_at' => $status === 'published' ? $updatedAt : null,
                'cost_cents' => 42,
            ]);
        }
    }

    // ── Moderation: pagination + search + status filter ─────────────────────────

    public function test_moderation_paginates_with_metadata(): void
    {
        $user = User::factory()->create();

        for ($i = 0; $i < 30; $i++) {
            $this->seedEvent("evt-{$i}", 'draft', "Headline {$i}");
        }

        $this->actingAs($user)
            ->get('/moderation?per_page=10&page=1')
            ->assertInertia(fn (AssertableInertia $page) => $page
                ->component('Moderation/Index')
                ->where('events.total', 30)
                ->where('events.per_page', 10)
                ->where('events.current_page', 1)
                ->has('events.data', 10)
            );
    }

    public function test_moderation_search_narrows_by_headline(): void
    {
        $user = User::factory()->create();

        $this->seedEvent('evt-quake', 'draft', 'Major earthquake hits region');
        $this->seedEvent('evt-vote', 'draft', 'Election results announced');

        $this->actingAs($user)
            ->get('/moderation?q=earthquake')
            ->assertInertia(fn (AssertableInertia $page) => $page
                ->where('events.total', 1)
                ->where('events.data.0.id', 'evt-quake')
            );
    }

    public function test_moderation_status_filter(): void
    {
        $user = User::factory()->create();

        $this->seedEvent('evt-pub', 'published', 'Published one');
        $this->seedEvent('evt-draft', 'draft', 'Draft one');
        $this->seedEvent('evt-drop', 'dropped', 'Dropped one');

        $this->actingAs($user)
            ->get('/moderation?status=published')
            ->assertInertia(fn (AssertableInertia $page) => $page
                ->where('events.total', 1)
                ->where('events.data.0.status', 'published')
            );
    }

    // ── Outlets: search + sort + bulk ───────────────────────────────────────────

    public function test_outlets_search_narrows(): void
    {
        $user = User::factory()->create();
        $this->seedOutlet(['id' => 'bbc', 'name' => 'bbc', 'display_name' => 'BBC', 'url' => 'https://www.bbc.com/']);
        $this->seedOutlet(['id' => 'wired', 'name' => 'wired', 'display_name' => 'Wired', 'url' => 'https://www.wired.com/']);

        $this->actingAs($user)
            ->get('/outlets?q=wired')
            ->assertInertia(fn (AssertableInertia $page) => $page
                ->component('Outlets/Index')
                ->has('outlets', 1)
                ->where('outlets.0.id', 'wired')
            );
    }

    public function test_outlets_sort_by_display_name_desc(): void
    {
        $user = User::factory()->create();
        $this->seedOutlet(['id' => 'aaa', 'name' => 'aaa', 'display_name' => 'AAA News', 'url' => 'https://a.example/']);
        $this->seedOutlet(['id' => 'zzz', 'name' => 'zzz', 'display_name' => 'ZZZ News', 'url' => 'https://z.example/']);

        $this->actingAs($user)
            ->get('/outlets?sort=display_name&dir=desc')
            ->assertInertia(fn (AssertableInertia $page) => $page
                ->where('outlets.0.id', 'zzz')
                ->where('outlets.1.id', 'aaa')
                ->where('filters.sort', 'display_name')
                ->where('filters.dir', 'desc')
            );
    }

    public function test_bulk_deactivate_flips_active_and_audits(): void
    {
        $operator = User::factory()->operator()->create();
        $this->seedOutlet(['id' => 'bbc', 'active' => true]);
        $this->seedOutlet(['id' => 'cnn', 'name' => 'cnn', 'display_name' => 'CNN', 'url' => 'https://cnn.com/', 'active' => true]);

        $this->actingAs($operator)
            ->post('/outlets/bulk', ['action' => 'deactivate', 'ids' => ['bbc', 'cnn']])
            ->assertRedirect(route('outlets.index'))
            ->assertSessionHas('success');

        $this->assertFalse((bool) Outlet::query()->find('bbc')->active);
        $this->assertFalse((bool) Outlet::query()->find('cnn')->active);

        // Per-row audit + a rollup summary carrying the affected ids.
        $this->assertSame(2, AuditLog::query()->where('action', 'outlet.updated')->count());
        $summary = AuditLog::query()->where('action', 'outlet.bulk_deactivated')->first();
        $this->assertNotNull($summary);
        $this->assertSame(2, $summary->after['count']);
        $this->assertEqualsCanonicalizing(['bbc', 'cnn'], $summary->after['ids']);
    }

    public function test_bulk_activate_and_delete(): void
    {
        $operator = User::factory()->operator()->create();
        $this->seedOutlet(['id' => 'bbc', 'active' => false]);
        $this->seedOutlet(['id' => 'cnn', 'name' => 'cnn', 'display_name' => 'CNN', 'url' => 'https://cnn.com/', 'active' => true]);

        // Activate bbc (cnn already active → no-op, no audit noise).
        $this->actingAs($operator)
            ->post('/outlets/bulk', ['action' => 'activate', 'ids' => ['bbc', 'cnn']]);
        $this->assertTrue((bool) Outlet::query()->find('bbc')->active);
        $this->assertSame(1, AuditLog::query()->where('action', 'outlet.updated')->count());

        // Delete both.
        $this->actingAs($operator)
            ->post('/outlets/bulk', ['action' => 'delete', 'ids' => ['bbc', 'cnn']]);
        $this->assertSame(0, Outlet::query()->count());
        $this->assertSame(2, AuditLog::query()->where('action', 'outlet.deleted')->count());
        $this->assertNotNull(AuditLog::query()->where('action', 'outlet.bulk_deleted')->first());
    }

    public function test_bulk_is_operator_gated(): void
    {
        $viewer = User::factory()->viewer()->create();

        $this->actingAs($viewer)
            ->post('/outlets/bulk', ['action' => 'deactivate', 'ids' => ['bbc']])
            ->assertForbidden();
    }

    public function test_bulk_rejects_unknown_action(): void
    {
        $operator = User::factory()->operator()->create();
        $this->seedOutlet();

        $this->actingAs($operator)
            ->post('/outlets/bulk', ['action' => 'frobnicate', 'ids' => ['bbc']])
            ->assertSessionHasErrors('action');
    }
}
