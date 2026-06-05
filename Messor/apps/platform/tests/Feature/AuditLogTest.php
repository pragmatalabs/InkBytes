<?php

namespace Tests\Feature;

use App\Models\ApiKey;
use App\Models\AuditLog;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

/**
 * B1 — Audit log: every state-changing admin action records who did what to
 * which target, with secret-free before/after snapshots.
 */
class AuditLogTest extends TestCase
{
    use RefreshDatabase;

    public function test_audit_index_is_displayed(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->get('/audit-log')->assertOk();
    }

    /**
     * The recorder snapshots the authenticated user + IP and persists
     * before/after JSON. (The outlet HTTP routes exercise the same recorder;
     * they cannot run here because `public.outlets` lives in Postgres, not the
     * SQLite test DB — outlet wiring is verified against Postgres via tinker.)
     */
    public function test_recorder_snapshots_actor_and_before_after(): void
    {
        $user = User::factory()->create();
        Auth::login($user);

        AuditLog::record(
            'outlet.updated',
            'outlet',
            'test-outlet',
            ['display_name' => 'Test Outlet', 'priority' => 2],
            ['display_name' => 'Renamed Outlet', 'priority' => 1],
        );

        $log = AuditLog::query()->where('action', 'outlet.updated')->firstOrFail();

        $this->assertSame($user->getKey(), $log->actor_id);
        $this->assertSame($user->name, $log->actor_name);
        $this->assertSame($user->email, $log->actor_email);
        $this->assertSame('outlet', $log->target_type);
        $this->assertSame('test-outlet', $log->target_id);
        $this->assertSame('Test Outlet', $log->before['display_name']);
        $this->assertSame('Renamed Outlet', $log->after['display_name']);
        $this->assertSame(2, $log->before['priority']);
        $this->assertSame(1, $log->after['priority']);
        $this->assertNotNull($log->created_at);
    }

    /**
     * An audit write failure must never bubble up and break the audited action.
     */
    public function test_recorder_is_best_effort_and_never_throws(): void
    {
        // Force the insert to fail by removing the table, then confirm record()
        // swallows the error instead of bubbling a 500-worthy exception.
        \Illuminate\Support\Facades\Schema::drop('audit_logs');

        AuditLog::record('outlet.deleted', 'outlet', 'gone', ['x' => 1], null);

        $this->assertTrue(true);
    }

    public function test_apikey_actions_are_audited_without_any_key_material(): void
    {
        $user = User::factory()->create();
        $secret = 'sk-super-secret-abcd1234';

        // CREATE
        $this->actingAs($user)->post('/api-keys', [
            'provider' => 'openai',
            'label' => 'prod',
            'value' => $secret,
            'active' => true,
        ])->assertRedirect(route('api-keys.index'));

        $key = ApiKey::first();

        // UPDATE (rotate to a new secret)
        $newSecret = 'sk-rotated-secret-wxyz9999';
        $this->actingAs($user)->put("/api-keys/{$key->id}", [
            'label' => 'prod-rotated',
            'value' => $newSecret,
            'active' => false,
        ])->assertRedirect(route('api-keys.index'));

        // DELETE
        $this->actingAs($user)->delete("/api-keys/{$key->id}")->assertRedirect();

        $apikeyLogs = AuditLog::query()->where('target_type', 'apikey')->get();
        $this->assertCount(3, $apikeyLogs);

        // Prove NO key material is ever persisted in any audit row — scan the
        // raw stored before/after JSON columns for either secret.
        $rawRows = DB::table('audit_logs')->where('target_type', 'apikey')->get();
        foreach ($rawRows as $row) {
            $blob = ($row->before ?? '').'|'.($row->after ?? '');
            $this->assertStringNotContainsString($secret, $blob);
            $this->assertStringNotContainsString($newSecret, $blob);
            $this->assertStringNotContainsString('sk-', $blob);
        }

        // What IS recorded: provider, label, masked last-4, active.
        $created = $apikeyLogs->firstWhere('action', 'apikey.created');
        $this->assertSame('openai', $created->after['provider']);
        $this->assertSame('prod', $created->after['label']);
        $this->assertArrayHasKey('masked', $created->after);
        $this->assertStringEndsWith('1234', $created->after['masked']);
        $this->assertArrayNotHasKey('value', $created->after);

        $updated = $apikeyLogs->firstWhere('action', 'apikey.updated');
        $this->assertSame('prod', $updated->before['label']);
        $this->assertSame('prod-rotated', $updated->after['label']);
        $this->assertStringEndsWith('9999', $updated->after['masked']);
    }

    public function test_settings_update_is_audited_with_diff(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->put('/settings', [
            // B15: LLM provider (now required by the update validation).
            'llm_provider' => 'anthropic',
            'enrich_model' => 'claude-haiku-4-5',
            'synthesize_model' => 'claude-haiku-4-5',
            'max_tokens_enrich' => 1000,
            'max_tokens_synth' => 2000,
            'temperature' => 0.3,
            'similarity_threshold' => 0.8,
            'entity_overlap_min' => 2,
            'min_sources_to_publish' => 2,
            'recent_window_hours' => 48,
            // ADR-0004: embedding tier (required by the update validation).
            'embeddings_provider' => 'ollama',
            'embeddings_model' => 'bge-m3',
            'embeddings_base_url' => 'http://localhost:11434/v1',
        ])->assertRedirect(route('settings.edit'));

        $log = AuditLog::query()->where('action', 'settings.updated')->first();
        $this->assertNotNull($log);
        $this->assertSame('settings', $log->target_type);
        $this->assertSame($user->email, $log->actor_email);
        $this->assertSame(48, $log->after['recent_window_hours']);
    }
}
