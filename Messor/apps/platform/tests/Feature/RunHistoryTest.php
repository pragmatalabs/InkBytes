<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia;
use Tests\TestCase;

/**
 * B4 — Scraping run history / time-series.
 *
 * Messor's /api/scrapesessions call is faked with Http::fake() so the suite
 * never touches real infra. Two contracts under test:
 *   1. Happy path — sessions map into runs + summary (success_rate, articles,
 *      outlets) for the table and the dependency-free sparkline.
 *   2. Graceful degradation — a failed/unreachable Messor renders the page with
 *      an empty state and reachable=false (never a 500, never a hang).
 */
class RunHistoryTest extends TestCase
{
    use RefreshDatabase;

    /** A sample Messor session payload (mirrors the real :8050 shape). */
    private function sampleSessions(): array
    {
        return [
            'data' => [
                [
                    'id' => 'session-1780459200',
                    'start_time' => '2026-06-03T04:00:00+00:00',
                    'end_time' => '2026-06-03T04:15:00.5+00:00',
                    'total_articles' => 1801,
                    'successful_articles' => 1801,
                    'failed_articles' => 0,
                    'success_rate' => 1.0,
                    'duration' => 900.5,
                    'outlet' => 'Al Jazeera, Infobae +1 more',
                    'outlets' => [
                        ['name' => 'Al Jazeera', 'slug' => 'aljazeera', 'articles' => 22],
                        ['name' => 'Infobae', 'slug' => 'infobae', 'articles' => 78],
                    ],
                    'total_outlets' => 2,
                    'views' => 0,
                    'last_viewed' => null,
                ],
                [
                    'id' => 'session-1780455600',
                    'start_time' => '2026-06-03T03:00:00+00:00',
                    'end_time' => '2026-06-03T03:10:00+00:00',
                    'total_articles' => 100,
                    'successful_articles' => 90,
                    'failed_articles' => 10,
                    'success_rate' => 0.9,
                    'duration' => 600.0,
                    'outlet' => 'NPR',
                    'outlets' => [
                        ['name' => 'NPR', 'slug' => 'npr', 'articles' => 90],
                    ],
                    'total_outlets' => 1,
                    'views' => 0,
                    'last_viewed' => null,
                ],
            ],
            'meta' => ['pagination' => ['page' => 1, 'pageSize' => 50, 'pageCount' => 1, 'total' => 2]],
        ];
    }

    public function test_maps_sessions_into_runs_and_summary(): void
    {
        Http::fake([
            '*/api/scrapesessions*' => Http::response($this->sampleSessions(), 200),
        ]);

        $user = User::factory()->create();

        $response = $this->actingAs($user)->get('/run-history');

        $response->assertOk();
        $response->assertInertia(fn (AssertableInertia $page) => $page
            ->component('RunHistory/Index')
            ->where('runHistory.reachable', true)
            ->where('runHistory.error', null)
            ->where('runHistory.runs.0.id', 'session-1780459200')
            ->where('runHistory.runs.0.total_articles', 1801)
            // success_rate 1.0 serializes to JSON 1; assert the derived pct.
            ->where('runHistory.runs.0.success_rate_pct', 100)
            ->where('runHistory.runs.0.total_outlets', 2)
            ->where('runHistory.runs.0.outlets.0.name', 'Al Jazeera')
            ->where('runHistory.runs.1.success_rate_pct', 90)
            // Summary rollup across both runs.
            ->where('runHistory.summary.total_runs', 2)
            ->where('runHistory.summary.total_articles', 1901)
            ->where('runHistory.summary.avg_success_rate_pct', 95)
            ->where('runHistory.summary.last_run_at', '2026-06-03T04:00:00+00:00')
        );
    }

    public function test_single_session_renders(): void
    {
        $single = $this->sampleSessions();
        $single['data'] = [$single['data'][0]];

        Http::fake([
            '*/api/scrapesessions*' => Http::response($single, 200),
        ]);

        $user = User::factory()->create();

        $response = $this->actingAs($user)->get('/run-history');

        $response->assertOk();
        $response->assertInertia(fn (AssertableInertia $page) => $page
            ->component('RunHistory/Index')
            ->where('runHistory.summary.total_runs', 1)
            ->where('runHistory.summary.total_articles', 1801)
        );
    }

    public function test_unreachable_messor_degrades_gracefully(): void
    {
        Http::fake([
            '*/api/scrapesessions*' => fn () => throw new \Illuminate\Http\Client\ConnectionException('refused'),
        ]);

        $user = User::factory()->create();

        $response = $this->actingAs($user)->get('/run-history');

        // Page still renders (no 500) with an empty state + unreachable flag.
        $response->assertOk();
        $response->assertInertia(fn (AssertableInertia $page) => $page
            ->component('RunHistory/Index')
            ->where('runHistory.reachable', false)
            ->where('runHistory.error', 'Messor API unreachable')
            ->where('runHistory.runs', [])
            ->where('runHistory.summary.total_runs', 0)
        );
    }

    public function test_non_200_from_messor_is_reported_unreachable(): void
    {
        Http::fake([
            '*/api/scrapesessions*' => Http::response('error', 503),
        ]);

        $user = User::factory()->create();

        $response = $this->actingAs($user)->get('/run-history');

        $response->assertOk();
        $response->assertInertia(fn (AssertableInertia $page) => $page
            ->component('RunHistory/Index')
            ->where('runHistory.reachable', false)
            ->where('runHistory.runs', [])
        );
    }

    public function test_requires_authentication(): void
    {
        $this->get('/run-history')->assertRedirect('/login');
    }
}
