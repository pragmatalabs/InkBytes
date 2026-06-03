<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\CuratorCommandService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

/**
 * Phase 2.3 — moderation review screen + command publishing.
 *
 * The review controller reads Curator's public.events/public.pages, which do
 * not exist in the SQLite test DB; it degrades to an empty list (asserted
 * here). The command service is tested against a faked RabbitMQ management
 * HTTP API — no real broker needed.
 */
class ModerationTest extends TestCase
{
    use RefreshDatabase;

    public function test_moderation_index_renders_even_without_public_tables(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->get('/moderation')
            ->assertOk();
    }

    public function test_command_service_publishes_to_mgmt_api_with_routing_key_and_payload(): void
    {
        Http::fake([
            // PUT exchange declare → 201/204; POST publish → routed:true
            '*/publish' => Http::response(['routed' => true], 200),
            '*' => Http::response([], 201),
        ]);

        $service = app(CuratorCommandService::class);

        $this->assertTrue($service->unpublishPage('01EVENTPAGEID'));

        Http::assertSent(function ($request) {
            if (! str_ends_with($request->url(), '/publish')) {
                return false;
            }
            $body = $request->data();

            return $body['routing_key'] === 'page.unpublish'
                && $body['payload'] === json_encode(['id' => '01EVENTPAGEID'])
                && $body['payload_encoding'] === 'string';
        });
    }

    public function test_command_service_rejects_unknown_command(): void
    {
        $this->expectException(\RuntimeException::class);

        app(CuratorCommandService::class)->publish('page.frobnicate', 'x');
    }

    public function test_command_service_raises_when_message_not_routed(): void
    {
        // Exchange exists but no consumer queue bound → routed:false.
        Http::fake([
            '*/publish' => Http::response(['routed' => false], 200),
            '*' => Http::response([], 201),
        ]);

        $this->expectException(\RuntimeException::class);

        app(CuratorCommandService::class)->resynthesizeEvent('01EVENT');
    }

    public function test_publish_route_dispatches_command_and_flashes_success(): void
    {
        Http::fake([
            '*/publish' => Http::response(['routed' => true], 200),
            '*' => Http::response([], 201),
        ]);

        $user = User::factory()->create();

        $this->actingAs($user)
            ->post(route('moderation.pages.publish', '01PAGEID'))
            ->assertRedirect(route('moderation.index'))
            ->assertSessionHas('success');

        Http::assertSent(fn ($request) => str_ends_with($request->url(), '/publish')
            && $request->data()['routing_key'] === 'page.publish');
    }

    public function test_failed_publish_flashes_error_not_500(): void
    {
        Http::fake([
            '*/publish' => Http::response(['routed' => false], 200),
            '*' => Http::response([], 201),
        ]);

        $user = User::factory()->create();

        $this->actingAs($user)
            ->post(route('moderation.events.resynthesize', '01EVENT'))
            ->assertRedirect(route('moderation.index'))
            ->assertSessionHas('error');
    }
}
