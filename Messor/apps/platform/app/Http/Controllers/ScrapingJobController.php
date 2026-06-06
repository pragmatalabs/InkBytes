<?php

namespace App\Http\Controllers;

use App\Jobs\RunScrapingWorker;
use App\Models\AuditLog;
use App\Models\Outlet;
use App\Models\ScrapingJob;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\File;
use Inertia\Inertia;
use Inertia\Response;
use Symfony\Component\HttpFoundation\StreamedResponse;

class ScrapingJobController extends Controller
{
    /**
     * Display the scraping control panel.
     */
    public function index(): Response
    {
        return Inertia::render('ScrapingJobs/Index', [
            'jobs' => $this->formatJobs(
                ScrapingJob::query()
                    ->latest('id')
                    ->limit(100)
                    ->get()
            ),
            // Active outlet catalogue for the per-run subset multi-select. The
            // `id` is the slug the trigger validates against (public.outlets.id).
            'outlets' => Outlet::query()
                ->where('active', true)
                ->orderBy('name')
                ->get(['id', 'name', 'display_name'])
                ->map(fn (Outlet $outlet): array => [
                    'id' => (string) $outlet->id,
                    'name' => $outlet->name,
                    'display_name' => $outlet->display_name ?: $outlet->name,
                ])
                ->values()
                ->all(),
        ]);
    }

    /**
     * Trigger a new scraping worker run.
     */
    public function trigger(Request $request): JsonResponse
    {
        $command = trim((string) config('scraping.command', ''));
        if ($command === '') {
            return response()->json([
                'message' => 'SCRAPING_COMMAND is not configured.',
            ], 422);
        }

        $activeJobExists = ScrapingJob::query()
            ->whereIn('status', ['pending', 'running'])
            ->exists();

        if ($activeJobExists) {
            return response()->json([
                'message' => 'A scraping job is already running.',
            ], 409);
        }

        // SECURITY: outlet_slugs are validated against the public.outlets
        // allowlist so only real catalogue ids can ever reach the worker's arg
        // builder; limit is bounded to an int range. The slug regex is a cheap
        // first filter (rejects shell metacharacters) before the DB allowlist
        // check below. A slug not in the DB → 422 (never escapes into a shell
        // command).
        $validated = $request->validate([
            'name' => ['nullable', 'string', 'max:255'],
            'limit' => ['nullable', 'integer', 'min:1', 'max:200'],
            'outlet_slugs' => ['nullable', 'array', 'max:200'],
            'outlet_slugs.*' => ['string', 'regex:/^[a-z0-9._-]+$/'],
        ]);

        // DB allowlist: every requested slug must exist in public.outlets.
        // Done via the Outlet model (correctly bound to the public schema)
        // rather than Rule::exists, whose dotted-table parsing treats the
        // schema as a connection name. Any unknown slug fails validation (422).
        $requestedSlugs = array_values(array_unique($validated['outlet_slugs'] ?? []));
        if ($requestedSlugs !== []) {
            $knownSlugs = Outlet::query()
                ->whereIn('id', $requestedSlugs)
                ->pluck('id')
                ->map(fn ($id): string => (string) $id)
                ->all();

            $unknownSlugs = array_values(array_diff($requestedSlugs, $knownSlugs));
            if ($unknownSlugs !== []) {
                throw \Illuminate\Validation\ValidationException::withMessages([
                    'outlet_slugs' => [
                        'Unknown outlet slug(s): '.implode(', ', $unknownSlugs),
                    ],
                ]);
            }
        }

        $name = trim((string) ($validated['name'] ?? ''));
        if ($name === '') {
            $name = sprintf('Scraping Run %s', now()->format('Y-m-d H:i:s'));
        }

        // Normalise the per-run options. Empty selection + empty limit stores
        // null → the worker builds `--scrape` (all outlets), the default.
        $limit = $validated['limit'] ?? null;
        $slugs = array_values(array_unique($validated['outlet_slugs'] ?? []));

        $options = [];
        if ($limit !== null) {
            $options['limit'] = (int) $limit;
        }
        if ($slugs !== []) {
            $options['outlet_slugs'] = $slugs;
        }
        $options = $options === [] ? null : $options;

        $scrapingJob = ScrapingJob::query()->create([
            'name' => $name,
            'status' => 'pending',
            'triggered_by' => $request->user()?->email ?? 'system',
            'options' => $options,
        ]);

        // Audit the trigger with the chosen scope (B1). The stored options are
        // allowlist-validated, so this is safe to record verbatim.
        AuditLog::record('scraping.triggered', 'scraping_job', (string) $scrapingJob->id, null, [
            'name' => $name,
            'options' => $options,
        ]);

        RunScrapingWorker::dispatch($scrapingJob->id)->onQueue('scraping');

        return response()->json([
            'data' => $this->formatJob($scrapingJob->fresh()),
        ], 201);
    }

    /**
     * Stream live log lines for a scraping job through SSE.
     */
    public function stream(int $id): StreamedResponse
    {
        $scrapingJob = ScrapingJob::query()->findOrFail($id);
        $localLogPath = $this->ensureLocalLogFile($scrapingJob);

        return response()->stream(
            function () use ($scrapingJob, $localLogPath): void {
                @set_time_limit(0);
                @ini_set('output_buffering', 'off');
                @ini_set('zlib.output_compression', '0');

                while (ob_get_level() > 0) {
                    ob_end_flush();
                }

                $position = 0;
                $lastHeartbeat = microtime(true);

                while (true) {
                    clearstatcache(true, $localLogPath);
                    $size = is_file($localLogPath) ? (int) filesize($localLogPath) : 0;

                    if ($size > $position) {
                        $handle = fopen($localLogPath, 'rb');
                        if ($handle !== false) {
                            fseek($handle, $position);
                            $chunk = fread($handle, $size - $position);
                            $position = ftell($handle) ?: $size;
                            fclose($handle);

                            if (is_string($chunk) && $chunk !== '') {
                                foreach (preg_split("/\r\n|\n|\r/", $chunk) as $line) {
                                    if ($line === '') {
                                        continue;
                                    }

                                    $this->emitSse([
                                        'type' => 'line',
                                        'line' => $line,
                                    ]);
                                }
                            }
                        }
                    }

                    $status = (string) ($scrapingJob->fresh()?->status ?? $scrapingJob->status);
                    $isTerminal = in_array($status, ['completed', 'failed'], true);

                    if ($isTerminal) {
                        clearstatcache(true, $localLogPath);
                        $latestSize = is_file($localLogPath) ? (int) filesize($localLogPath) : $position;
                        if ($latestSize <= $position) {
                            $this->emitSse([
                                'type' => 'end',
                                'status' => $status,
                            ]);
                            break;
                        }
                    }

                    if (connection_aborted()) {
                        break;
                    }

                    if ((microtime(true) - $lastHeartbeat) >= 10) {
                        echo ": heartbeat\n\n";
                        $this->flushOutputBuffers();
                        $lastHeartbeat = microtime(true);
                    }

                    usleep(300000);
                }
            },
            200,
            [
                'Content-Type' => 'text/event-stream',
                'Cache-Control' => 'no-cache, no-transform',
                'Connection' => 'keep-alive',
                'X-Accel-Buffering' => 'no',
            ]
        );
    }

    /**
     * Short-poll log tail — returns new log lines since byte-offset `from`.
     *
     * Replaces the blocking SSE stream for non-blocking log observation.
     * Each call reads only the new bytes written since the last poll and
     * returns immediately, so php artisan serve is free between 1.5s client
     * intervals. The client stops polling when done=true.
     *
     * GET /scraping/{id}/tail?from=0
     * Response: { lines: string[], next_from: int, status: string, done: bool }
     */
    public function tail(Request $request, int $id): JsonResponse
    {
        $job      = ScrapingJob::query()->findOrFail($id);
        $logPath  = $this->localLogPath($job);
        $from     = max(0, (int) $request->query('from', 0));

        $lines    = [];
        $nextFrom = $from;

        if (is_file($logPath)) {
            $size = (int) filesize($logPath);
            if ($size > $from) {
                $handle = fopen($logPath, 'rb');
                if ($handle !== false) {
                    fseek($handle, $from);
                    $chunk = fread($handle, $size - $from);
                    $nextFrom = (int) (ftell($handle) ?: $size);
                    fclose($handle);

                    if (is_string($chunk) && $chunk !== '') {
                        foreach (preg_split("/\r\n|\n|\r/", $chunk) as $line) {
                            if ($line !== '') {
                                $lines[] = $line;
                            }
                        }
                    }
                }
            }
        }

        $status = (string) $job->status;

        return response()->json([
            'lines'     => $lines,
            'next_from' => $nextFrom,
            'status'    => $status,
            'done'      => in_array($status, ['completed', 'failed'], true),
        ]);
    }

    /**
     * Return the current scraping job list for polling updates.
     */
    public function status(): JsonResponse
    {
        $jobs = ScrapingJob::query()
            ->latest('id')
            ->limit(100)
            ->get();

        return response()->json([
            'data' => $this->formatJobs($jobs),
        ]);
    }

    /**
     * @param  Collection<int, ScrapingJob>  $jobs
     * @return array<int, array<string, mixed>>
     */
    private function formatJobs(Collection $jobs): array
    {
        return $jobs
            ->map(fn (ScrapingJob $job): array => $this->formatJob($job))
            ->values()
            ->all();
    }

    /**
     * @return array<string, mixed>
     */
    private function formatJob(?ScrapingJob $job): array
    {
        if ($job === null) {
            return [];
        }

        $durationSeconds = null;
        if ($job->started_at !== null) {
            $durationSeconds = $job->started_at->diffInSeconds($job->finished_at ?? now());
        }

        return [
            'id' => $job->id,
            'name' => $job->name,
            'status' => $job->status,
            'triggered_by' => $job->triggered_by,
            'started_at' => $job->started_at?->toIso8601String(),
            'finished_at' => $job->finished_at?->toIso8601String(),
            'duration_seconds' => $durationSeconds,
            'exit_code' => $job->exit_code,
            'log_path' => $job->log_path,
            'options' => $job->options,
            'progress' => null,
        ];
    }

    private function ensureLocalLogFile(ScrapingJob $job): string
    {
        $path = $this->localLogPath($job);
        File::ensureDirectoryExists(dirname($path));

        if (!File::exists($path)) {
            File::put($path, '');
        }

        return $path;
    }

    private function localLogPath(ScrapingJob $job): string
    {
        return storage_path("logs/scraping/{$job->id}.log");
    }

    /**
     * @param  array<string, mixed>  $payload
     */
    private function emitSse(array $payload): void
    {
        echo 'data: '.json_encode($payload, JSON_UNESCAPED_UNICODE)."\n\n";
        $this->flushOutputBuffers();
    }

    private function flushOutputBuffers(): void
    {
        if (ob_get_level() > 0) {
            @ob_flush();
        }

        flush();
    }
}
