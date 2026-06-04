<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

/**
 * B2 — RBAC: the `role` middleware gates dangerous routes server-side.
 *
 * Three tiers (admin ⊇ operator ⊇ viewer). The middleware runs before the
 * controller, so a forbidden role gets a 403 before any Postgres-backed
 * controller logic runs — which is why these gating assertions work against the
 * SQLite test DB even for routes that read Curator's `public.*` tables.
 *
 * For roles that DO pass the gate on those routes, we assert "not a 403"
 * (the controller may then redirect with a validation/flash error), since the
 * underlying public.* tables don't exist in SQLite. Moderation action POSTs
 * fake the RabbitMQ management API so an operator/admin reaches a real 302.
 */
class RoleAccessTest extends TestCase
{
    use RefreshDatabase;

    private function fakeRabbit(): void
    {
        Http::fake([
            '*/publish' => Http::response(['routed' => true], 200),
            '*' => Http::response([], 201),
        ]);
    }

    // ── viewer: read-only everything, 403 on every mutation ──────────────────

    public function test_viewer_can_reach_read_only_pages(): void
    {
        $viewer = User::factory()->viewer()->create();

        // Read-only pages that degrade gracefully without Curator's public.*
        // tables (see ModelUsageTest / ModerationTest). The Dashboard reads
        // public.outlets directly and is exercised against Postgres, not here.
        $this->actingAs($viewer)->get('/model-usage')->assertOk();
        $this->actingAs($viewer)->get('/moderation')->assertOk();
    }

    public function test_viewer_is_forbidden_from_outlet_store(): void
    {
        $viewer = User::factory()->viewer()->create();

        $this->actingAs($viewer)->post('/outlets', [])->assertForbidden();
    }

    public function test_viewer_is_forbidden_from_settings_update(): void
    {
        $viewer = User::factory()->viewer()->create();

        $this->actingAs($viewer)->put('/settings', [])->assertForbidden();
    }

    public function test_viewer_is_forbidden_from_api_key_store(): void
    {
        $viewer = User::factory()->viewer()->create();

        $this->actingAs($viewer)->post('/api-keys', [])->assertForbidden();
    }

    public function test_viewer_is_forbidden_from_moderation_actions(): void
    {
        $this->fakeRabbit();
        $viewer = User::factory()->viewer()->create();

        $this->actingAs($viewer)
            ->post(route('moderation.pages.publish', '01PAGEID'))
            ->assertForbidden();
        $this->actingAs($viewer)
            ->post(route('moderation.pages.unpublish', '01PAGEID'))
            ->assertForbidden();
        $this->actingAs($viewer)
            ->post(route('moderation.pages.drop', '01PAGEID'))
            ->assertForbidden();
    }

    public function test_viewer_is_forbidden_from_admin_sections(): void
    {
        $viewer = User::factory()->viewer()->create();

        $this->actingAs($viewer)->get('/api-keys')->assertForbidden();
        $this->actingAs($viewer)->get('/settings')->assertForbidden();
        $this->actingAs($viewer)->get('/audit-log')->assertForbidden();
        $this->actingAs($viewer)->get('/users')->assertForbidden();
    }

    // ── operator: outlets + moderation pass; keys + settings 403 ─────────────

    public function test_operator_is_forbidden_from_api_keys_and_settings(): void
    {
        $operator = User::factory()->operator()->create();

        $this->actingAs($operator)->get('/api-keys')->assertForbidden();
        $this->actingAs($operator)->post('/api-keys', [])->assertForbidden();
        $this->actingAs($operator)->put('/settings', [])->assertForbidden();
        $this->actingAs($operator)->get('/users')->assertForbidden();
    }

    public function test_operator_passes_outlet_gate(): void
    {
        $operator = User::factory()->operator()->create();

        // Passes the `role` gate (operator+), so it reaches the controller.
        // The outlet `store` validation uses Rule::unique('public.outlets'),
        // which only exists in Postgres — under the SQLite test DB it cannot
        // resolve, so the request continues past the gate to a non-403 outcome.
        // The point of THIS test is the gate, not the controller: assert the
        // operator is NOT forbidden (contrast with the viewer 403 above).
        $response = $this->actingAs($operator)->post('/outlets', []);
        $this->assertNotSame(403, $response->getStatusCode());
    }

    public function test_operator_passes_moderation_gate(): void
    {
        $this->fakeRabbit();
        $operator = User::factory()->operator()->create();

        $this->actingAs($operator)
            ->post(route('moderation.pages.publish', '01PAGEID'))
            ->assertRedirect(route('moderation.index'));
    }

    // ── admin: passes everything ─────────────────────────────────────────────

    public function test_admin_can_reach_admin_sections(): void
    {
        $admin = User::factory()->admin()->create();

        $this->actingAs($admin)->get('/api-keys')->assertOk();
        $this->actingAs($admin)->get('/settings')->assertOk();
        $this->actingAs($admin)->get('/audit-log')->assertOk();
        $this->actingAs($admin)->get('/users')->assertOk();
    }

    public function test_admin_passes_moderation_and_outlet_gates(): void
    {
        $this->fakeRabbit();
        $admin = User::factory()->admin()->create();

        // Outlet gate: admin is NOT forbidden (see operator test for the
        // Postgres-only validation caveat).
        $outletResponse = $this->actingAs($admin)->post('/outlets', []);
        $this->assertNotSame(403, $outletResponse->getStatusCode());

        $this->actingAs($admin)
            ->post(route('moderation.pages.publish', '01PAGEID'))
            ->assertRedirect(route('moderation.index'));
    }

    // ── default role for new self-service registrations ──────────────────────

    public function test_new_registration_defaults_to_viewer(): void
    {
        $this->post('/register', [
            'name' => 'Newbie',
            'email' => 'newbie@example.test',
            'password' => 'password123',
            'password_confirmation' => 'password123',
        ]);

        $user = User::query()->where('email', 'newbie@example.test')->firstOrFail();
        $this->assertSame(User::ROLE_VIEWER, $user->role);
    }
}
