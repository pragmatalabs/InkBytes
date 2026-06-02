<?php

namespace App\Services;

use App\Models\ScrapeRun;
use App\Models\Source;
use Carbon\CarbonInterface;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Collection;
use Illuminate\Support\Str;

class ScrapeRunService
{
    public function listForInertia(int $limit = 30): Collection
    {
        return ScrapeRun::query()
            ->latest('started_at')
            ->limit($limit)
            ->get()
            ->map(fn (ScrapeRun $run): array => [
                'id' => $run->run_code,
                'started_at' => ($run->started_at ?? $run->created_at)?->toIso8601String(),
                'duration' => $this->formatDuration($run->duration_seconds),
                'status' => $run->status,
                'articles' => $run->articles_count,
            ])
            ->values();
    }

    public function dashboardMetrics(): array
    {
        $latestRun = ScrapeRun::query()->with('source')->latest('started_at')->first();

        return [
            'total_sources' => Source::query()->count(),
            'active_sources' => Source::query()->where('status', 'active')->count(),
            'total_runs' => ScrapeRun::query()->count(),
            'running_runs' => ScrapeRun::query()->where('status', 'running')->count(),
            'completed_runs' => ScrapeRun::query()->where('status', 'completed')->count(),
            'failed_runs' => ScrapeRun::query()->where('status', 'failed')->count(),
            'articles_last_24h' => ScrapeRun::query()
                ->where('started_at', '>=', now()->subDay())
                ->sum('articles_count'),
            'latest_run' => $latestRun ? [
                'id' => $latestRun->run_code,
                'status' => $latestRun->status,
                'source' => $latestRun->source?->name ?? data_get($latestRun->metadata, 'outlet', 'Unknown'),
                'started_at' => $latestRun->started_at?->toIso8601String(),
                'articles' => $latestRun->articles_count,
            ] : null,
        ];
    }

    public function listSessionsForApi(Request $request): array
    {
        $page = max(1, (int) $request->input('pagination.page', $request->input('page', 1)));
        $pageSize = (int) $request->input('pagination.pageSize', $request->input('limit', 10));
        $pageSize = max(1, min(100, $pageSize));

        $query = ScrapeRun::query()->with('source');

        $filters = $request->input('filters', []);

        if (is_array($filters)) {
            $outletFilter = $filters['outlet']['$eq'] ?? null;
            if (is_string($outletFilter) && $outletFilter !== '') {
                $query->where(function ($builder) use ($outletFilter): void {
                    $builder->whereHas('source', function ($sourceQuery) use ($outletFilter): void {
                        $sourceQuery->where('name', $outletFilter);
                    })->orWhere('metadata->outlet', $outletFilter);
                });
            }

            $publishedAtFilter = $filters['publishedAt'] ?? [];
            if (is_array($publishedAtFilter)) {
                $start = $this->parseDate($publishedAtFilter['$gte'] ?? null);
                if ($start !== null) {
                    $query->where('started_at', '>=', $start);
                }

                $end = $this->parseDate($publishedAtFilter['$lte'] ?? null);
                if ($end !== null) {
                    $query->where('started_at', '<=', $end);
                }
            }
        }

        [$sortField, $direction] = $this->resolveSort($request);
        $query->orderBy($sortField, $direction);

        $paginator = $query->paginate($pageSize, ['*'], 'page', $page);

        $data = $paginator->getCollection()
            ->map(fn (ScrapeRun $run): array => $this->formatSessionRecord($run))
            ->values()
            ->all();

        return [
            'data' => $data,
            'meta' => [
                'pagination' => [
                    'page' => $paginator->currentPage(),
                    'pageSize' => $paginator->perPage(),
                    'pageCount' => $paginator->lastPage(),
                    'total' => $paginator->total(),
                ],
            ],
        ];
    }

    public function ingestSessionPayload(array $payload): ScrapeRun
    {
        $data = $payload['data'] ?? $payload;
        if (!is_array($data)) {
            $data = [];
        }

        $outlet = trim((string) ($data['outlet'] ?? 'Unknown Outlet'));
        $source = $this->resolveSource($outlet);
        $runCode = $this->resolveRunCode($data);

        $existing = ScrapeRun::query()->where('run_code', $runCode)->first();

        $startedAt = $this->parseDate($data['start_time'] ?? null) ?? $existing?->started_at ?? now();
        $completedAt = $this->parseDate($data['end_time'] ?? null);
        $durationSeconds = isset($data['duration']) && is_numeric($data['duration'])
            ? (int) round((float) $data['duration'])
            : $existing?->duration_seconds;

        $totalArticles = max(0, (int) ($data['total_articles'] ?? $existing?->articles_count ?? 0));
        $failedArticles = max(0, (int) ($data['failed_articles'] ?? data_get($existing?->metadata, 'failed_articles', 0)));
        $successfulArticles = max(
            0,
            (int) ($data['successful_articles'] ?? max($totalArticles - $failedArticles, 0))
        );

        $completed = (bool) ($data['completed_session'] ?? false);
        $status = $this->resolveStatus($data, $completed, $failedArticles, $successfulArticles, $totalArticles);

        $views = max(0, (int) ($data['views'] ?? $existing?->views_count ?? 0));
        $lastViewedAt = $this->parseDate($data['last_viewed'] ?? null) ?? $existing?->last_viewed_at;

        $mergedMetadata = array_merge(
            is_array($existing?->metadata) ? $existing->metadata : [],
            $data,
            ['outlet' => $outlet]
        );

        $run = ScrapeRun::query()->updateOrCreate(
            ['run_code' => $runCode],
            [
                'source_id' => $source?->id,
                'started_at' => $startedAt,
                'completed_at' => $completed ? ($completedAt ?? now()) : $completedAt,
                'duration_seconds' => $durationSeconds,
                'status' => $status,
                'articles_count' => $totalArticles,
                'failure_reason' => $status === 'failed'
                    ? ($data['failure_reason'] ?? $existing?->failure_reason ?? 'Scrape session failed')
                    : null,
                'views_count' => $views,
                'last_viewed_at' => $lastViewedAt,
                'metadata' => $mergedMetadata,
            ]
        );

        return $run->fresh('source');
    }

    public function formatSessionRecord(ScrapeRun $run): array
    {
        $totalArticles = max(0, (int) ($run->articles_count ?? 0));
        $failedArticles = max(0, (int) data_get($run->metadata, 'failed_articles', 0));

        $successfulArticles = (int) data_get($run->metadata, 'successful_articles', max($totalArticles - $failedArticles, 0));
        $successfulArticles = max(0, min($successfulArticles, $totalArticles > 0 ? $totalArticles : $successfulArticles));

        $successRate = $totalArticles > 0
            ? round($successfulArticles / $totalArticles, 6)
            : 0.0;

        $startTime = ($run->started_at ?? $run->created_at)?->toIso8601String();
        $endTime = $run->completed_at?->toIso8601String();
        $outlet = data_get($run->metadata, 'outlet', $run->source?->name ?? 'Unknown Outlet');

        return [
            'id' => $run->id,
            'documentId' => $run->run_code,
            'run_code' => $run->run_code,
            'start_time' => $startTime,
            'end_time' => $endTime,
            'total_articles' => $totalArticles,
            'failed_articles' => $failedArticles,
            'successful_articles' => $successfulArticles,
            'duration' => (float) ($run->duration_seconds ?? 0),
            'success_rate' => $successRate,
            'outlet' => $outlet,
            'completed_session' => $run->status === 'completed',
            'status' => $run->status,
            'views' => (int) ($run->views_count ?? 0),
            'last_viewed' => $run->last_viewed_at?->toIso8601String(),
            'publishedAt' => $startTime,
            'createdAt' => $run->created_at?->toIso8601String(),
            'updatedAt' => $run->updated_at?->toIso8601String(),
        ];
    }

    public function currentStatus(): array
    {
        $running = ScrapeRun::query()->where('status', 'running')->exists();

        return [
            'status' => $running ? 'Scraping in progress' : 'Ready to scrape',
        ];
    }

    public function latestResultsPayload(): ?array
    {
        $run = ScrapeRun::query()->with('source')->latest('started_at')->first();
        if ($run === null) {
            return null;
        }

        $session = $this->formatSessionRecord($run);
        $outletName = $session['outlet'];
        $outletUrl = $run->source?->base_url ?? $this->guessOutletUrl($outletName);
        $errors = [];

        if (is_string($run->failure_reason) && $run->failure_reason !== '') {
            $errors[] = $run->failure_reason;
        }

        $metadataErrors = data_get($run->metadata, 'errors');
        if (is_array($metadataErrors)) {
            $errors = array_values(array_unique(array_merge($errors, $metadataErrors)));
        }

        return [
            'id' => $session['documentId'],
            'start_time' => $session['start_time'],
            'end_time' => $session['end_time'] ?? $session['start_time'],
            'total_outlets_scraped' => 1,
            'total_articles_scraped' => $session['total_articles'],
            'duration' => $session['duration'],
            'overall_success_rate' => $session['success_rate'],
            'views' => $session['views'],
            'last_viewed' => $session['last_viewed'],
            'results' => [
                [
                    'outlet' => [
                        'name' => $outletName,
                        'url' => $outletUrl,
                        'type' => 'news',
                    ],
                    'total_articles' => $session['total_articles'],
                    'successful_scrapes' => $session['successful_articles'],
                    'failed_scrapes' => $session['failed_articles'],
                    'duration' => $session['duration'],
                    'errors' => $errors,
                ],
            ],
        ];
    }

    public function recordSessionView(string $sessionIdentifier): array
    {
        $query = ScrapeRun::query()->where('run_code', $sessionIdentifier);
        if (ctype_digit($sessionIdentifier)) {
            $query->orWhere('id', (int) $sessionIdentifier);
        }

        $run = $query->first();

        if ($run === null) {
            return [
                'session_id' => $sessionIdentifier,
                'views' => 1,
                'last_viewed' => now()->toIso8601String(),
            ];
        }

        $run->views_count = (int) ($run->views_count ?? 0) + 1;
        $run->last_viewed_at = now();
        $run->save();

        return [
            'session_id' => $run->run_code,
            'views' => $run->views_count,
            'last_viewed' => $run->last_viewed_at?->toIso8601String(),
        ];
    }

    private function formatDuration(?int $seconds): string
    {
        if ($seconds === null) {
            return 'N/A';
        }

        $hours = intdiv($seconds, 3600);
        $minutes = intdiv($seconds % 3600, 60);
        $remainingSeconds = $seconds % 60;

        if ($hours > 0) {
            return sprintf('%dh %02dm', $hours, $minutes);
        }

        if ($minutes > 0) {
            return sprintf('%dm %02ds', $minutes, $remainingSeconds);
        }

        return sprintf('%ds', $remainingSeconds);
    }

    private function resolveSort(Request $request): array
    {
        $sort = $request->input('sort.0', 'publishedAt:desc');
        if (!is_string($sort) || $sort === '') {
            return ['started_at', 'desc'];
        }

        [$field, $direction] = array_pad(explode(':', $sort, 2), 2, 'desc');
        $normalizedField = match ($field) {
            'publishedAt', 'start_time', 'started_at' => 'started_at',
            'updatedAt' => 'updated_at',
            default => 'started_at',
        };

        $normalizedDirection = strtolower($direction) === 'asc' ? 'asc' : 'desc';

        return [$normalizedField, $normalizedDirection];
    }

    private function parseDate(mixed $value): ?CarbonInterface
    {
        if (!is_string($value) || trim($value) === '') {
            return null;
        }

        try {
            return Carbon::parse($value);
        } catch (\Throwable) {
            return null;
        }
    }

    private function resolveRunCode(array $data): string
    {
        $rawRunCode = (string) ($data['results_staging_file_name'] ?? $data['run_code'] ?? '');
        if ($rawRunCode !== '') {
            return $rawRunCode;
        }

        return sprintf(
            'RUN-%s-%s',
            now()->format('Ymd-His'),
            Str::upper(Str::random(6))
        );
    }

    private function resolveSource(string $outlet): ?Source
    {
        if ($outlet === '' || $outlet === 'Unknown Outlet') {
            return null;
        }

        $slug = Str::slug($outlet);
        if ($slug === '') {
            $slug = Str::lower(Str::random(12));
        }

        $existing = Source::query()
            ->whereRaw('LOWER(name) = ?', [Str::lower($outlet)])
            ->orWhere('slug', $slug)
            ->first();

        if ($existing !== null) {
            return $existing;
        }

        return Source::query()->create([
            'name' => $outlet,
            'slug' => $slug,
            'region' => 'Global',
            'base_url' => $this->guessOutletUrl($outlet),
            'status' => 'active',
            'last_synced_at' => now(),
        ]);
    }

    private function resolveStatus(
        array $payload,
        bool $completed,
        int $failedArticles,
        int $successfulArticles,
        int $totalArticles
    ): string {
        $explicitStatus = strtolower((string) ($payload['status'] ?? ''));
        if (in_array($explicitStatus, ['queued', 'running', 'completed', 'failed'], true)) {
            return $explicitStatus;
        }

        if (!$completed) {
            return 'running';
        }

        if ($totalArticles > 0 && $successfulArticles === 0 && $failedArticles > 0) {
            return 'failed';
        }

        return 'completed';
    }

    private function guessOutletUrl(string $outlet): string
    {
        $trimmedOutlet = trim($outlet);
        if ($trimmedOutlet === '') {
            return 'https://example.com';
        }

        if (Str::startsWith($trimmedOutlet, ['http://', 'https://'])) {
            return $trimmedOutlet;
        }

        $candidate = Str::lower($trimmedOutlet);
        if (str_contains($candidate, '.')) {
            return 'https://'.Str::of($candidate)->replace(' ', '');
        }

        return 'https://www.'.Str::slug($candidate, '').'.com';
    }
}
