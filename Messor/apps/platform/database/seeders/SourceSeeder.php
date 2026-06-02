<?php

namespace Database\Seeders;

use App\Models\Source;
use Illuminate\Database\Seeder;

class SourceSeeder extends Seeder
{
    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        $timestamp = now();

        $sources = [
            [
                'name' => 'Reuters',
                'slug' => 'reuters',
                'region' => 'Global',
                'base_url' => 'https://www.reuters.com',
                'status' => 'active',
            ],
            [
                'name' => 'BBC',
                'slug' => 'bbc',
                'region' => 'United Kingdom',
                'base_url' => 'https://www.bbc.com',
                'status' => 'active',
            ],
            [
                'name' => 'AP News',
                'slug' => 'ap-news',
                'region' => 'United States',
                'base_url' => 'https://apnews.com',
                'status' => 'active',
            ],
            [
                'name' => 'The Guardian',
                'slug' => 'the-guardian',
                'region' => 'United Kingdom',
                'base_url' => 'https://www.theguardian.com',
                'status' => 'paused',
            ],
        ];

        Source::query()->upsert(
            array_map(fn (array $source): array => [
                ...$source,
                'last_synced_at' => $timestamp,
                'created_at' => $timestamp,
                'updated_at' => $timestamp,
            ], $sources),
            ['slug'],
            ['name', 'region', 'base_url', 'status', 'last_synced_at', 'updated_at'],
        );
    }
}
