<?php

use App\Models\ScrapeRun;
use App\Models\Source;
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
        Schema::create('articles', function (Blueprint $table) {
            $table->id();
            $table->string('external_id', 128)->unique();
            $table->string('uid', 128)->nullable()->index();
            $table->foreignIdFor(Source::class)
                ->nullable()
                ->constrained()
                ->nullOnDelete();
            $table->foreignIdFor(ScrapeRun::class)
                ->nullable()
                ->constrained()
                ->nullOnDelete();
            $table->text('article_url')->nullable();
            $table->string('article_source', 120)->nullable()->index();
            $table->text('title')->nullable();
            $table->longText('text')->nullable();
            $table->text('summary')->nullable();
            $table->json('authors')->nullable();
            $table->json('keywords')->nullable();
            $table->json('topics')->nullable();
            $table->json('meta_categories')->nullable();
            $table->json('entities')->nullable();
            $table->string('language', 16)->nullable()->index();
            $table->timestamp('publish_date')->nullable();
            $table->timestamp('fetched_on')->nullable();
            $table->timestamp('last_updated_at')->nullable();
            $table->json('metadata')->nullable();
            $table->timestamps();

            $table->index(['article_source', 'publish_date']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('articles');
    }
};
