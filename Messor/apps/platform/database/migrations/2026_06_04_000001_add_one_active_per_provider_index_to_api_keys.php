<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * B8 — one-active-per-provider DB safety net on backoffice.api_keys.
 *
 * A PARTIAL UNIQUE INDEX on (provider) WHERE active enforces the invariant
 * that at most one row per provider may be active=true, even under a race the
 * app logic might lose. The application still deactivates-then-activates in a
 * transaction so it never trips this index in normal operation; the index is
 * the last line of defence.
 *
 * Backoffice-owned (ADR-0003): targets the `backoffice` schema only (the
 * default connection's search_path is `backoffice,public`, so the unqualified
 * `api_keys` table is the backoffice one). Never touches `public.*`.
 *
 * ADR-0004 unchanged: Curator still loads its real keys from env; this is purely
 * a record-keeping invariant on the management vault.
 *
 * Driver-aware: Postgres + SQLite both support `CREATE UNIQUE INDEX ... WHERE`.
 */
return new class extends Migration
{
    private const INDEX = 'api_keys_one_active_per_provider';

    public function up(): void
    {
        $driver = Schema::getConnection()->getDriverName();

        // Both Postgres and SQLite accept a partial (filtered) unique index.
        // `WHERE active` evaluates truthiness — true rows are constrained, and
        // any number of inactive (active=false) rows per provider are allowed.
        if (in_array($driver, ['pgsql', 'sqlite'], true)) {
            DB::statement(
                'CREATE UNIQUE INDEX '.self::INDEX.' ON api_keys (provider) WHERE active'
            );
        }
    }

    public function down(): void
    {
        $driver = Schema::getConnection()->getDriverName();

        if (in_array($driver, ['pgsql', 'sqlite'], true)) {
            DB::statement('DROP INDEX IF EXISTS '.self::INDEX);
        }
    }
};
