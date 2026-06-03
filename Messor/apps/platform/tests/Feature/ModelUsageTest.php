<?php

namespace Tests\Feature;

use App\Models\ModelUsage;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Inertia\Testing\AssertableInertia;
use Tests\TestCase;

class ModelUsageTest extends TestCase
{
    use RefreshDatabase;

    public function test_dashboard_renders(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->get('/model-usage')->assertOk();
    }

    public function test_dashboard_aggregates_by_model_day_and_derived_costs(): void
    {
        $user = User::factory()->create();

        ModelUsage::insert([
            [
                'call_label' => 'enrich',
                'model' => 'claude-haiku-4-5',
                'input_tokens' => 1000,
                'output_tokens' => 200,
                'cost_usd' => 0.0020,
                'event_id' => null,
                'created_at' => '2026-06-01 10:00:00',
            ],
            [
                'call_label' => 'enrich',
                'model' => 'claude-haiku-4-5',
                'input_tokens' => 1000,
                'output_tokens' => 200,
                'cost_usd' => 0.0020,
                'event_id' => null,
                'created_at' => '2026-06-02 10:00:00',
            ],
            [
                'call_label' => 'synthesize',
                'model' => 'claude-sonnet-4-5',
                'input_tokens' => 5000,
                'output_tokens' => 600,
                'cost_usd' => 0.0060,
                'event_id' => 'evt-1',
                'created_at' => '2026-06-02 11:00:00',
            ],
        ]);

        $response = $this->actingAs($user)->get('/model-usage');

        $response->assertInertia(fn (AssertableInertia $page) => $page
            ->component('ModelUsage/Index')
            // Total spend = 0.002 + 0.002 + 0.006 = 0.010
            ->where('summary.total_cost_usd', 0.01)
            ->where('summary.total_calls', 3)
            ->where('summary.total_input_tokens', 7000)
            ->where('summary.total_output_tokens', 1000)
            // Two distinct models, haiku ranked first only if its cost is higher;
            // here sonnet (0.006) > haiku (0.004) so sonnet is first.
            ->has('byModel', 2)
            ->where('byModel.0.model', 'claude-sonnet-4-5')
            ->where('byModel.0.cost_usd', 0.006)
            ->where('byModel.1.model', 'claude-haiku-4-5')
            ->where('byModel.1.cost_usd', 0.004)
            // Two call labels.
            ->has('byLabel', 2)
            // Two distinct days (2026-06-01, 2026-06-02), newest first.
            ->has('byDay', 2)
            ->where('byDay.0.day', '2026-06-02')
            ->where('byDay.0.calls', 2)
            ->where('byDay.1.day', '2026-06-01')
            ->where('byDay.1.calls', 1)
        );
    }
}
