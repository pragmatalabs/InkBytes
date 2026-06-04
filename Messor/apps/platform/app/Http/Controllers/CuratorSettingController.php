<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use App\Models\CuratorSetting;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;

/**
 * Edit the single live `curator_settings` row (Backoffice-owned, ADR-0003).
 *
 * Curator polls this table and picks up changes within its refresh interval
 * (no redeploy needed — ADR-0004 / backend-architecture §6). This controller
 * only writes the row; it does not touch Curator's `public` pipeline tables.
 *
 * B9 (settings safety): model ids are validated against an allowlist in
 * `config/curator.php` (a typo here would otherwise reach the live pipeline),
 * numeric knobs are range-checked, and a "reset to defaults" action restores
 * the canonical values from that same config (single source of truth shared
 * with the create-table migration's seed).
 */
class CuratorSettingController extends Controller
{
    public function edit(): Response
    {
        $settings = CuratorSetting::current();

        return Inertia::render('Settings/Index', [
            'settings' => [
                'enrich_model' => $settings->enrich_model,
                'synthesize_model' => $settings->synthesize_model,
                'max_tokens_enrich' => (int) $settings->max_tokens_enrich,
                'max_tokens_synth' => (int) $settings->max_tokens_synth,
                'temperature' => (float) $settings->temperature,
                'similarity_threshold' => (float) $settings->similarity_threshold,
                'entity_overlap_min' => (int) $settings->entity_overlap_min,
                'min_sources_to_publish' => (int) $settings->min_sources_to_publish,
                'recent_window_hours' => (int) $settings->recent_window_hours,
                // B5: monthly budget (USD). Null when unset → budget widget hides.
                'monthly_budget_usd' => $settings->monthly_budget_usd !== null
                    ? (float) $settings->monthly_budget_usd
                    : null,
                'updated_at' => $settings->updated_at?->toIso8601String(),
            ],
            // B9: drive the model dropdowns from the allowlist (no free text).
            'enrichModels' => config('curator.allowed_models.enrich'),
            'synthesizeModels' => config('curator.allowed_models.synthesize'),
        ]);
    }

    public function update(Request $request): RedirectResponse
    {
        $enrichModels = config('curator.allowed_models.enrich');
        $synthesizeModels = config('curator.allowed_models.synthesize');

        $data = $request->validate([
            // B9: model ids must be on the allowlist — a typo'd id would
            // otherwise be polled by Curator (ADR-0004) and break the pipeline.
            'enrich_model' => ['required', 'string', Rule::in($enrichModels)],
            'synthesize_model' => ['required', 'string', Rule::in($synthesizeModels)],
            'max_tokens_enrich' => ['required', 'integer', 'between:1,32000'],
            'max_tokens_synth' => ['required', 'integer', 'between:1,32000'],
            'temperature' => ['required', 'numeric', 'between:0,1'],
            'similarity_threshold' => ['required', 'numeric', 'between:0,1'],
            'entity_overlap_min' => ['required', 'integer', 'between:0,20'],
            'min_sources_to_publish' => ['required', 'integer', 'between:1,20'],
            'recent_window_hours' => ['required', 'integer', 'between:1,720'],
            // B5: optional monthly budget in USD. Nullable (no budget) and
            // small budgets allowed (tests use $0.001), so min is 0.
            'monthly_budget_usd' => ['nullable', 'numeric', 'min:0', 'max:1000000'],
        ], [
            'enrich_model.in' => 'Enrich model must be one of the allowed Anthropic model ids: '.implode(', ', $enrichModels).'.',
            'synthesize_model.in' => 'Synthesize model must be one of the allowed Anthropic model ids: '.implode(', ', $synthesizeModels).'.',
        ]);

        $settings = CuratorSetting::current();
        $before = $settings->only(array_keys($data));
        $settings->fill($data)->save();

        AuditLog::record(
            'settings.updated',
            'settings',
            (string) $settings->getKey(),
            $before,
            $settings->only(array_keys($data)),
        );

        return redirect()
            ->route('settings.edit')
            ->with('success', 'Curator settings saved. Changes take effect within Curator\'s refresh interval (no redeploy).');
    }

    /**
     * B9: restore the canonical defaults from `config/curator.php` (the same
     * source the create-table migration seeds from). Audited via B1.
     */
    public function reset(): RedirectResponse
    {
        $defaults = config('curator.defaults');

        $settings = CuratorSetting::current();
        $before = $settings->only(array_keys($defaults));
        $settings->fill($defaults)->save();

        AuditLog::record(
            'settings.reset',
            'settings',
            (string) $settings->getKey(),
            $before,
            $settings->only(array_keys($defaults)),
        );

        return redirect()
            ->route('settings.edit')
            ->with('success', 'Curator settings reset to defaults. Changes take effect within Curator\'s refresh interval (no redeploy).');
    }
}
