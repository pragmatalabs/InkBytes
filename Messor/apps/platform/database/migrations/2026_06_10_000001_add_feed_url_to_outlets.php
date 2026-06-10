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
        Schema::table('outlets', function (Blueprint $table) {
            $table->text('feed_url')->nullable()->after('url');
        });
    }

    public function down(): void
    {
        Schema::table('outlets', function (Blueprint $table) {
            $table->dropColumn('feed_url');
        });
    }
};
