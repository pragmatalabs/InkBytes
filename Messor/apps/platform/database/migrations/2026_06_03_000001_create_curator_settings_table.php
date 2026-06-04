<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * curator_settings — the Backoffice-owned tunables Curator reads at runtime.
 *
 * Backoffice-owned (ADR-0001 / ADR-0003): this table lands in the `backoffice`
 * schema via the connection search_path; Curator reads it read-only and
 * schema-qualified (`backoffice.curator_settings`). The columns mirror the
 * knobs in `Curator/apps/curator/core/config.py` (LlmCfg + ClusterCfg).
 *
 * Single-row design: one settings row (id=1) holds the live config. Curator
 * loads it on boot and refreshes it on a `curator.config.changed` RabbitMQ
 * signal. Env/YAML remain the bootstrap fallback when the row is absent.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('curator_settings', function (Blueprint $table) {
            $table->id();

            // LLM (mirrors LlmCfg)
            $table->string('enrich_model')->default('claude-haiku-4-5');
            $table->string('synthesize_model')->default('claude-haiku-4-5');
            $table->unsignedInteger('max_tokens_enrich')->default(1500);
            $table->unsignedInteger('max_tokens_synth')->default(2500);
            $table->decimal('temperature', 3, 2)->default(0.20);

            // Clustering (mirrors ClusterCfg)
            $table->decimal('similarity_threshold', 4, 3)->default(0.620);
            $table->unsignedInteger('entity_overlap_min')->default(1);
            $table->unsignedInteger('min_sources_to_publish')->default(2);
            $table->unsignedInteger('recent_window_hours')->default(48);

            $table->timestamps();
        });

        // Seed the single live row from the canonical defaults. These live in
        // `config/curator.php` (B9) so the seed and the "reset to defaults"
        // action share one source of truth and can't drift. `monthly_budget_usd`
        // (B5) defaults to NULL (unset) and is omitted here — its column is
        // added by a later migration with a nullable default.
        $defaults = config('curator.defaults');

        DB::table('curator_settings')->insert([
            'id' => 1,
            'enrich_model' => $defaults['enrich_model'],
            'synthesize_model' => $defaults['synthesize_model'],
            'max_tokens_enrich' => $defaults['max_tokens_enrich'],
            'max_tokens_synth' => $defaults['max_tokens_synth'],
            'temperature' => $defaults['temperature'],
            'similarity_threshold' => $defaults['similarity_threshold'],
            'entity_overlap_min' => $defaults['entity_overlap_min'],
            'min_sources_to_publish' => $defaults['min_sources_to_publish'],
            'recent_window_hours' => $defaults['recent_window_hours'],
            'created_at' => now(),
            'updated_at' => now(),
        ]);
    }

    public function down(): void
    {
        Schema::dropIfExists('curator_settings');
    }
};
