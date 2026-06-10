<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * RSS/Atom feed URL for outlets that support it.
     * NULL = no feed configured; Messor scraper falls back to newspaper3k homepage crawl.
     * Non-null = scraper uses feed-first URL discovery (avoids geo-blocks, more precise).
     */
    public function up(): void
    {
        // Curator migration 012 owns this column — it may already exist when
        // Curator ran before this Laravel migration. Guard so `php artisan migrate`
        // is idempotent on either ordering.
        if (Schema::hasColumn('outlets', 'feed_url')) {
            return;
        }

        Schema::table('outlets', function (Blueprint $table): void {
            $table->text('feed_url')->nullable()->after('url');
        });
    }

    public function down(): void
    {
        if (Schema::hasColumn('outlets', 'feed_url')) {
            Schema::table('outlets', function (Blueprint $table): void {
                $table->dropColumn('feed_url');
            });
        }
    }
};
