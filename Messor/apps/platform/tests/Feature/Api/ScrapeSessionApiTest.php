<?php

namespace Tests\Feature\Api;

use App\Models\ScrapeRun;
use App\Models\Source;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ScrapeSessionApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_news_outlets_endpoint_returns_active_sources_only_when_filtered(): void
    {
        Source::query()->create([
            'name' => 'Reuters',
            'slug' => 'reuters',
            'region' => 'Global',
            'base_url' => 'https://www.reuters.com',
            'status' => 'active',
        ]);

        Source::query()->create([
            'name' => 'Paused Source',
            'slug' => 'paused-source',
            'region' => 'Global',
            'base_url' => 'https://example.com',
            'status' => 'paused',
        ]);

        $response = $this->getJson('/api/news-outlets?filters[active]=true');

        $response->assertOk()
            ->assertJsonCount(1, 'data')
            ->assertJsonPath('data.0.name', 'Reuters');
    }

    public function test_can_ingest_and_list_scrape_sessions(): void
    {
        $payload = [
            'data' => [
                'start_time' => now()->subMinutes(5)->toIso8601String(),
                'end_time' => now()->toIso8601String(),
                'total_articles' => 30,
                'failed_articles' => 2,
                'successful_articles' => 28,
                'duration' => 300.1,
                'success_rate' => 0.9333,
                'outlet' => 'Reuters',
                'completed_session' => true,
                'results_staging_file_name' => 'session-001.db.json',
            ],
        ];

        $storeResponse = $this->postJson('/api/scrapesessions', $payload);
        $storeResponse->assertCreated()
            ->assertJsonPath('data.documentId', 'session-001.db.json')
            ->assertJsonPath('data.total_articles', 30);

        $listResponse = $this->getJson('/api/scrapesessions?pagination[pageSize]=10&pagination[page]=1&sort[0]=publishedAt:desc');
        $listResponse->assertOk()
            ->assertJsonPath('meta.pagination.total', 1)
            ->assertJsonPath('data.0.documentId', 'session-001.db.json')
            ->assertJsonPath('data.0.outlet', 'Reuters');
    }

    public function test_record_session_view_increments_counter(): void
    {
        $run = ScrapeRun::query()->create([
            'run_code' => 'RUN-VIEW-001',
            'started_at' => now()->subMinute(),
            'completed_at' => now(),
            'duration_seconds' => 10,
            'status' => 'completed',
            'articles_count' => 3,
            'views_count' => 0,
        ]);

        $response = $this->postJson('/api/scrape/session/RUN-VIEW-001/view');

        $response->assertOk()
            ->assertJsonPath('session_id', 'RUN-VIEW-001')
            ->assertJsonPath('views', 1);

        $run->refresh();
        $this->assertSame(1, $run->views_count);
        $this->assertNotNull($run->last_viewed_at);
    }
}
