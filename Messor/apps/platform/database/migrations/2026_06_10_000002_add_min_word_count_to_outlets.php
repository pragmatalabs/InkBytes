<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Per-outlet minimum word count (P4, 2026-06-09).
 *
 * NULL means "use the global Messor config default" (currently 40 words).
 * Set to a lower integer for outlets that routinely publish short pieces
 * (e.g. BBC news briefs: 25, Reuters wire stubs: 25).
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('outlets', function (Blueprint $table): void {
            $table->unsignedSmallInteger('min_word_count')->nullable()->after('feed_url');
        });
    }

    public function down(): void
    {
        Schema::table('outlets', function (Blueprint $table): void {
            $table->dropColumn('min_word_count');
        });
    }
};
