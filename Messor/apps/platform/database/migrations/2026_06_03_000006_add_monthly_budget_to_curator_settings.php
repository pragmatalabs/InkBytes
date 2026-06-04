<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Add `monthly_budget_usd` to curator_settings (B5 — cost dashboard upgrades).
 *
 * Backoffice-owned (ADR-0003): this column lands in the `backoffice` schema on
 * the existing single-row curator_settings table. It is the admin-editable
 * monthly LLM-spend budget the Cost & Usage dashboard compares month-to-date
 * spend against (over-budget alert). NULL = no budget set → the widget hides.
 *
 * It rides on curator_settings rather than a dedicated table to keep the
 * surface minimal: there is already one admin-only, B1-audited settings form.
 * Curator does NOT read this value (it is a Backoffice-only display knob), so
 * adding it here does not change the config contract Curator polls (ADR-0004).
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            // Nullable: no budget configured by default. USD with cent+ precision
            // so tiny test budgets (e.g. $0.001) are representable.
            $table->decimal('monthly_budget_usd', 12, 4)->nullable()->after('recent_window_hours');
        });
    }

    public function down(): void
    {
        Schema::table('curator_settings', function (Blueprint $table) {
            $table->dropColumn('monthly_budget_usd');
        });
    }
};
