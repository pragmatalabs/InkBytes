<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/**
 * Outlet — the canonical news-outlet catalogue.
 *
 * Bound to the shared `public.outlets` table, whose DDL is owned by Curator
 * (`Curator/apps/curator/db/migrations/002_outlets_table.sql`). The Backoffice
 * CRUDs the rows but does NOT own the schema — there is intentionally no
 * Laravel migration for this table. See docs/adr/0003-backoffice-schema-isolation.md.
 *
 * The primary key is a TEXT slug (e.g. "bbc"), not an auto-increment integer.
 */
class Outlet extends Model
{
    /**
     * The table lives in the `public` schema; Laravel's search_path is
     * `backoffice,public`, so an unqualified `outlets` resolves to
     * `public.outlets`. We qualify it explicitly to be unambiguous.
     */
    protected $table = 'public.outlets';

    protected $primaryKey = 'id';

    public $incrementing = false;

    protected $keyType = 'string';

    public $timestamps = true;

    protected $fillable = [
        'id',
        'name',
        'display_name',
        'url',
        'feed_url',
        'region',
        'language',
        'vertical',
        'active',
        'priority',
    ];

    protected $casts = [
        'active' => 'boolean',
        'priority' => 'integer',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];
}
