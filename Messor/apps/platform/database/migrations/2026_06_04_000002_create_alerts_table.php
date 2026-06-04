<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * alerts — operational alerts raised by the scheduled evaluator (B11).
 *
 * Backoffice-owned DDL (ADR-0001 / ADR-0003): lands in the `backoffice` schema
 * via the connection search_path. The evaluator (`alerts:evaluate`) probes the
 * existing B3/B4/B5/B6 signal sources (read-only across the schema line) and
 * UPSERTS rows here keyed on `dedup_key`, so a still-firing condition does not
 * spawn a duplicate open alert each run.
 *
 * `context` is a free-form jsonb bag of the metrics that tripped the rule
 * (e.g. {budget_usd, mtd_spend_usd}) for the UI to render — it must never carry
 * secrets (the probes already strip credentials).
 *
 * `dedup_key` identifies the open occurrence of a condition. The evaluator's
 * upsert matches on (dedup_key, status='open'); a per-rule unique partial index
 * (Postgres) guarantees at most one OPEN alert per key even under a race. An
 * acknowledged alert keeps its dedup_key for history, so the partial index only
 * constrains the open ones (a later re-fire of the same condition can open a
 * fresh row once the prior one is acknowledged).
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('alerts', function (Blueprint $table) {
            $table->id();

            // Rule that raised it: scrape_low_success | stale_outlet |
            // over_budget | pipeline_stalled.
            $table->string('type');

            // warning | critical.
            $table->string('severity')->default('warning');

            $table->string('title');
            $table->text('message');

            // The metrics that tripped the rule. jsonb on Postgres; Laravel maps
            // this to TEXT on SQLite (test DB). Never secret material.
            $table->jsonb('context')->nullable();

            // Identifies the open occurrence of a condition, e.g.
            // "over_budget" (singleton) or "stale_outlet:bbc" (per-outlet). The
            // evaluator upserts on this.
            $table->string('dedup_key');

            // open | acknowledged.
            $table->string('status')->default('open');

            // Snapshot of the human who acknowledged it (B1-style; actor_id is
            // nullable + intentionally NOT a foreign key so history survives a
            // user deletion).
            $table->timestampTz('acknowledged_at')->nullable();
            $table->unsignedBigInteger('acknowledged_by')->nullable();

            $table->timestampsTz();

            $table->index('status');
            $table->index('type');
            $table->index('dedup_key');
        });

        // At most one OPEN alert per dedup_key. Postgres supports a partial
        // unique index; SQLite (test DB) supports partial indexes too. Wrapped
        // per-driver so the upsert-by-dedup_key invariant holds even under a
        // concurrent evaluate.
        $driver = Schema::getConnection()->getDriverName();

        if (in_array($driver, ['pgsql', 'sqlite'], true)) {
            Schema::getConnection()->statement(
                "CREATE UNIQUE INDEX alerts_one_open_per_dedup_key
                 ON alerts (dedup_key) WHERE status = 'open'"
            );
        }
    }

    public function down(): void
    {
        Schema::dropIfExists('alerts');
    }
};
