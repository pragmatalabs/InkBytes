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
                // ADR-0004: embedding tier (provider/model/base_url live-applied).
                'embeddings_provider' => $settings->embeddings_provider,
                'embeddings_model' => $settings->embeddings_model,
                'embeddings_base_url' => $settings->embeddings_base_url,
                // B15: LLM provider (anthropic | openai). Curator live-polls.
                'llm_provider' => $settings->llm_provider,
                'updated_at' => $settings->updated_at?->toIso8601String(),
            ],
            // B9: drive the model dropdowns from the allowlist (no free text).
            'enrichModels' => config('curator.allowed_models.enrich'),
            'synthesizeModels' => config('curator.allowed_models.synthesize'),
            // ADR-0004: embedding provider/model allowlists + derived dims (the
            // UI shows dims read-only and warns that changing width needs a
            // migration + re-embed).
            'embeddingProviders' => config('curator.allowed_embeddings.providers'),
            'embeddingModels' => config('curator.allowed_embeddings.models'),
            'embeddingDimensions' => $dimsByModel,
            // B15: LLM provider/model allowlists. The UI drives both dropdowns
            // from these so a typo'd provider or model id can never reach Curator.
            'llmProviders' => config('curator.allowed_llm.providers'),
            'llmModels' => config('curator.allowed_llm.models'),
        ]);
    }

    public function update(Request $request): RedirectResponse
    {
        $embeddingProviders = config('curator.allowed_embeddings.providers');
        $modelsByProvider = config('curator.allowed_embeddings.models');
        // Validate the embedding model against the SELECTED provider's list, so
        // (e.g.) an OpenAI model can't be saved under provider=ollama.
        $selectedProvider = $request->input('embeddings_provider');
        $allowedEmbeddingModels = $modelsByProvider[$selectedProvider]
            ?? array_merge(...array_values($modelsByProvider));

        // B15: validate enrich/synthesize models against the SELECTED LLM provider's
        // list, so (e.g.) a GPT model can't be saved under provider=anthropic.
        $llmProviders = config('curator.allowed_llm.providers');
        $llmModelsByProvider = config('curator.allowed_llm.models');
        $selectedLlmProvider = $request->input('llm_provider');
        $allowedEnrichModels = $llmModelsByProvider[$selectedLlmProvider]['enrich']
            ?? array_merge(...array_column(array_values($llmModelsByProvider), 'enrich'));
        $allowedSynthModels = $llmModelsByProvider[$selectedLlmProvider]['synthesize']
            ?? array_merge(...array_column(array_values($llmModelsByProvider), 'synthesize'));

        $data = $request->validate([
            // B15: LLM provider from the allowlist; model ids validated per-provider.
            'llm_provider' => ['required', 'string', Rule::in($llmProviders)],
            // B9 (updated B15): model ids validated against the selected LLM provider's
            // list — a typo'd id or cross-provider mismatch would otherwise be polled
            // by Curator (ADR-0004) and break the pipeline.
            'enrich_model' => ['required', 'string', Rule::in($allowedEnrichModels)],
            'synthesize_model' => ['required', 'string', Rule::in($allowedSynthModels)],
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
            // ADR-0004: embedding tier. provider + model from the allowlist;
            // base_url required for ollama (its endpoint), optional for openai.
            'embeddings_provider' => ['required', 'string', Rule::in($embeddingProviders)],
            'embeddings_model' => ['required', 'string', Rule::in($allowedEmbeddingModels)],
            'embeddings_base_url' => ['nullable', 'string', 'url', 'required_if:embeddings_provider,ollama'],
        ], [
            'llm_provider.in' => 'LLM provider must be one of: '.implode(', ', $llmProviders).'.',
            'enrich_model.in' => 'Enrich model must be one allowed for the selected LLM provider ('.($selectedLlmProvider ?? '?').'): '.implode(', ', $allowedEnrichModels).'.',
            'synthesize_model.in' => 'Synthesize model must be one allowed for the selected LLM provider ('.($selectedLlmProvider ?? '?').'): '.implode(', ', $allowedSynthModels).'.',
            'embeddings_model.in' => 'Embedding model must be one allowed for the selected provider: '.implode(', ', $allowedEmbeddingModels).'.',
            'embeddings_base_url.required_if' => 'A base URL is required for the Ollama provider (e.g. http://ollama:11434/v1).',
        ]);

        // Normalise: OpenAI uses the SDK default endpoint, so clear base_url.
        if (($data['embeddings_provider'] ?? null) === 'openai') {
            $data['embeddings_base_url'] = null;
        }

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
}
