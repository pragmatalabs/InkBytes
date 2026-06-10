<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * RSS/Atom feed URL for outlets that support it.
     * NULL = no feed configured; Messor scraper falls back to newspaper3k homepage crawl.
     * Non-null = scraper uses feed-first URL discovery (avoids geo-blocks, more precise).
     *
     * NOTE: Schema::hasColumn() is unreliable here because the Backoffice DB
     * connection's search_path starts with 'backoffice', so Doctrine DBAL looks
     * in the wrong schema. Use a raw information_schema check instead.
     */
    public function up(): void
    {
        // Curator migration 012 owns this column — it may already exist when
        // Curator ran before this Laravel migration. Guard so `php artisan migrate`
        // is idempotent on either ordering.
        $exists = DB::selectOne(
            "SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'outlets' AND column_name = 'feed_url'"
        );

        if ($exists) {
            return;
        }

        Schema::table('outlets', function (Blueprint $table): void {
            $table->text('feed_url')->nullable()->after('url');
        });
    }

    public function down(): void
    {
        $exists = DB::selectOne(
            "SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'outlets' AND column_name = 'feed_url'"
        );

        if ($exists) {
            Schema::table('outlets', function (Blueprint $table): void {
                $table->dropColumn('feed_url');
            });
        }
    }
};
