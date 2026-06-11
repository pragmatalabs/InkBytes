<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Breaking-news pulse flag (Messor ADR-0017, 2026-06-11).
 *
 * Pulse outlets are polled every ~5 minutes via their RSS feed (never
 * newspaper3k) and their articles are published at AMQP priority 9 so
 * Curator processes them ahead of the regular backlog. Requires feed_url.
 *
 * NOTE: Schema::hasColumn() is unreliable here because the Backoffice DB
 * connection's search_path starts with 'backoffice', so Doctrine DBAL looks
 * in the wrong schema. Use a raw information_schema check instead.
 */
return new class extends Migration
{
    public function up(): void
    {
        // Curator migration 014 owns this column — guard so the migration is
        // idempotent regardless of whether Curator ran first.
        $exists = DB::selectOne(
            "SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'outlets' AND column_name = 'pulse'"
        );

        if ($exists) {
            return;
        }

        Schema::table('outlets', function (Blueprint $table): void {
            $table->boolean('pulse')->default(false)->after('min_word_count');
        });
    }

    public function down(): void
    {
        $exists = DB::selectOne(
            "SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'outlets' AND column_name = 'pulse'"
        );

        if ($exists) {
            Schema::table('outlets', function (Blueprint $table): void {
                $table->dropColumn('pulse');
            });
        }
    }
};
