<?php

namespace Tests\Feature;

use App\Models\AuditLog;
use App\Models\CuratorSetting;
use App\Models\User;
use App\Services\CuratorCommandService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery;
use Tests\TestCase;

class CuratorSettingsTest extends TestCase
{
    use RefreshDatabase;

    public function test_settings_page_is_displayed(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->get('/settings')->assertOk();
    }

    public function test_settings_can_be_updated(): void
    {
        $user = User::factory()->create();

        $response = $this->actingAs($user)->put('/settings', $this->validPayload([
            'synthesize_model' => 'claude-sonnet-4-5',
            'max_tokens_enrich' => 1200,
            'max_tokens_synth' => 3000,
            'temperature' => 0.35,
            'similarity_threshold' => 0.7,
            'entity_overlap_min' => 2,
            'min_sources_to_publish' => 3,
            'recent_window_hours' => 72,
        ]));

        $response->assertRedirect(route('settings.edit'));

        $settings = CuratorSetting::current();
        $this->assertSame('claude-sonnet-4-5', $settings->synthesize_model);
        $this->assertSame(3, $settings->min_sources_to_publish);
        $this->assertEqualsWithDelta(0.35, $settings->temperature, 0.0001);
    }

    public function test_settings_validation_rejects_out_of_range(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload(['temperature' => 9.0])) // out of 0..1
            ->assertSessionHasErrors('temperature');
    }

    // ── ADR-0004: embedding tier ──────────────────────────────────────────

    /** Embedding provider/model/base_url persist. */
    public function test_update_persists_embedding_settings(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload([
                'embeddings_provider' => 'ollama',
                'embeddings_model' => 'mxbai-embed-large',
                'embeddings_base_url' => 'http://ollama:11434/v1',
            ]))
            ->assertRedirect(route('settings.edit'))
            ->assertSessionHasNoErrors();

        $s = CuratorSetting::current();
        $this->assertSame('ollama', $s->embeddings_provider);
        $this->assertSame('mxbai-embed-large', $s->embeddings_model);
        $this->assertSame('http://ollama:11434/v1', $s->embeddings_base_url);
    }

    /** An unknown embedding provider is rejected. */
    public function test_update_rejects_unknown_embedding_provider(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload(['embeddings_provider' => 'cohere']))
            ->assertSessionHasErrors('embeddings_provider');
    }

    /** A model not allowed for the selected provider is rejected. */
    public function test_update_rejects_model_not_allowed_for_provider(): void
    {
        $user = User::factory()->create();

        // OpenAI model under the ollama provider → invalid.
        $this->actingAs($user)
            ->put('/settings', $this->validPayload([
                'embeddings_provider' => 'ollama',
                'embeddings_model' => 'text-embedding-3-small',
            ]))
            ->assertSessionHasErrors('embeddings_model');
    }

    /** Ollama requires a base URL. */
    public function test_update_requires_base_url_for_ollama(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload([
                'embeddings_provider' => 'ollama',
                'embeddings_model' => 'bge-m3',
                'embeddings_base_url' => '',
            ]))
            ->assertSessionHasErrors('embeddings_base_url');
    }

    /** OpenAI stores no base_url (uses the SDK default endpoint). */
    public function test_update_clears_base_url_for_openai(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload([
                'embeddings_provider' => 'openai',
                'embeddings_model' => 'text-embedding-3-small',
                'embeddings_base_url' => 'http://should-be-ignored/v1',
            ]))
            ->assertRedirect(route('settings.edit'))
            ->assertSessionHasNoErrors();

        $this->assertNull(CuratorSetting::current()->embeddings_base_url);
    }

    /** Re-embed publishes the embeddings.reembed command and is audited. */
    public function test_reembed_publishes_command_and_audits(): void
    {
        $user = User::factory()->create();

        $mock = Mockery::mock(CuratorCommandService::class);
        $mock->shouldReceive('reembedCorpus')->once()->with('all')->andReturnTrue();
        $this->app->instance(CuratorCommandService::class, $mock);

        $this->actingAs($user)
            ->post('/settings/reembed')
            ->assertRedirect(route('settings.edit'))
            ->assertSessionHasNoErrors();

        $this->assertSame(1, AuditLog::where('action', 'embeddings.reembed')->count());
    }

    /** B9: a model id off the allowlist is rejected. */
    public function test_update_rejects_model_not_on_allowlist(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload(['enrich_model' => 'not-a-model']))
            ->assertSessionHasErrors('enrich_model');
    }

    /** B9: an allowlisted model id is accepted and saved. */
    public function test_update_accepts_allowlisted_model(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload(['synthesize_model' => 'claude-sonnet-4-5']))
            ->assertRedirect(route('settings.edit'))
            ->assertSessionHasNoErrors();

        $this->assertSame('claude-sonnet-4-5', CuratorSetting::current()->synthesize_model);
    }

    /** B9: temperature above 1 is rejected (range is 0..1). */
    public function test_update_rejects_temperature_above_one(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload(['temperature' => 5]))
            ->assertSessionHasErrors('temperature');
    }

    /** B9: min_sources_to_publish must be >= 1. */
    public function test_update_rejects_min_sources_below_one(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload(['min_sources_to_publish' => 0]))
            ->assertSessionHasErrors('min_sources_to_publish');
    }

    /** B9: reset restores the canonical defaults and writes a B1 audit row. */
    public function test_reset_restores_defaults_and_is_audited(): void
    {
        $user = User::factory()->create();

        // Move the live row away from defaults first.
        CuratorSetting::current()->fill([
            'enrich_model' => 'claude-sonnet-4-5',
            'synthesize_model' => 'claude-opus-4-5',
            'max_tokens_enrich' => 999,
            'temperature' => 0.9,
            'similarity_threshold' => 0.9,
            'min_sources_to_publish' => 5,
            'recent_window_hours' => 12,
            'monthly_budget_usd' => 42.5,
        ])->save();

        $this->actingAs($user)
            ->post('/settings/reset')
            ->assertRedirect(route('settings.edit'))
            ->assertSessionHasNoErrors();

        $settings = CuratorSetting::current();
        $defaults = config('curator.defaults');

        $this->assertSame($defaults['enrich_model'], $settings->enrich_model);
        $this->assertSame($defaults['synthesize_model'], $settings->synthesize_model);
        $this->assertSame($defaults['max_tokens_enrich'], $settings->max_tokens_enrich);
        $this->assertEqualsWithDelta($defaults['temperature'], $settings->temperature, 0.0001);
        $this->assertEqualsWithDelta($defaults['similarity_threshold'], $settings->similarity_threshold, 0.0001);
        $this->assertSame($defaults['min_sources_to_publish'], $settings->min_sources_to_publish);
        $this->assertSame($defaults['recent_window_hours'], $settings->recent_window_hours);
        $this->assertNull($settings->monthly_budget_usd);

        $this->assertSame(1, AuditLog::where('action', 'settings.reset')->count());
    }

    // ── B15: LLM provider switching ──────────────────────────────────────

    /** B15: llm_provider=openai with a valid OpenAI model persists. */
    public function test_update_persists_llm_provider(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload([
                'llm_provider' => 'openai',
                'enrich_model' => 'gpt-4o-mini',
                'synthesize_model' => 'gpt-4o-mini',
            ]))
            ->assertRedirect(route('settings.edit'))
            ->assertSessionHasNoErrors();

        $s = CuratorSetting::current();
        $this->assertSame('openai', $s->llm_provider);
        $this->assertSame('gpt-4o-mini', $s->enrich_model);
        $this->assertSame('gpt-4o-mini', $s->synthesize_model);
    }

    /** B15: an unknown LLM provider is rejected. */
    public function test_update_rejects_unknown_llm_provider(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->put('/settings', $this->validPayload(['llm_provider' => 'cohere']))
            ->assertSessionHasErrors('llm_provider');
    }

    /** B15: an OpenAI model under provider=anthropic is rejected. */
    public function test_update_rejects_model_not_allowed_for_llm_provider(): void
    {
        $user = User::factory()->create();

        // gpt-4o-mini is an OpenAI model — invalid under provider=anthropic.
        $this->actingAs($user)
            ->put('/settings', $this->validPayload([
                'llm_provider' => 'anthropic',
                'enrich_model' => 'gpt-4o-mini',
            ]))
            ->assertSessionHasErrors('enrich_model');
    }

    /** B15: reset includes llm_provider = 'anthropic' (the default). */
    public function test_reset_includes_llm_provider(): void
    {
        $user = User::factory()->create();

        // Move the row to OpenAI first so we can verify the reset.
        CuratorSetting::current()->fill([
            'llm_provider' => 'openai',
            'enrich_model' => 'gpt-4o-mini',
            'synthesize_model' => 'gpt-4o-mini',
        ])->save();

        $this->actingAs($user)
            ->post('/settings/reset')
            ->assertRedirect(route('settings.edit'))
            ->assertSessionHasNoErrors();

        $this->assertSame('anthropic', CuratorSetting::current()->llm_provider);
    }

    /**
     * A full, valid update payload with optional overrides.
     *
     * @param  array<string, mixed>  $overrides
     * @return array<string, mixed>
     */
    private function validPayload(array $overrides = []): array
    {
        return array_merge([
            // B15: LLM provider (now required by the update validation).
            'llm_provider' => 'anthropic',
            'enrich_model' => 'claude-haiku-4-5',
            'synthesize_model' => 'claude-haiku-4-5',
            'max_tokens_enrich' => 1500,
            'max_tokens_synth' => 2500,
            'temperature' => 0.2,
            'similarity_threshold' => 0.62,
            'entity_overlap_min' => 1,
            'min_sources_to_publish' => 2,
            'recent_window_hours' => 48,
            // ADR-0004: embedding tier (now required by the update validation).
            'embeddings_provider' => 'ollama',
            'embeddings_model' => 'bge-m3',
            'embeddings_base_url' => 'http://localhost:11434/v1',
        ], $overrides);
    }
}
