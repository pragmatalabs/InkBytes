<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Add llm_provider to curator_settings (B15 — multi-provider LLM support;
 * Curator ADR live-reconfigure).
 *
 * Backoffice-owned (ADR-0003): the column lands on the single-row
 * curator_settings table in the `backoffice` schema. Curator polls and
 * LIVE-applies llm_provider (it rebuilds its LLM client within its refresh
 * interval — no redeploy needed per ADR-0004).
 *
 * Allowed values: 'anthropic' (default) | 'openai'. Validated by the
 * CuratorSettingController against config('curator.allowed_llm.providers').
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->string('llm_provider')->default('anthropic')->after('synthesize_model');
        });
    }

    public function down(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->dropColumn('llm_provider');
        });
    }
};
