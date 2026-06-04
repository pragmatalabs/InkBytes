<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Per-run scrape options (outlet subset + limit) for scraping_jobs.
 *
 * Stores the operator's validated, per-run selection as JSON, e.g.
 *   {"limit": 3, "outlet_slugs": ["bbc", "cnbc"]}
 * Nullable: a null/empty value means "scrape all outlets" (today's default).
 *
 * The values written here have already been validated against the
 * public.outlets allowlist (slugs) and an int range (limit) in
 * ScrapingJobController@trigger — RunScrapingWorker re-reads them and builds
 * the shell args safely (escapeshellarg). See ADR / docs note.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('scraping_jobs', function (Blueprint $table) {
            $table->json('options')->nullable()->after('triggered_by');
        });
    }

    public function down(): void
    {
        Schema::table('scraping_jobs', function (Blueprint $table) {
            $table->dropColumn('options');
        });
    }
};
