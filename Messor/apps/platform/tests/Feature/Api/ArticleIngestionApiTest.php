<?php

namespace Tests\Feature\Api;

use App\Models\Article;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ArticleIngestionApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_batch_ingestion_skips_duplicate_hash_ids(): void
    {
        $payload = [
            'data' => [
                'run_code' => 'session-001.db.json',
                'articles' => [
                    [
                        'id' => '9c8ba6d0-a69f-31dc-af3e-24f2949e0764',
                        'uid' => '9c8ba6d0-a69f-31dc-af3e-24f2949e0764',
                        'article_source' => 'bbccouk',
                        'article_url' => 'https://www.bbc.co.uk/news/articles/cx2vpz1kwreo',
                        'title' => 'How rescue of US airman in remote part of Iran unfolded',
                        'text' => 'Sample body',
                        'summary' => 'Sample summary',
                        'authors' => [],
                        'keywords' => ['iran', 'rescue'],
                        'topics' => [],
                        'meta_categories' => ['World'],
                        'entities' => [],
                        'language' => 'en',
                        'publish_date' => null,
                        'fetched_on' => now()->toIso8601String(),
                        'last_updated' => now()->toIso8601String(),
                        'metadata' => ['article' => ['section' => 'World']],
                    ],
                ],
            ],
        ];

        $firstResponse = $this->postJson('/api/articles/batch', $payload);
        $firstResponse->assertOk()
            ->assertJsonPath('data.received', 1)
            ->assertJsonPath('data.inserted', 1)
            ->assertJsonPath('data.skipped', 0);

        $secondResponse = $this->postJson('/api/articles/batch', $payload);
        $secondResponse->assertOk()
            ->assertJsonPath('data.received', 1)
            ->assertJsonPath('data.inserted', 0)
            ->assertJsonPath('data.skipped', 1);

        $this->assertSame(1, Article::query()->count());
        $this->assertDatabaseHas('articles', [
            'external_id' => '9c8ba6d0-a69f-31dc-af3e-24f2949e0764',
            'article_source' => 'bbccouk',
        ]);
    }
}
