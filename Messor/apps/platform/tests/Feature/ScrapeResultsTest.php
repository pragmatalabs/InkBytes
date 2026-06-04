<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Illuminate\Support\Facades\DB;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\TestCase;

/**
 * B12.2 — Backoffice Scrape Results browser (read-only, cross-schema).
 *
 * The page reads Curator's `public.scrape_sessions` (ADR-0006), which the
 * Backoffice never writes. Two shapes are exercised:
 *
 *  1. EMPTY — `public.scrape_sessions` does not exist (no ATTACH). The
 *     controller's defensive try/catch must render an empty paginator + the
 *     `reachable=false` flag rather than 500-ing. This matches the live state
 *     today (the table exists but holds 0 rows — same empty-list outcome).
 *
 *  2. POPULATED — we ATTACH an in-memory `public` schema + the scrape_sessions
 *     table (mirroring the Curator-owned columns; no DDL/migration is shipped)
 *     so the list + per-session detail run against the REAL Eloquent model,
 *     exactly as they would hit Postgres. DatabaseMigrations (not
 *     RefreshDatabase) because ATTACH cannot run inside the per-test
 *     transaction RefreshDatabase wraps everything in.
 */
class ScrapeResultsTest extends TestCase
{
    use DatabaseMigrations;

    /**
     * Create the test-only `public.scrape_sessions` scaffold. Called explicitly
     * by the populated tests; the empty-state test deliberately skips it so the
     * cross-schema read fails and exercises the catch path.
     */
    private function attachScrapeSessions(): void
    {
        DB::statement("ATTACH DATABASE ':memory:' AS public");
        DB::statement('CREATE TABLE public.scrape_sessions (
            session_id TEXT PRIMARY KEY,
            started_at DATETIME,
            ended_at DATETIME,
            total_articles INTEGER NOT NULL DEFAULT 0,
            successful_articles INTEGER NOT NULL DEFAULT 0,
            failed_articles INTEGER NOT NULL DEFAULT 0,
            duplicates_total INTEGER NOT NULL DEFAULT 0,
            success_rate NUMERIC NOT NULL DEFAULT 0,
            duration_seconds NUMERIC,
            outlets TEXT NOT NULL DEFAULT "[]",
            total_outlets INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME
        )');
    }

    /**
     * Insert one session row directly (the Backoffice model is read-only).
     *
     * @param  array<string, mixed>  $overrides
     */
    private function seedSession(array $overrides = []): string
    {
        $row = array_merge([
            'session_id' => 'session-1700000000',
            'started_at' => '2026-06-04 10:00:00',
            'ended_at' => '2026-06-04 10:05:00',
            'total_articles' => 100,
            'successful_articles' => 90,
            'failed_articles' => 10,
            'duplicates_total' => 5,
            'success_rate' => 0.9,
            'duration_seconds' => 300,
            'outlets' => json_encode([
                ['name' => 'CNN', 'slug' => 'cnn', 'articles' => 60, 'successful' => 55, 'failed' => 5, 'duplicates' => 3],
                ['name' => 'NPR', 'slug' => 'npr', 'articles' => 40, 'successful' => 35, 'failed' => 5, 'duplicates' => 2],
            ]),
            'total_outlets' => 2,
            'created_at' => '2026-06-04 10:05:00',
            'updated_at' => '2026-06-04 10:05:00',
        ], $overrides);

        DB::table('public.scrape_sessions')->insert($row);

        return $row['session_id'];
    }

    // ── Empty state (table unreachable / 0 rows) ──────────────────────────────

    public function test_index_renders_empty_state_when_table_unreachable(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->get('/scrape-results')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('ScrapeResults/Index')
                ->where('reachable', false)
                ->where('sessions.total', 0)
                ->where('sessions.data', [])
                ->where('stats.session_count', 0)
            );
    }

    // ── Populated list ────────────────────────────────────────────────────────

    public function test_index_lists_a_seeded_session(): void
    {
        $this->attachScrapeSessions();
        $user = User::factory()->create();
        $this->seedSession();

        $this->actingAs($user)
            ->get('/scrape-results')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->component('ScrapeResults/Index')
                ->where('reachable', true)
                ->where('sessions.total', 1)
                ->where('stats.session_count', 1)
                ->where('sessions.data.0.session_id', 'session-1700000000')
                ->where('sessions.data.0.total_articles', 100)
                ->where('sessions.data.0.successful_articles', 90)
                ->where('sessions.data.0.success_rate_pct', 90)
                ->where('sessions.data.0.total_outlets', 2)
            );
    }

    public function test_index_search_narrows_by_session_id(): void
    {
        $this->attachScrapeSessions();
        $user = User::factory()->create();
        $this->seedSession(['session_id' => 'session-aaa']);
        $this->seedSession(['session_id' => 'session-bbb']);

        $this->actingAs($user)
            ->get('/scrape-results?q=aaa')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->where('sessions.total', 1)
                ->where('sessions.data.0.session_id', 'session-aaa')
            );
    }

    public function test_index_sorts_by_total_articles_desc(): void
    {
        $this->attachScrapeSessions();
        $user = User::factory()->create();
        $this->seedSession(['session_id' => 'session-small', 'total_articles' => 10]);
        $this->seedSession(['session_id' => 'session-big', 'total_articles' => 999]);

        $this->actingAs($user)
            ->get('/scrape-results?sort=total_articles&dir=desc')
            ->assertOk()
            ->assertInertia(fn (Assert $page) => $page
                ->where('sessions.data.0.session_id', 'session-big')
                ->where('filters.sort', 'total_articles')
                ->where('filters.dir', 'desc')
            );
    }

    // ── Per-session detail (outlets[] breakdown) ──────────────────────────────

    public function test_show_returns_per_outlet_breakdown(): void
    {
        $this->attachScrapeSessions();
        $user = User::factory()->create();
        $id = $this->seedSession();

        $response = $this->actingAs($user)->getJson('/scrape-results/'.$id);

        $response->assertOk()
            ->assertJsonPath('session.session_id', $id)
            ->assertJsonPath('session.outlets.0.name', 'CNN')
            ->assertJsonPath('session.outlets.0.articles', 60)
            ->assertJsonPath('session.outlets.0.duplicates', 3)
            ->assertJsonPath('session.outlets.1.slug', 'npr')
            ->assertJsonCount(2, 'session.outlets');
    }

    public function test_show_returns_404_for_unknown_session(): void
    {
        $this->attachScrapeSessions();
        $user = User::factory()->create();

        $this->actingAs($user)
            ->getJson('/scrape-results/session-does-not-exist')
            ->assertStatus(404)
            ->assertJsonPath('session', null);
    }

    // ── Auth gating (read pages are all-authenticated, B2) ────────────────────

    public function test_index_requires_authentication(): void
    {
        $this->get('/scrape-results')->assertRedirect('/login');
    }

    public function test_show_requires_authentication(): void
    {
        $this->get('/scrape-results/session-1700000000')->assertRedirect('/login');
    }

    public function test_index_is_available_to_a_viewer_role(): void
    {
        $this->attachScrapeSessions();
        $viewer = User::factory()->viewer()->create();
        $this->seedSession();

        $this->actingAs($viewer)->get('/scrape-results')->assertOk();
    }
}
