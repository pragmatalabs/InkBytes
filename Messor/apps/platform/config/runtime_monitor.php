<?php

return [
    'enabled' => env('RUNTIME_MONITOR_ENABLED', true),
    'project' => env('RUNTIME_MONITOR_PROJECT'),
    'socket_path' => env('RUNTIME_MONITOR_SOCKET_PATH', '/var/run/docker.sock'),
    'max_processes' => env('RUNTIME_MONITOR_MAX_PROCESSES', 6),
    'timeout_seconds' => env('RUNTIME_MONITOR_TIMEOUT_SECONDS', 3),
];
