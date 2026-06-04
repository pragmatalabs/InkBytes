<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Add `role` to backoffice.users — B2 (RBAC).
 *
 * Backoffice-owned DDL (ADR-0001 / ADR-0003): lands in the `backoffice` schema
 * via the connection search_path. Never touches Curator's `public.*` tables.
 *
 * Three app-level roles gate dangerous actions (see ADR-0005):
 *   - admin    — everything (API keys, settings, audit log, user management)
 *   - operator — outlets / scraping / moderation mutations; no keys/settings/users
 *   - viewer   — read-only (the safe default for new registrations)
 *
 * Role is a plain string validated at the application layer (the role
 * middleware + UserController) rather than a DB check constraint, to keep the
 * SQLite test DB and Postgres prod DB behaving identically.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('role')->default('viewer')->after('email');
        });

        // Promote the seeded dev admin if it already exists.
        DB::table('users')->where('email', 'admin@inkbytes.test')->update(['role' => 'admin']);
    }

    public function down(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->dropColumn('role');
        });
    }
};
