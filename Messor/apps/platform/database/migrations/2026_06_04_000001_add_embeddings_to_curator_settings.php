<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Add embedding provider settings to curator_settings (ADR-0004 — admin-managed
 * embedding tier).
 *
 * Backoffice-owned (ADR-0003): these columns land on the single-row
 * curator_settings table in the `backoffice` schema. Curator polls and
 * LIVE-applies provider/model/base_url (it rebuilds its embedding client, with
 * a dimension-probe guard — ADR-0004).
 *
 * Note: vector `dimensions` is intentionally NOT a column here. It is the
 * pgvector column width (a migration concern), derived from the model for
 * display via config('curator.allowed_embeddings.dimensions'); a model whose
 * width differs from the live column is refused by Curator rather than applied.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->string('embeddings_provider')->default('ollama')->after('recent_window_hours');
            $table->string('embeddings_model')->default('bge-m3')->after('embeddings_provider');
            // Nullable: only used by provider=ollama (OpenAI uses its SDK default
            // endpoint). Defaults to the in-cluster Ollama service URL.
            $table->string('embeddings_base_url')->nullable()->default('http://localhost:11434/v1')->after('embeddings_model');
        });
    }

    public function down(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->dropColumn(['embeddings_provider', 'embeddings_model', 'embeddings_base_url']);
        });
    }
};
