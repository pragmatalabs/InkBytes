<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Add OpenRouter routing knobs to backoffice.curator_settings (Curator ADR-0041).
 *
 * Makes the OpenRouter provider fully admin-manageable + hot-reloadable
 * (Curator polls this row per ADR-0004), so model routing no longer needs an
 * SSH/env edit:
 *   - openrouter_api_key           — OpenRouter key (plaintext varchar, same
 *                                     security boundary + UI masking as the other
 *                                     *_api_key columns; env var is the fallback).
 *   - llm_enrich_fallbacks          — comma-separated OpenRouter model slugs tried
 *   - llm_synth_fallbacks             (in order) when the primary errors/rate-limits
 *                                     — OpenRouter's request `models` array. Empty
 *                                     => keep the env value.
 *   - openrouter_deepseek_fallback  — provider-level fallback: on an OpenRouter
 *                                     quota/credit error, retry the call on the
 *                                     DIRECT DeepSeek endpoint. Default true.
 *
 * Plain Schema::table (no information_schema guard): curator_settings lives in
 * the `backoffice` schema (first in the connection search_path), so the Laravel
 * schema builder resolves it correctly — the public.* hasColumn gotcha does not
 * apply here.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->string('openrouter_api_key', 512)->nullable()->after('deepseek_api_key');
            // Comma-separated model slugs; Curator splits them into a list.
            $table->text('llm_enrich_fallbacks')->nullable()->after('llm_base_url');
            $table->text('llm_synth_fallbacks')->nullable()->after('llm_enrich_fallbacks');
            // OpenRouter quota/credit error → retry on the direct DeepSeek endpoint.
            $table->boolean('openrouter_deepseek_fallback')->default(true)->after('llm_synth_fallbacks');
        });
    }

    public function down(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->dropColumn([
                'openrouter_api_key',
                'llm_enrich_fallbacks',
                'llm_synth_fallbacks',
                'openrouter_deepseek_fallback',
            ]);
        });
    }
};
