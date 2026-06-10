<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Per-outlet minimum word count (P4, 2026-06-09).
 *
 * NULL means "use the global Messor config default" (currently 40 words).
 * Set to a lower integer for outlets that routinely publish short pieces
 * (e.g. BBC news briefs: 25, Reuters wire stubs: 25).
 *
 * NOTE: Schema::hasColumn() is unreliable here because the Backoffice DB
 * connection's search_path starts with 'backoffice', so Doctrine DBAL looks
 * in the wrong schema. Use a raw information_schema check instead.
 */
return new class extends Migration
{
    public function up(): void
    {
        // Curator migration 013 owns this column — guard so the migration is
        // idempotent regardless of whether Curator ran first.
        $exists = DB::selectOne(
            "SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'outlets' AND column_name = 'min_word_count'"
        );

        if ($exists) {
            return;
        }

        Schema::table('outlets', function (Blueprint $table): void {
            $table->unsignedSmallInteger('min_word_count')->nullable()->after('feed_url');
        });
    }

    public function down(): void
    {
        $exists = DB::selectOne(
            "SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'outlets' AND column_name = 'min_word_count'"
        );

        if ($exists) {
            Schema::table('outlets', function (Blueprint $table): void {
                $table->dropColumn('min_word_count');
            });
        }
    }
};
