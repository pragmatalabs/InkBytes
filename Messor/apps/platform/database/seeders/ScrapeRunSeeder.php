<?php

namespace Database\Seeders;

use App\Models\ScrapeRun;
use App\Models\Source;
use Illuminate\Database\Seeder;

class ScrapeRunSeeder extends Seeder
{
    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        $sources = Source::query()->get()->keyBy('slug');

        if ($sources->isEmpty()) {
            return;
        }

        $now = now();

        $runs = [
            [
                'run_code' => sprintf('RUN-%s-001', $now->format('Ymd')),
                'source_id' => $sources->get('reuters')?->id,
                'started_at' => $now->copy()->subMinutes(12),
                'completed_at' => null,
                'duration_seconds' => null,
                'status' => 'running',
                'articles_count' => 784,
                'failure_reason' => null,
                'metadata' => [
                    'queue' => 'high',
                    'initiator' => 'scheduler',
                ],
            ],
            [
                'run_code' => sprintf('RUN-%s-014', $now->copy()->subDay()->format('Ymd')),
                'source_id' => $sources->get('bbc')?->id,
                'started_at' => $now->copy()->subHours(3),
                'completed_at' => $now->copy()->subHours(3)->addMinutes(8)->addSeconds(18),
                'duration_seconds' => 498,
                'status' => 'completed',
                'articles_count' => 1256,
                'failure_reason' => null,
                'metadata' => [
                    'queue' => 'default',
                    'initiator' => 'worker',
                ],
            ],
            [
                'run_code' => sprintf('RUN-%s-009', $now->copy()->subDays(2)->format('Ymd')),
                'source_id' => $sources->get('ap-news')?->id,
                'started_at' => $now->copy()->subDay(),
                'completed_at' => $now->copy()->subDay()->addMinute()->addSeconds(9),
                'duration_seconds' => 69,
                'status' => 'failed',
                'articles_count' => 89,
                'failure_reason' => 'Timeout while resolving outlet feed URLs.',
                'metadata' => [
                    'queue' => 'default',
                    'initiator' => 'worker',
                ],
            ],
        ];

        foreach ($runs as $run) {
            ScrapeRun::query()->updateOrCreate(
                ['run_code' => $run['run_code']],
                $run,
            );
        }
    }
}
