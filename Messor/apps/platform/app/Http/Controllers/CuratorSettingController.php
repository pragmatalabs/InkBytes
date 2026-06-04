<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use App\Models\CuratorSetting;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

/**
 * Edit the single live `curator_settings` row (Backoffice-owned, ADR-0003).
 *
 * Curator polls this table and picks up changes within its refresh interval
 * (no redeploy needed — ADR-0004 / backend-architecture §6). This controller
 * only writes the row; it does not touch Curator's `public` pipeline tables.
 */
class CuratorSettingController extends Controller
{
    private const KNOWN_MODELS = [
        'claude-haiku-4-5',
        'claude-sonnet-4-5',
        'claude-opus-4-1',
    ];

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
                'updated_at' => $settings->updated_at?->toIso8601String(),
            ],
            'modelSuggestions' => self::KNOWN_MODELS,
        ]);
    }

    public function update(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'enrich_model' => ['required', 'string', 'max:120'],
            'synthesize_model' => ['required', 'string', 'max:120'],
            'max_tokens_enrich' => ['required', 'integer', 'between:1,32000'],
            'max_tokens_synth' => ['required', 'integer', 'between:1,32000'],
            'temperature' => ['required', 'numeric', 'between:0,2'],
            'similarity_threshold' => ['required', 'numeric', 'between:0,1'],
            'entity_overlap_min' => ['required', 'integer', 'between:0,20'],
            'min_sources_to_publish' => ['required', 'integer', 'between:1,20'],
            'recent_window_hours' => ['required', 'integer', 'between:1,720'],
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
}
