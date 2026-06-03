<?php

namespace Tests\Feature;

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
}
