<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/**
 * ModelUsage — one row per completed Curator LLM call (tokens + cost).
 *
 * Backoffice-owned DDL (ADR-0003); lives in the `backoffice` schema. Curator
 * writes rows directly via asyncpg (schema-qualified INSERT); the Backoffice
 * reads them for the cost dashboard. Read-only from the admin's perspective —
 * there is no UI to create/edit/delete usage rows.
 *
 * `created_at` is set by the writer (Curator), so Eloquent's automatic
 * timestamps are disabled and `updated_at` does not exist.
 */
class ModelUsage extends Model
{
    protected $table = 'model_usage';

    public $timestamps = false;

    protected $fillable = [
        'call_label',
        'model',
        'input_tokens',
        'output_tokens',
        'cost_usd',
        'event_id',
        'created_at',
    ];

    protected $casts = [
        'input_tokens' => 'integer',
        'output_tokens' => 'integer',
        'cost_usd' => 'float',
        'created_at' => 'datetime',
    ];
}
