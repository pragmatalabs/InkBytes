<?php

namespace Tests\Feature;

use App\Models\ApiKey;
use App\Models\AuditLog;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

class ApiKeysTest extends TestCase
{
    use RefreshDatabase;

    public function test_index_is_displayed(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->get('/api-keys')->assertOk();
    }

    public function test_key_is_stored_encrypted_and_never_returned_raw(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->post('/api-keys', [
            'provider' => 'openai',
            'label' => 'prod',
            'value' => 'sk-super-secret-1234',
            'active' => true,
        ])->assertRedirect(route('api-keys.index'));

        $key = ApiKey::first();
        $this->assertNotNull($key);

        // Decrypts transparently in PHP via the cast.
        $this->assertSame('sk-super-secret-1234', $key->value);

        // ...but the raw column holds ciphertext, not the plaintext.
        $raw = DB::table('api_keys')->where('id', $key->id)->value('value');
        $this->assertNotSame('sk-super-secret-1234', $raw);
        $this->assertStringNotContainsString('sk-super-secret-1234', $raw);

        // Masked form shows only the last 4, and serialization hides the value.
        $this->assertStringEndsWith('1234', $key->masked());
        $this->assertArrayNotHasKey('value', $key->toArray());
    }

    public function test_rotate_keeps_existing_secret_when_value_blank(): void
    {
        $user = User::factory()->create();
        $key = ApiKey::create([
            'provider' => 'anthropic',
            'label' => 'old',
            'value' => 'sk-original-9999',
            'active' => true,
        ]);

        $this->actingAs($user)->put("/api-keys/{$key->id}", [
            'label' => 'renamed',
            'value' => '', // blank => keep existing secret
            'active' => false,
        ])->assertRedirect(route('api-keys.index'));

        $key->refresh();
        $this->assertSame('renamed', $key->label);
        $this->assertFalse($key->active);
        $this->assertSame('sk-original-9999', $key->value);
    }

    public function test_key_can_be_deleted(): void
    {
        $user = User::factory()->create();
        $key = ApiKey::create([
            'provider' => 'openai',
            'value' => 'sk-delete-me-0000',
            'active' => true,
        ]);

        $this->actingAs($user)
            ->delete("/api-keys/{$key->id}")
            ->assertRedirect(route('api-keys.index'));

        $this->assertNull(ApiKey::find($key->id));
    }

    // ── B8: one-active-per-provider ──────────────────────────────────────────

    public function test_activating_a_key_deactivates_the_previous_active_one(): void
    {
        $user = User::factory()->create();

        // Key A: anthropic, active.
        $this->actingAs($user)->post('/api-keys', [
            'provider' => 'anthropic',
            'label' => 'A',
            'value' => 'sk-ant-aaaa-1111',
            'active' => true,
        ])->assertRedirect(route('api-keys.index'));
        $a = ApiKey::where('label', 'A')->firstOrFail();
        $this->assertTrue($a->fresh()->active);

        // Key B: anthropic, active → B becomes sole active, A demoted.
        $this->actingAs($user)->post('/api-keys', [
            'provider' => 'anthropic',
            'label' => 'B',
            'value' => 'sk-ant-bbbb-2222',
            'active' => true,
        ])->assertRedirect(route('api-keys.index'));
        $b = ApiKey::where('label', 'B')->firstOrFail();

        $this->assertTrue($b->fresh()->active, 'B should be active');
        $this->assertFalse($a->fresh()->active, 'A should be auto-deactivated');

        // Exactly one active anthropic key.
        $this->assertSame(1, ApiKey::where('provider', 'anthropic')->where('active', true)->count());

        // The auto-deactivation is audited as apikey.deactivated, secret-free.
        $deactivated = AuditLog::where('action', 'apikey.deactivated')
            ->where('target_id', (string) $a->id)
            ->firstOrFail();
        $this->assertSame('apikey', $deactivated->target_type);
        $this->assertFalse($deactivated->after['active']);
        // No key material anywhere in the audit row.
        $blob = json_encode([$deactivated->before, $deactivated->after]);
        $this->assertStringNotContainsString('sk-ant-aaaa-1111', $blob);
        $this->assertStringNotContainsString('sk-ant-bbbb-2222', $blob);
    }

    public function test_activating_via_update_deactivates_the_previous_active_one(): void
    {
        $user = User::factory()->create();
        $a = ApiKey::create(['provider' => 'openai', 'label' => 'A', 'value' => 'sk-a-1111', 'active' => true]);
        $b = ApiKey::create(['provider' => 'openai', 'label' => 'B', 'value' => 'sk-b-2222', 'active' => false]);

        $this->actingAs($user)->put("/api-keys/{$b->id}", [
            'label' => 'B',
            'value' => '',
            'active' => true,
        ])->assertRedirect(route('api-keys.index'));

        $this->assertTrue($b->fresh()->active);
        $this->assertFalse($a->fresh()->active);
        $this->assertSame(1, ApiKey::where('provider', 'openai')->where('active', true)->count());
    }

    public function test_two_providers_can_each_have_one_active_key(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->post('/api-keys', [
            'provider' => 'anthropic', 'label' => 'ant', 'value' => 'sk-ant-9999', 'active' => true,
        ])->assertRedirect();
        $this->actingAs($user)->post('/api-keys', [
            'provider' => 'openai', 'label' => 'oai', 'value' => 'sk-oai-9999', 'active' => true,
        ])->assertRedirect();

        // Both providers keep exactly one active key — independent invariants.
        $this->assertSame(1, ApiKey::where('provider', 'anthropic')->where('active', true)->count());
        $this->assertSame(1, ApiKey::where('provider', 'openai')->where('active', true)->count());
        $this->assertSame(2, ApiKey::where('active', true)->count());
    }

    public function test_partial_unique_index_blocks_a_second_active_key_per_provider(): void
    {
        // DB safety net: even bypassing the controller, two active rows for the
        // same provider must be rejected by the partial unique index.
        ApiKey::create(['provider' => 'anthropic', 'value' => 'sk-1111', 'active' => true]);

        $this->expectException(\Illuminate\Database\QueryException::class);
        ApiKey::create(['provider' => 'anthropic', 'value' => 'sk-2222', 'active' => true]);
    }

    // ── B8: rotation / change history view ───────────────────────────────────

    public function test_history_view_lists_apikey_audit_rows_paginated_and_secret_free(): void
    {
        $user = User::factory()->create();

        // Generate create + deactivate (supersede) + update history.
        $this->actingAs($user)->post('/api-keys', [
            'provider' => 'anthropic', 'label' => 'A', 'value' => 'sk-ant-secret-1111', 'active' => true,
        ]);
        $this->actingAs($user)->post('/api-keys', [
            'provider' => 'anthropic', 'label' => 'B', 'value' => 'sk-ant-secret-2222', 'active' => true,
        ]);

        $response = $this->actingAs($user)->get('/api-keys/history?per_page=10');
        $response->assertOk();

        // Paginated payload shape + only apikey.* actions.
        $response->assertInertia(fn ($page) => $page
            ->component('ApiKeys/History')
            ->has('logs.data')
            ->where('logs.per_page', 10)
            ->where('state.per_page', 10)
        );

        // No key material anywhere in the rendered response.
        $body = $response->getContent();
        $this->assertStringNotContainsString('sk-ant-secret-1111', $body);
        $this->assertStringNotContainsString('sk-ant-secret-2222', $body);
        $this->assertStringNotContainsString('sk-', $body);
        $this->assertStringNotContainsString('eyJ', $body);

        // Every listed row is an apikey.* action (filtered view).
        foreach (AuditLog::where('target_type', 'apikey')->get() as $row) {
            $this->assertStringStartsWith('apikey.', $row->action);
        }
    }

    public function test_history_view_is_admin_only(): void
    {
        $viewer = User::factory()->viewer()->create();

        $this->actingAs($viewer)->get('/api-keys/history')->assertForbidden();
    }
}
