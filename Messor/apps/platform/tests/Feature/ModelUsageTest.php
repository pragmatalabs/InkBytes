<?php

namespace Tests\Feature;

use App\Models\AuditLog;
use App\Models\CuratorSetting;
use App\Models\ModelUsage;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Carbon;
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

        // Explicit range covering the seeded rows so the assertion is stable
        // regardless of the wall clock (default range is the last 30 days).
        $response = $this->actingAs($user)->get('/model-usage?from=2026-06-01&to=2026-06-02');

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

    public function test_date_range_filter_scopes_all_aggregates(): void
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
                'created_at' => '2026-05-01 10:00:00',
            ],
            [
                'call_label' => 'synthesize',
                'model' => 'claude-sonnet-4-5',
                'input_tokens' => 5000,
                'output_tokens' => 600,
                'cost_usd' => 0.0060,
                'event_id' => 'evt-1',
                'created_at' => '2026-06-03 11:00:00',
            ],
        ]);

        // Wide range: both rows are included.
        $this->actingAs($user)
            ->get('/model-usage?from=2026-05-01&to=2026-06-03')
            ->assertInertia(fn (AssertableInertia $page) => $page
                ->where('summary.total_cost_usd', 0.008)
                ->where('summary.total_calls', 2)
                ->has('byModel', 2)
            );

        // Narrow range that EXCLUDES the 2026-06-03 row → zeros.
        $this->actingAs($user)
            ->get('/model-usage?from=2026-04-01&to=2026-04-30')
            ->assertInertia(fn (AssertableInertia $page) => $page
                // 0.0 serializes to JSON 0; compare numerically, not strictly.
                ->where('summary.total_cost_usd', fn ($v) => (float) $v === 0.0)
                ->where('summary.total_calls', 0)
                ->has('byModel', 0)
                // byEvent is now a server paginator (B7): rows live under .data.
                ->has('byEvent.events.data', 0)
            );

        // Range capturing ONLY the 2026-06-03 row → just the synth row.
        $this->actingAs($user)
            ->get('/model-usage?from=2026-06-03&to=2026-06-03')
            ->assertInertia(fn (AssertableInertia $page) => $page
                ->where('summary.total_cost_usd', 0.006)
                ->where('summary.total_calls', 1)
                ->has('byEvent.events.data', 1)
                ->where('byEvent.events.data.0.event_id', 'evt-1')
            );
    }

    public function test_csv_export_returns_filtered_rows(): void
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
                'created_at' => '2026-05-01 10:00:00',
            ],
            [
                'call_label' => 'synthesize',
                'model' => 'claude-sonnet-4-5',
                'input_tokens' => 5000,
                'output_tokens' => 600,
                'cost_usd' => 0.0060,
                'event_id' => 'evt-1',
                'created_at' => '2026-06-03 11:00:00',
            ],
        ]);

        $response = $this->actingAs($user)
            ->get('/model-usage/export?from=2026-06-01&to=2026-06-30');

        $response->assertOk();
        $this->assertStringContainsString('text/csv', $response->headers->get('Content-Type'));

        $body = $response->streamedContent();
        $lines = array_values(array_filter(explode("\n", trim($body))));

        // Header row + exactly one data row (only the June row is in range).
        $this->assertSame(
            'created_at,call_label,model,input_tokens,output_tokens,cost_usd,event_id',
            $lines[0]
        );
        $this->assertCount(2, $lines);
        $this->assertStringContainsString('synthesize', $lines[1]);
        $this->assertStringContainsString('evt-1', $lines[1]);
        $this->assertStringContainsString('0.006000', $lines[1]);
        // The out-of-range May row must not appear.
        $this->assertStringNotContainsString('2026-05-01', $body);
    }

    public function test_budget_widget_flags_over_and_under_budget(): void
    {
        $user = User::factory()->create();

        // A spend in the current month so MTD picks it up.
        ModelUsage::insert([
            [
                'call_label' => 'synthesize',
                'model' => 'claude-haiku-4-5',
                'input_tokens' => 100,
                'output_tokens' => 50,
                'cost_usd' => 0.0050,
                'event_id' => 'evt-now',
                'created_at' => Carbon::now()->toDateTimeString(),
            ],
        ]);

        // No budget set → widget hidden.
        $this->actingAs($user)
            ->get('/model-usage')
            ->assertInertia(fn (AssertableInertia $page) => $page->where('budget', null));

        // Tiny budget → over budget.
        CuratorSetting::current()->forceFill(['monthly_budget_usd' => 0.001])->save();
        $this->actingAs($user)
            ->get('/model-usage')
            ->assertInertia(fn (AssertableInertia $page) => $page
                ->where('budget.over_budget', true)
                ->where('budget.budget_usd', 0.001)
            );

        // Large budget → within budget.
        CuratorSetting::current()->forceFill(['monthly_budget_usd' => 100])->save();
        $this->actingAs($user)
            ->get('/model-usage')
            ->assertInertia(fn (AssertableInertia $page) => $page
                ->where('budget.over_budget', false)
            );
    }

    public function test_budget_update_via_settings_writes_audit_row(): void
    {
        $admin = User::factory()->admin()->create();

        $response = $this->actingAs($admin)->put('/settings', [
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
            'monthly_budget_usd' => 12.5,
            // ADR-0004: embedding tier (required by the update validation).
            'embeddings_provider' => 'ollama',
            'embeddings_model' => 'bge-m3',
            'embeddings_base_url' => 'http://localhost:11434/v1',
        ]);

        $response->assertRedirect(route('settings.edit'));

        $this->assertEqualsWithDelta(
            12.5,
            (float) CuratorSetting::current()->monthly_budget_usd,
            0.0001
        );

        $audit = AuditLog::query()->where('action', 'settings.updated')->latest('id')->first();
        $this->assertNotNull($audit);
        $this->assertSame(12.5, (float) ($audit->after['monthly_budget_usd'] ?? null));
    }
}
