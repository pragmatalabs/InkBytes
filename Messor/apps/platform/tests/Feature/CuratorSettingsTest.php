<?php

namespace Tests\Feature;

use App\Models\AuditLog;
use App\Models\CuratorSetting;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
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

        $response = $this->actingAs($user)->put('/settings', [
            'enrich_model' => 'claude-haiku-4-5',
            'synthesize_model' => 'claude-sonnet-4-5',
            'max_tokens_enrich' => 1200,
            'max_tokens_synth' => 3000,
            'temperature' => 0.35,
            'similarity_threshold' => 0.7,
            'entity_overlap_min' => 2,
            'min_sources_to_publish' => 3,
            'recent_window_hours' => 72,
        ]);

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
            ->put('/settings', [
                'enrich_model' => 'claude-haiku-4-5',
                'synthesize_model' => 'claude-haiku-4-5',
                'max_tokens_enrich' => 1200,
                'max_tokens_synth' => 3000,
                'temperature' => 9.0, // out of 0..2
                'similarity_threshold' => 0.7,
                'entity_overlap_min' => 2,
                'min_sources_to_publish' => 3,
                'recent_window_hours' => 72,
            ])
            ->assertSessionHasErrors('temperature');
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

    /**
     * A full, valid update payload with optional overrides.
     *
     * @param  array<string, mixed>  $overrides
     * @return array<string, mixed>
     */
    private function validPayload(array $overrides = []): array
    {
        return array_merge([
            'enrich_model' => 'claude-haiku-4-5',
            'synthesize_model' => 'claude-haiku-4-5',
            'max_tokens_enrich' => 1500,
            'max_tokens_synth' => 2500,
            'temperature' => 0.2,
            'similarity_threshold' => 0.62,
            'entity_overlap_min' => 1,
            'min_sources_to_publish' => 2,
            'recent_window_hours' => 48,
        ], $overrides);
    }
}
