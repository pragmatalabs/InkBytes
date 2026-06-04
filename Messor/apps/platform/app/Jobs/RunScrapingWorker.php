<?php

namespace App\Jobs;

use App\Models\ScrapingJob;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\File;
use RuntimeException;
use Symfony\Component\Process\Process;
use Throwable;

class RunScrapingWorker implements ShouldQueue
{
    use Dispatchable;
    use InteractsWithQueue;
    use Queueable;
    use SerializesModels;

    /**
     * Placeholder in SCRAPING_COMMAND replaced with the safely-built scrape
     * args. If absent, the command runs verbatim (backward-compatible).
     */
    public const SCRAPE_ARGS_PLACEHOLDER = '{SCRAPE_ARGS}';

    /**
     * Defensive allowlist for an outlet slug — mirrors the controller's DB
     * allowlist as a second line of defence at build time. Slugs in
     * public.outlets are TEXT ids like "bbc" / "el-caribe-dr".
     */
    private const SLUG_PATTERN = '/^[a-z0-9._-]+$/';

    public int $tries = 1;

    public int $timeout = 0;

    public function __construct(
        private readonly int $scrapingJobId
    ) {
        $this->onQueue('scraping');
    }

    /**
     * Execute the scraping worker command and persist lifecycle updates.
     */
    public function handle(): void
    {
        $scrapingJob = ScrapingJob::query()->find($this->scrapingJobId);
        if ($scrapingJob === null) {
            return;
        }

        $localLogPath = $this->localLogPath($scrapingJob->id);
        $this->ensureLogDirectory($localLogPath);

        $scrapingJob->forceFill([
            'status' => 'running',
            'started_at' => $scrapingJob->started_at ?? now(),
            'finished_at' => null,
            'exit_code' => null,
            'log_path' => $this->persistedLogPath($scrapingJob->id),
        ])->save();

        $stream = fopen($localLogPath, 'ab');
        if ($stream === false) {
            throw new RuntimeException("Unable to write scraping log file at {$localLogPath}.");
        }

        try {
            fwrite($stream, sprintf("[%s] Scraping worker started.%s", now()->toIso8601String(), PHP_EOL));
            fflush($stream);

            $process = $this->buildProcess($scrapingJob->id);
            $process->setTimeout(config('scraping.process_timeout'));

            $process->run(function (string $type, string $output) use ($stream): void {
                fwrite($stream, $output);
                fflush($stream);
            });

            $scrapingJob->forceFill([
                'status' => $process->isSuccessful() ? 'completed' : 'failed',
                'finished_at' => now(),
                'exit_code' => $process->getExitCode(),
            ])->save();
        } catch (Throwable $exception) {
            fwrite(
                $stream,
                sprintf(
                    "[%s] Worker failed: %s%s",
                    now()->toIso8601String(),
                    $exception->getMessage(),
                    PHP_EOL
                )
            );
            fflush($stream);

            $scrapingJob->forceFill([
                'status' => 'failed',
                'finished_at' => now(),
                'exit_code' => $exception->getCode() !== 0 ? $exception->getCode() : 1,
            ])->save();

            throw $exception;
        } finally {
            fwrite($stream, sprintf("[%s] Scraping worker finished.%s", now()->toIso8601String(), PHP_EOL));
            fclose($stream);
        }
    }

    private function buildProcess(int $scrapingJobId): Process
    {
        $command = trim((string) config('scraping.command', ''));
        if ($command === '') {
            throw new RuntimeException('SCRAPING_COMMAND is not configured.');
        }

        // Per-run scrape options (B-scrape-run-options). If the configured
        // command template carries the {SCRAPE_ARGS} placeholder, substitute it
        // with safely-built args derived from the job's stored, pre-validated
        // options. If the template has no placeholder, run it verbatim — that's
        // the pre-existing behaviour, kept for backward compatibility.
        if (str_contains($command, self::SCRAPE_ARGS_PLACEHOLDER)) {
            $command = str_replace(
                self::SCRAPE_ARGS_PLACEHOLDER,
                $this->buildScrapeArgs($scrapingJobId),
                $command
            );
        }

        $remoteHost = trim((string) config('scraping.remote_host', ''));
        if ($remoteHost === '') {
            return Process::fromShellCommandline(
                sprintf('bash -lc %s', escapeshellarg("set -o pipefail; {$command} 2>&1")),
                base_path()
            );
        }

        $remoteLogPath = $this->remoteLogPath($scrapingJobId);
        $remoteCommand = sprintf(
            'set -o pipefail; %s 2>&1 | tee -a %s; exit ${PIPESTATUS[0]}',
            $command,
            escapeshellarg($remoteLogPath)
        );
        $remoteInvocation = sprintf('bash -lc %s', escapeshellarg($remoteCommand));

        $arguments = [
            (string) config('scraping.ssh_binary', 'ssh'),
        ];

        $sshPort = (int) config('scraping.ssh_port', 22);
        if ($sshPort > 0) {
            $arguments[] = '-p';
            $arguments[] = (string) $sshPort;
        }

        $sshKeyPath = trim((string) config('scraping.ssh_key_path', ''));
        if ($sshKeyPath !== '') {
            $arguments[] = '-i';
            $arguments[] = $sshKeyPath;
        }

        $sshOptions = config('scraping.ssh_options', []);
        if (is_array($sshOptions)) {
            foreach ($sshOptions as $option) {
                if (!is_string($option) || trim($option) === '') {
                    continue;
                }

                $arguments[] = '-o';
                $arguments[] = trim($option);
            }
        }

        $arguments[] = $remoteHost;
        $arguments[] = $remoteInvocation;

        return new Process($arguments, base_path());
    }

    /**
     * Read the job's stored options and compose the Messor scrape args.
     */
    private function buildScrapeArgs(int $scrapingJobId): string
    {
        $options = ScrapingJob::query()->find($scrapingJobId)?->options;

        return self::composeScrapeArgs(is_array($options) ? $options : null);
    }

    /**
     * Build the Messor `--scrape...` argument string from validated options.
     *
     * SECURITY: this is the ONLY place per-run user input becomes shell text.
     * Inputs were validated upstream (slugs against the public.outlets
     * allowlist, limit as an int range). We re-validate defensively here and
     * escapeshellarg the outlet CSV so nothing user-supplied is ever
     * interpolated raw into the command. A slug failing the defensive pattern
     * is dropped (it should already have been rejected at validation).
     *
     * Mapping (mirrors Messor's command_processor parsing):
     *   none                       → --scrape                 (all outlets)
     *   {limit:N}                  → --scrape=--limit=N
     *   {outlet_slugs:[a,b]}       → --scrape --outlets='a,b'
     *   {outlet_slugs:[a], limit:N}→ --scrape --outlets='a' --limit=N
     *
     * @param  array<string, mixed>|null  $options
     */
    public static function composeScrapeArgs(?array $options): string
    {
        $options ??= [];

        $limit = null;
        if (array_key_exists('limit', $options) && $options['limit'] !== null && $options['limit'] !== '') {
            $candidate = filter_var($options['limit'], FILTER_VALIDATE_INT);
            if ($candidate !== false && $candidate >= 1 && $candidate <= 200) {
                $limit = $candidate;
            }
        }

        $slugs = [];
        $rawSlugs = $options['outlet_slugs'] ?? [];
        if (is_array($rawSlugs)) {
            foreach ($rawSlugs as $slug) {
                if (is_string($slug) && preg_match(self::SLUG_PATTERN, $slug) === 1) {
                    $slugs[] = $slug;
                }
            }
        }
        $slugs = array_values(array_unique($slugs));

        // No outlet subset: --scrape (optionally with --limit folded in via the
        // single-token =--limit form Messor's parser understands).
        if ($slugs === []) {
            if ($limit !== null) {
                return '--scrape=--limit='.$limit;
            }

            return '--scrape';
        }

        // Outlet subset: escape the CSV; append --limit as a separate token.
        $csv = implode(',', $slugs);
        $args = '--scrape --outlets='.escapeshellarg($csv);
        if ($limit !== null) {
            $args .= ' --limit='.$limit;
        }

        return $args;
    }

    private function localLogPath(int $scrapingJobId): string
    {
        return storage_path("logs/scraping/{$scrapingJobId}.log");
    }

    private function remoteLogPath(int $scrapingJobId): string
    {
        $logDirectory = trim((string) config('scraping.log_dir', '/tmp/scraping'));
        return rtrim($logDirectory, '/')."/{$scrapingJobId}.log";
    }

    private function persistedLogPath(int $scrapingJobId): string
    {
        $remoteHost = trim((string) config('scraping.remote_host', ''));
        if ($remoteHost !== '') {
            return $this->remoteLogPath($scrapingJobId);
        }

        return $this->localLogPath($scrapingJobId);
    }

    private function ensureLogDirectory(string $logPath): void
    {
        File::ensureDirectoryExists(dirname($logPath));
    }
}
