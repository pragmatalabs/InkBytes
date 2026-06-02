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
