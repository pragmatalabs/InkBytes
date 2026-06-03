<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * api_keys — Backoffice-owned provider key vault (store / rotate / mask / test).
 *
 * Backoffice-owned (ADR-0001 / ADR-0003): lands in the `backoffice` schema.
 *
 * IMPORTANT (ADR-0004): Curator does NOT read or decrypt this table. Curator
 * keeps loading the REAL provider keys from env (ANTHROPIC_API_KEY /
 * OPENAI_API_KEY). This table exists so the admin can store, rotate, mask and
 * test keys; `value` is encrypted at rest via Laravel's `encrypted` cast, so a
 * raw key is never stored in plaintext, never logged, never returned unmasked.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('api_keys', function (Blueprint $table) {
            $table->id();
            $table->string('provider'); // anthropic | openai
            $table->string('label')->nullable();
            // Encrypted at rest by the model's `encrypted` cast — store as text
            // because the ciphertext is much longer than the raw key.
            $table->text('value');
            $table->boolean('active')->default(true);
            $table->timestamps();

            $table->index('provider');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('api_keys');
    }
};
