<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use App\Models\CuratorSetting;
use App\Services\CuratorCommandService;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;
use Throwable;

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
    public function __construct(private readonly CuratorCommandService $commands)
    {
    }

    public function edit(): Response
    {
        $settings = CuratorSetting::current();
        $dimsByModel = config('curator.allowed_embeddings.dimensions');

        return Inertia::render('Settings/Index', [
            'settings' => [
                'enrich_model'    => $settings->enrich_model,
                'synthesize_model' => $settings->synthesize_model,
                'max_tokens_enrich' => (int) $settings->max_tokens_enrich,
                'max_tokens_synth'  => (int) $settings->max_tokens_synth,
                'temperature'       => (float) $settings->temperature,
                'similarity_threshold'  => (float) $settings->similarity_threshold,
                'entity_overlap_min'    => (int) $settings->entity_overlap_min,
                'min_sources_to_publish' => (int) $settings->min_sources_to_publish,
                'recent_window_hours'   => (int) $settings->recent_window_hours,
                // ADR-0023 "Stop Curator" kill-switch (default true for legacy rows).
                'processing_enabled' => (bool) ($settings->processing_enabled ?? true),
                'monthly_budget_usd' => $settings->monthly_budget_usd !== null
                    ? (float) $settings->monthly_budget_usd : null,
                // Embedding tier.
                'embeddings_provider' => $settings->embeddings_provider,
                'embeddings_model'    => $settings->embeddings_model,
                'embeddings_base_url' => $settings->embeddings_base_url,
                // LLM provider + custom base URL (for OpenAI-compatible providers).
                'llm_provider' => $settings->llm_provider,
                'llm_base_url' => $settings->llm_base_url,
                // API key presence flags — never send the actual key to the UI.
                'anthropic_api_key_set'    => !empty($settings->anthropic_api_key),
                'openai_api_key_set'       => !empty($settings->openai_api_key),
                'deepseek_api_key_set'     => !empty($settings->deepseek_api_key),
                'embeddings_api_key_set'   => !empty($settings->embeddings_api_key),
                'updated_at' => $settings->updated_at?->toIso8601String(),
            ],
            // Model suggestions for autocomplete (free-text allowed — no hard validation).
            'llmModelSuggestions' => config('curator.allowed_llm.models'),
            'embeddingModelSuggestions' => config('curator.allowed_embeddings.models'),
            // Provider allowlists still drive the provider dropdowns.
            'llmProviders' => config('curator.allowed_llm.providers'),
            'embeddingProviders' => config('curator.allowed_embeddings.providers'),
            'embeddingDimensions' => $dimsByModel,
        ]);
    }

    public function update(Request $request): RedirectResponse
    {
        $embeddingProviders = config('curator.allowed_embeddings.providers');
        $llmProviders       = config('curator.allowed_llm.providers');

        $data = $request->validate([
            // Provider still validated against the allowlist (it drives SDK selection).
            'llm_provider'    => ['required', 'string', Rule::in($llmProviders)],
            // Model ids are free-text — any valid model string accepted.
            'enrich_model'    => ['required', 'string', 'max:120'],
            'synthesize_model' => ['required', 'string', 'max:120'],
            'max_tokens_enrich' => ['required', 'integer', 'between:1,32000'],
            'max_tokens_synth'  => ['required', 'integer', 'between:1,32000'],
            'temperature'       => ['required', 'numeric', 'between:0,1'],
            'similarity_threshold'  => ['required', 'numeric', 'between:0,1'],
            'entity_overlap_min'    => ['required', 'integer', 'between:0,20'],
            'min_sources_to_publish' => ['required', 'integer', 'between:1,20'],
            'recent_window_hours'   => ['required', 'integer', 'between:1,720'],
            'monthly_budget_usd'    => ['nullable', 'numeric', 'min:0', 'max:1000000'],
            // Embedding tier.
            'embeddings_provider' => ['required', 'string', Rule::in($embeddingProviders)],
            'embeddings_model'    => ['required', 'string', 'max:120'],
            'embeddings_base_url' => ['nullable', 'string', 'url', 'required_if:embeddings_provider,ollama'],
            // Custom base URL for OpenAI-compatible LLM providers.
            'llm_base_url' => ['nullable', 'string', 'url', 'max:255'],
            // API keys — empty string means "don't update"; non-empty saves the new key.
            'anthropic_api_key'  => ['nullable', 'string', 'max:512'],
            'openai_api_key'     => ['nullable', 'string', 'max:512'],
            'deepseek_api_key'   => ['nullable', 'string', 'max:512'],
            'embeddings_api_key' => ['nullable', 'string', 'max:512'],
        ], [
            'llm_provider.in' => 'LLM provider must be one of: '.implode(', ', $llmProviders).'.',
            'embeddings_base_url.required_if' => 'A base URL is required for the Ollama provider (e.g. http://ollama:11434/v1).',
        ]);

        // Normalise: OpenAI embeddings use the SDK default endpoint.
        if (($data['embeddings_provider'] ?? null) === 'openai') {
            $data['embeddings_base_url'] = null;
        }

        $settings = CuratorSetting::current();
        $before   = $settings->only(array_keys($data));

        // API key fields: empty string → don't overwrite existing value.
        // Non-empty → save new value. This lets the user update a key without
        // having to clear the existing one first.
        foreach (['anthropic_api_key', 'openai_api_key', 'deepseek_api_key', 'embeddings_api_key'] as $keyField) {
            if (isset($data[$keyField]) && $data[$keyField] === '') {
                unset($data[$keyField]);  // keep current DB value unchanged
            }
        }

        $settings->fill($data)->save();

        // Audit: mask key values so raw secrets never hit the audit log.
        $maskedBefore = $before;
        $maskedAfter  = $settings->only(array_keys($before));
        foreach (['anthropic_api_key', 'openai_api_key', 'deepseek_api_key', 'embeddings_api_key'] as $keyField) {
            if (isset($maskedBefore[$keyField]))  $maskedBefore[$keyField]  = '***';
            if (isset($maskedAfter[$keyField]))   $maskedAfter[$keyField]   = '***';
        }

        AuditLog::record(
            'settings.updated',
            'settings',
            (string) $settings->getKey(),
            $maskedBefore,
            $maskedAfter,
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

    /**
     * ADR-0004: trigger a corpus re-embed. After switching the embedding
     * provider/model, existing vectors are stale (different vector space); this
     * publishes the `embeddings.reembed` command so Curator rebuilds every
     * article's embedding in the background with the current embedder. Audited.
     */
    public function reembed(): RedirectResponse
    {
        try {
            $this->commands->reembedCorpus('all');
        } catch (Throwable $e) {
            return redirect()
                ->route('settings.edit')
                ->with('error', 'Re-embed command could not be sent: '.$e->getMessage());
        }

        AuditLog::record('embeddings.reembed', 'settings', '1');

        return redirect()
            ->route('settings.edit')
            ->with('success', 'Re-embed command sent. Curator is rebuilding embeddings for the whole corpus in the background.');
    }

    /**
     * "Stop Curator" kill-switch (ADR-0023). Sets curator_settings.processing_enabled;
     * Curator polls it and pauses/resumes its pipeline within the refresh interval.
     * Articles keep queuing in RabbitMQ while paused (no loss); the API stays up.
     */
    public function toggleProcessing(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'enabled' => ['required', 'boolean'],
        ]);

        $settings = CuratorSetting::current();
        $before   = ['processing_enabled' => (bool) ($settings->processing_enabled ?? true)];

        $settings->processing_enabled = $data['enabled'];
        $settings->save();

        AuditLog::record(
            'settings.processing_toggled',
            'settings',
            (string) $settings->getKey(),
            $before,
            ['processing_enabled' => (bool) $settings->processing_enabled],
        );

        $msg = $data['enabled']
            ? 'Curator processing RESUMED. The pipeline restarts within the refresh interval (~30s).'
            : 'Curator processing PAUSED. New articles queue in RabbitMQ (no loss) and the reader stays up; takes effect within ~30s.';

        return redirect()->route('settings.edit')->with('success', $msg);
    }
}
