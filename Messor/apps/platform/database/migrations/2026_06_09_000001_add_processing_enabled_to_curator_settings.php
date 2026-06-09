<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Add `processing_enabled` to curator_settings — the "Stop Curator" kill-switch
 * (Curator ADR-0023).
 *
 * Backoffice-owned (ADR-0003): lands on the single-row curator_settings table in
 * the `backoffice` schema. Curator polls it (30s refresh loop, ADR-0004) and,
 * when FALSE, pauses its enrich→cluster→synthesize pipeline — incoming articles
 * are requeued in RabbitMQ (never lost) and the API keeps serving. Default TRUE
 * so an existing row keeps running until an admin explicitly pauses it.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->boolean('processing_enabled')->default(true)->after('recent_window_hours');
        });
    }

    public function down(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->dropColumn('processing_enabled');
        });
    }
};
