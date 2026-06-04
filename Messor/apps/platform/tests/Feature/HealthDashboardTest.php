<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia;
use Tests\TestCase;

/**
 * B6 — Unified health dashboard.
 *
 * External calls (Curator / Messor / RabbitMQ) are faked with Http::fake() so
 * the suite never touches real infra. Postgres counts come from the SQLite test
 * DB, which has no `public.*` tables — so the controller's defensive fallback
 * marks postgres `down` here (and the page still renders). The fully-populated
 * postgres payload (309/220 counts) is verified against real Postgres via
 * tinker in the B6 verification notes, matching prior cross-schema phases.
 *
 * The point of these tests is the graceful-degradation contract: every external
 * component reports a status without throwing, and a down service never blocks
 * the page or the others.
 */
class HealthDashboardTest extends TestCase
{
    use RefreshDatabase;

    public function test_all_services_up(): void
    {
        Http::fake([
            '*/status' => Http::response([
                'articles_total' => 309,
                'events_total' => 220,
                'pages_published' => 29,
            ], 200),
            '*/api/scrapesessions*' => Http::response(['sessions' => []], 200),
            '*/api/overview' => Http::response(['rabbitmq_version' => '3.13'], 200),
            '*/api/queues' => Http::response([
                ['name' => 'curator.articles-scraped', 'messages' => 7],
                ['name' => 'curator.commands', 'messages' => 0],
            ], 200),
        ]);

        $user = User::factory()->create();

        $response = $this->actingAs($user)->get('/health');

        $response->assertOk();
        $response->assertInertia(fn (AssertableInertia $page) => $page
            ->component('Health/Index')
            ->where('health.curator.status', 'up')
            ->where('health.curator.metrics.pages_published', 29)
            ->where('health.messor.status', 'up')
            ->where('health.rabbitmq.status', 'up')
            // Key queue depth surfaced for the scraped-articles queue.
            ->where('health.rabbitmq.queues.0.name', 'curator.articles-scraped')
            ->where('health.rabbitmq.queues.0.messages', 7)
        );
    }

    public function test_service_down_degrades_gracefully(): void
    {
        Http::fake([
            // Curator down — connection refused style failure.
            '*/status' => fn () => throw new \Illuminate\Http\Client\ConnectionException('refused'),
            // Messor + RabbitMQ stay up.
            '*/api/scrapesessions*' => Http::response(['sessions' => []], 200),
            '*/api/overview' => Http::response(['rabbitmq_version' => '3.13'], 200),
            '*/api/queues' => Http::response([
                ['name' => 'curator.articles-scraped', 'messages' => 3],
            ], 200),
        ]);

        $user = User::factory()->create();

        $response = $this->actingAs($user)->get('/health');

        // Page still renders (no 500) with Curator reported unreachable and the
        // other services still up.
        $response->assertOk();
        $response->assertInertia(fn (AssertableInertia $page) => $page
            ->component('Health/Index')
            ->where('health.curator.status', 'unreachable')
            ->where('health.messor.status', 'up')
            ->where('health.rabbitmq.status', 'up')
        );
    }

    public function test_no_rabbitmq_credentials_in_props(): void
    {
        Http::fake([
            '*/status' => Http::response(['pages_published' => 1], 200),
            '*/api/scrapesessions*' => Http::response([], 200),
            '*/api/overview' => Http::response([], 200),
            '*/api/queues' => Http::response([], 200),
        ]);

        config([
            'services.curator.rabbitmq.user' => 'secret-user',
            'services.curator.rabbitmq.password' => 'super-secret-pass',
        ]);

        $user = User::factory()->create();

        $response = $this->actingAs($user)->get('/health');

        $response->assertOk();
        // Neither the basic-auth creds nor the mgmt URL should reach the client.
        $response->assertDontSee('super-secret-pass');
        $response->assertDontSee('secret-user');
        $response->assertDontSee('15672');
    }

    public function test_requires_authentication(): void
    {
        $this->get('/health')->assertRedirect('/login');
    }
}
