<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/**
 * CuratorSetting — the single live row of Curator tunables.
 *
 * Backoffice-owned (ADR-0001 / ADR-0003). Lives in the `backoffice` schema;
 * Curator reads it read-only and schema-qualified. Columns mirror the LLM and
 * clustering knobs in `Curator/apps/curator/core/config.py`.
 *
 * We treat row id=1 as the canonical settings row (see ::current()).
 */
class CuratorSetting extends Model
{
    protected $table = 'curator_settings';

    protected $fillable = [
        'enrich_model',
        'synthesize_model',
        'max_tokens_enrich',
        'max_tokens_synth',
        'temperature',
        'similarity_threshold',
        'entity_overlap_min',
        'min_sources_to_publish',
        'recent_window_hours',
        // B5: admin-editable monthly LLM-spend budget (USD). NULL = unset.
        // Backoffice-only display knob; Curator does not read it (ADR-0004).
        'monthly_budget_usd',
        // ADR-0004: admin-managed embedding tier. provider/model/base_url are
        // live-applied by Curator (it rebuilds its client). Vector width is
        // derived from the model (config), not stored.
        'embeddings_provider',
        'embeddings_model',
        'embeddings_base_url',
        // B15: LLM provider (anthropic | openai). Curator live-polls and rebuilds its client.
        'llm_provider',
    ];

    protected $casts = [
        'max_tokens_enrich' => 'integer',
        'max_tokens_synth' => 'integer',
        'temperature' => 'float',
        'similarity_threshold' => 'float',
        'entity_overlap_min' => 'integer',
        'min_sources_to_publish' => 'integer',
        'recent_window_hours' => 'integer',
        'monthly_budget_usd' => 'float',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    /**
     * The single live settings row. Created from defaults if somehow absent.
     */
    public static function current(): self
    {
        return static::query()->firstOrCreate(['id' => 1]);
    }
}
