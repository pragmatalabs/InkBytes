<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/**
 * ScrapeSession — one durable, run-level record of a Messor harvest session.
 *
 * READ-ONLY from the Backoffice. The DDL is owned by Curator (migration
 * `Curator/apps/curator/db/migrations/004_scrape_sessions.sql`, ADR-0006); the
 * row is written by Curator's consumer (which upserts on a Messor-emitted
 * `scrape.session.completed` event — Messor stays Postgres-free). The Backoffice
 * only reads it cross-schema for the Scrape Results browser (B12.2). It NEVER
 * writes this table — there is intentionally no Laravel migration for it.
 *
 * The table lives in the `public` schema; Laravel's search_path is
 * `backoffice,public`, so an unqualified `scrape_sessions` would resolve there,
 * but we qualify it explicitly to be unambiguous (matches Outlet/Event/Page).
 *
 * The primary key is a TEXT run id (e.g. "session-<unix_ts>"), not an integer.
 */
class ScrapeSession extends Model
{
    protected $table = 'public.scrape_sessions';

    protected $primaryKey = 'session_id';

    public $incrementing = false;

    protected $keyType = 'string';

    public $timestamps = false; // Curator manages created_at/updated_at via trigger

    protected $guarded = ['*']; // read-only: nothing is mass-assignable

    protected $casts = [
        'started_at' => 'datetime',
        'ended_at' => 'datetime',
        'total_articles' => 'integer',
        'successful_articles' => 'integer',
        'failed_articles' => 'integer',
        'duplicates_total' => 'integer',
        'success_rate' => 'float',
        'duration_seconds' => 'float',
        'total_outlets' => 'integer',
        'outlets' => 'array',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];
}
