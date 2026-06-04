<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * audit_logs — append-only record of every state-changing admin action (B1).
 *
 * Backoffice-owned DDL (ADR-0001 / ADR-0003): lands in the `backoffice` schema
 * via the connection search_path. Never touches Curator's `public.*` tables.
 *
 * Actor identity is SNAPSHOTTED (actor_name / actor_email copied at write time)
 * so deleting a user later does not orphan or erase who did what. `actor_id` is
 * nullable and intentionally NOT a foreign key — keeping history independent of
 * the users table.
 *
 * `before` / `after` hold JSON snapshots of the target's relevant fields. They
 * must NEVER contain secret material (e.g. raw/encrypted API keys) — the
 * recorder's callers are responsible for passing only safe projections.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('audit_logs', function (Blueprint $table) {
            $table->id();

            // Snapshot of the acting user. actor_id may dangle after a user is
            // deleted; the name/email columns preserve the human record.
            $table->unsignedBigInteger('actor_id')->nullable();
            $table->string('actor_name')->nullable();
            $table->string('actor_email')->nullable();

            // e.g. "outlet.updated", "apikey.created", "page.published".
            $table->string('action');

            // e.g. "outlet", "apikey", "settings", "page", "event".
            $table->string('target_type');
            // Target's natural id; string to cover both TEXT (Curator) and
            // numeric (Backoffice) keys. Nullable for global targets.
            $table->string('target_id')->nullable();

            // Field-level snapshots. jsonb on Postgres; Laravel maps this to
            // TEXT on SQLite (test DB) automatically.
            $table->jsonb('before')->nullable();
            $table->jsonb('after')->nullable();

            $table->string('ip')->nullable();

            // Set at write time; timestamptz on Postgres.
            $table->timestampTz('created_at')->useCurrent();

            $table->index('action');
            $table->index(['target_type', 'target_id']);
            $table->index('created_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('audit_logs');
    }
};
