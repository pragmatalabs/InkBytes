<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Add API key fields + llm_base_url to backoffice.curator_settings.
 *
 * Purpose: allow the admin to set LLM / embedding API keys directly in the
 * Backoffice instead of requiring them as shell env vars. Curator polls these
 * columns (via its 30-s config-refresh loop, ADR-0004) and uses them in place
 * of the env var fallbacks when set.
 *
 * Security note: keys are stored as plaintext varchar in the backoffice schema
 * (same security boundary as the rest of curator_settings). They are masked in
 * the UI (never echoed back) and never logged. For higher-assurance deployments
 * continue using env vars — DB values take precedence when both are set.
 *
 * llm_base_url allows pointing the OpenAI-compatible client at any endpoint
 * (DeepSeek, Groq, Together, local Ollama text generation, etc.).
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            // LLM provider keys — stored in DB override the corresponding env var.
            $table->string('anthropic_api_key', 512)->nullable()->after('llm_provider');
            $table->string('openai_api_key',    512)->nullable()->after('anthropic_api_key');
            $table->string('deepseek_api_key',  512)->nullable()->after('openai_api_key');
            // Base URL for OpenAI-compatible providers (DeepSeek, Groq, Together, etc.).
            // When set, overrides the provider's default endpoint.
            $table->string('llm_base_url', 255)->nullable()->after('deepseek_api_key');
            // Embedding provider key (used when embeddings.provider = openai).
            $table->string('embeddings_api_key', 512)->nullable()->after('embeddings_base_url');
        });
    }

    public function down(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->dropColumn([
                'anthropic_api_key',
                'openai_api_key',
                'deepseek_api_key',
                'llm_base_url',
                'embeddings_api_key',
            ]);
        });
    }
};
