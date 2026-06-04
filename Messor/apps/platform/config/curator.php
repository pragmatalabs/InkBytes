<?php

/**
 * Curator settings safety (B9).
 *
 * Single source of truth for:
 *   - the model ALLOWLIST that `enrich_model` / `synthesize_model` are validated
 *     against (so a typo'd model id can never reach the live pipeline — a bad
 *     value here is polled by Curator per ADR-0004), and
 *   - the canonical DEFAULTS used both to seed `backoffice.curator_settings`
 *     (the create-table migration) and to power "Reset to defaults".
 *
 * These DEFAULTS mirror `Curator/apps/curator/core/config.py` (LlmCfg +
 * ClusterCfg). When Curator's config.py changes, update this file and the two
 * consumers (the migration seed + the reset action) stay in sync automatically.
 *
 * The migration `2026_06_03_000001_create_curator_settings_table.php` reads
 * `config('curator.defaults')` for its seed row, so there is one place to edit.
 */

return [
    /*
    |--------------------------------------------------------------------------
    | Allowed model ids
    |--------------------------------------------------------------------------
    |
    | Anthropic model ids the Settings page exposes as dropdowns and that the
    | update request validates against. Keep this list small and current; edit
    | here when a new Haiku/Sonnet/Opus generation ships. Free-text entry is NOT
    | allowed — the value must be one of these.
    |
    | (Enrich and synthesize share the same allowlist today; split into separate
    | keys if their valid sets ever diverge.)
    */
    'allowed_models' => [
        'enrich' => [
            'claude-haiku-4-5',
            'claude-sonnet-4-5',
            'claude-opus-4-5',
        ],
        'synthesize' => [
            'claude-haiku-4-5',
            'claude-sonnet-4-5',
            'claude-opus-4-5',
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Canonical defaults
    |--------------------------------------------------------------------------
    |
    | The source-of-truth values for a fresh install and for "Reset to
    | defaults". Mirror Curator config.py. `monthly_budget_usd` is a
    | Backoffice-only display knob (B5) and resets to unset (null).
    */
    'defaults' => [
        'enrich_model' => 'claude-haiku-4-5',
        'synthesize_model' => 'claude-haiku-4-5',
        'max_tokens_enrich' => 1500,
        'max_tokens_synth' => 2500,
        'temperature' => 0.20,
        'similarity_threshold' => 0.620,
        'entity_overlap_min' => 1,
        'min_sources_to_publish' => 2,
        'recent_window_hours' => 48,
        'monthly_budget_usd' => null,
    ],
];
