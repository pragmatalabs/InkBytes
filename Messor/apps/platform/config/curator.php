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
    | Allowed embedding providers + models (ADR-0004)
    |--------------------------------------------------------------------------
    |
    | The Settings page drives provider + model dropdowns from these lists and
    | the update request validates against them (no free text). Curator polls
    | provider/model/base_url and LIVE-rebuilds its embedding client.
    |
    | `dimensions` is the pgvector column width each model implies — DERIVED, not
    | stored: it's shown read-only in the UI and is a MIGRATION concern, not a
    | hot-reload knob. Curator refuses a model whose width != the live
    | articles.embedding column (it would break every INSERT). Switching to a
    | different-width model requires a vector-width migration + full re-embed.
    */
    'allowed_embeddings' => [
        'providers' => ['ollama', 'openai'],
        'models' => [
            'ollama' => ['bge-m3', 'nomic-embed-text', 'mxbai-embed-large'],
            'openai' => ['text-embedding-3-small', 'text-embedding-3-large'],
        ],
        'dimensions' => [
            'bge-m3' => 1024,
            'nomic-embed-text' => 768,
            'mxbai-embed-large' => 1024,
            'text-embedding-3-small' => 1536,
            'text-embedding-3-large' => 3072,
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
        // Embeddings (ADR-0004). Local-first default: Ollama bge-m3 (1024d).
        'embeddings_provider' => 'ollama',
        'embeddings_model' => 'bge-m3',
        'embeddings_base_url' => 'http://localhost:11434/v1',
    ],

    /*
    |--------------------------------------------------------------------------
    | Alerting thresholds (B11)
    |--------------------------------------------------------------------------
    |
    | Thresholds the scheduled `alerts:evaluate` evaluator reads when checking
    | each rule against the existing B3/B4/B5/B6 signal sources. Keep the knobs
    | here (not hard-coded in the command) so ops can tune them in one place.
    |
    |   stale_outlet_hours    — an ACTIVE outlet whose latest public.articles
    |                           scrape is older than this (or never scraped) is
    |                           "stale". One alert per outlet.
    |   low_success_rate      — latest Messor session success_rate (0..1) below
    |                           this raises scrape_low_success (defensive HTTP;
    |                           skipped if Messor is unreachable).
    |   pipeline_stalled_hours— no harvest (MAX public.articles.scraped_at) in
    |                           this many hours raises pipeline_stalled.
    |   queue_backlog         — total RabbitMQ depth across the key queues above
    |                           this also raises pipeline_stalled.
    |
    | over_budget has no threshold here — it fires deterministically when MTD
    | model_usage cost exceeds curator_settings.monthly_budget_usd (skipped when
    | the budget is null).
    */
    'alerts' => [
        'stale_outlet_hours' => env('ALERT_STALE_OUTLET_HOURS', 24),
        'low_success_rate' => env('ALERT_LOW_SUCCESS_RATE', 0.5),
        'pipeline_stalled_hours' => env('ALERT_PIPELINE_STALLED_HOURS', 6),
        'queue_backlog' => env('ALERT_QUEUE_BACKLOG', 1000),
    ],
];
