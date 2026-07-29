<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Add `max_article_age_hours` to curator_settings — the stale-message intake
 * gate, made live-tunable (stale-feed incident 2026-07-29).
 *
 * Backoffice-owned (ADR-0003): the single-row curator_settings table in the
 * `backoffice` schema. Curator polls it (30s refresh loop, ADR-0004) and
 * ack-and-drops any queued article whose scraped_at is older than this many
 * hours BEFORE spending an LLM call — so a harvest burst can't push fresh news
 * hours behind the FIFO backlog. Default 24 (was a hard-coded 48 in env.yaml,
 * which only caught the 105k-msg flood of 2026-06-09). 0 disables the gate.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->integer('max_article_age_hours')->default(24)->after('recent_window_hours');
        });
    }

    public function down(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->dropColumn('max_article_age_hours');
        });
    }
};
