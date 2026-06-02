<?php

namespace App\Services;

use Illuminate\Support\Carbon;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Http;
use Throwable;

class DockerRuntimeService
{
    private const DOCKER_HOST = 'http://localhost';

    public function snapshot(): array
    {
        $project = config('runtime_monitor.project');
        $updatedAt = now()->toIso8601String();

        if (!config('runtime_monitor.enabled')) {
            return $this->unavailableSnapshot(
                $project,
                $updatedAt,
                'Runtime monitor is disabled by configuration.'
            );
        }

        $socketPath = (string) config('runtime_monitor.socket_path');

        if ($socketPath === '' || !file_exists($socketPath)) {
            return $this->unavailableSnapshot(
                $project,
                $updatedAt,
                "Docker socket is not available at {$socketPath}."
            );
        }

        try {
            $containers = $this->fetchContainerList($project)
                ->map(fn (array $container): array => $this->formatContainerSnapshot($container))
                ->values()
                ->all();

            return [
                'available' => true,
                'project' => $project,
                'updated_at' => $updatedAt,
                'containers' => $containers,
            ];
        } catch (Throwable $exception) {
            report($exception);

            return $this->unavailableSnapshot(
                $project,
                $updatedAt,
                'Unable to load Docker runtime data.'
            );
        }
    }

    private function unavailableSnapshot(?string $project, string $updatedAt, string $message): array
    {
        return [
            'available' => false,
            'project' => $project,
            'updated_at' => $updatedAt,
            'message' => $message,
            'containers' => [],
        ];
    }

    private function fetchContainerList(?string $project): Collection
    {
        $containers = $this->dockerRequest('/containers/json', [
            'all' => 1,
        ]);

        if (!is_array($containers)) {
            return collect();
        }

        return collect($containers)
            ->filter(fn ($container): bool => is_array($container))
            ->filter(function (array $container) use ($project): bool {
                if (!is_string($project) || $project === '') {
                    return true;
                }

                $containerProject = $this->containerLabel($container, 'com.docker.compose.project');

                return is_string($containerProject) && $containerProject === $project;
            })
            ->sortBy(fn (array $container): string => (string) ($this->containerLabel($container, 'com.docker.compose.service') ?? data_get($container, 'Names.0', '')))
            ->values();
    }

    private function formatContainerSnapshot(array $container): array
    {
        $id = (string) ($container['Id'] ?? '');
        $name = ltrim((string) data_get($container, 'Names.0', ''), '/');
        $service = (string) ($this->containerLabel($container, 'com.docker.compose.service') ?? $name);

        return [
            'id' => substr($id, 0, 12),
            'name' => $name,
            'service' => $service,
            'image' => (string) ($container['Image'] ?? ''),
            'state' => (string) ($container['State'] ?? 'unknown'),
            'status' => (string) ($container['Status'] ?? 'unknown'),
            'created_at' => Carbon::createFromTimestamp((int) ($container['Created'] ?? 0))->toIso8601String(),
            'ports' => $this->formatPorts($container['Ports'] ?? []),
            'stats' => $this->fetchContainerStats($id),
            'processes' => $this->fetchContainerProcesses($id),
        ];
    }

    private function formatPorts(mixed $ports): array
    {
        if (!is_array($ports)) {
            return [];
        }

        return collect($ports)
            ->filter(fn ($port): bool => is_array($port))
            ->map(fn (array $port): array => [
                'ip' => $port['IP'] ?? '0.0.0.0',
                'public_port' => $port['PublicPort'] ?? null,
                'private_port' => $port['PrivatePort'] ?? null,
                'type' => $port['Type'] ?? null,
            ])
            ->values()
            ->all();
    }

    private function fetchContainerStats(string $containerId): array
    {
        if ($containerId === '') {
            return [];
        }

        try {
            $stats = $this->dockerRequest("/containers/{$containerId}/stats", [
                'stream' => 'false',
            ]);
        } catch (Throwable) {
            return [];
        }

        if (!is_array($stats)) {
            return [];
        }

        $cpuTotal = (float) data_get($stats, 'cpu_stats.cpu_usage.total_usage', 0);
        $cpuTotalPrev = (float) data_get($stats, 'precpu_stats.cpu_usage.total_usage', 0);
        $cpuSystem = (float) data_get($stats, 'cpu_stats.system_cpu_usage', 0);
        $cpuSystemPrev = (float) data_get($stats, 'precpu_stats.system_cpu_usage', 0);
        $cpuCores = (int) data_get($stats, 'cpu_stats.online_cpus', 1);

        $cpuDelta = max($cpuTotal - $cpuTotalPrev, 0.0);
        $systemDelta = max($cpuSystem - $cpuSystemPrev, 0.0);
        $cpuPercent = $systemDelta > 0
            ? round(($cpuDelta / $systemDelta) * max($cpuCores, 1) * 100, 2)
            : 0.0;

        $memoryUsage = (int) data_get($stats, 'memory_stats.usage', 0);
        $memoryLimit = (int) data_get($stats, 'memory_stats.limit', 0);
        $memoryPercent = $memoryLimit > 0
            ? round(($memoryUsage / $memoryLimit) * 100, 2)
            : 0.0;

        $networkMetrics = collect((array) data_get($stats, 'networks', []));
        $networkRx = (int) $networkMetrics->sum(fn (array $network): int => (int) ($network['rx_bytes'] ?? 0));
        $networkTx = (int) $networkMetrics->sum(fn (array $network): int => (int) ($network['tx_bytes'] ?? 0));

        return [
            'cpu_percent' => $cpuPercent,
            'memory_usage' => $memoryUsage,
            'memory_limit' => $memoryLimit,
            'memory_percent' => $memoryPercent,
            'network_rx' => $networkRx,
            'network_tx' => $networkTx,
            'pids' => (int) data_get($stats, 'pids_stats.current', 0),
        ];
    }

    private function fetchContainerProcesses(string $containerId): array
    {
        if ($containerId === '') {
            return [];
        }

        try {
            $top = $this->dockerRequest("/containers/{$containerId}/top", [
                'ps_args' => 'aux',
            ]);
        } catch (Throwable) {
            return [];
        }

        $titles = data_get($top, 'Titles', []);
        $processes = data_get($top, 'Processes', []);

        if (!is_array($titles) || !is_array($processes)) {
            return [];
        }

        return collect($processes)
            ->filter(fn ($row): bool => is_array($row))
            ->map(function (array $row) use ($titles): array {
                $process = [];
                foreach ($titles as $index => $title) {
                    if (!is_string($title)) {
                        continue;
                    }

                    $process[$title] = $row[$index] ?? null;
                }

                return [
                    'user' => (string) ($process['USER'] ?? ''),
                    'pid' => (string) ($process['PID'] ?? ''),
                    'cpu' => (string) ($process['%CPU'] ?? ''),
                    'memory' => (string) ($process['%MEM'] ?? ''),
                    'command' => (string) ($process['COMMAND'] ?? ''),
                ];
            })
            ->take((int) config('runtime_monitor.max_processes'))
            ->values()
            ->all();
    }

    private function dockerRequest(string $path, array $query = []): mixed
    {
        $socketPath = (string) config('runtime_monitor.socket_path');

        $response = Http::timeout((int) config('runtime_monitor.timeout_seconds'))
            ->withOptions([
                'curl' => [
                    CURLOPT_UNIX_SOCKET_PATH => $socketPath,
                ],
            ])
            ->acceptJson()
            ->get(self::DOCKER_HOST . $path, $query);

        $response->throw();

        return $response->json();
    }

    private function containerLabel(array $container, string $label): ?string
    {
        $labels = $container['Labels'] ?? null;

        if (!is_array($labels)) {
            return null;
        }

        $value = $labels[$label] ?? null;

        return is_string($value) ? $value : null;
    }
}
