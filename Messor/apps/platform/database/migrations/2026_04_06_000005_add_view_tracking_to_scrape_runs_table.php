<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('scrape_runs', function (Blueprint $table) {
            $table->unsignedInteger('views_count')->default(0)->after('failure_reason');
            $table->timestamp('last_viewed_at')->nullable()->after('views_count');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('scrape_runs', function (Blueprint $table) {
            $table->dropColumn(['views_count', 'last_viewed_at']);
        });
    }
};
