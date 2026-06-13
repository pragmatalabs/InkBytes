<?php

return [
    'enabled' => env('RUNTIME_MONITOR_ENABLED', true),
    'project' => env('RUNTIME_MONITOR_PROJECT'),
    'socket_path' => env('RUNTIME_MONITOR_SOCKET_PATH', '/var/run/docker.sock'),
    // When set (e.g. http://docker-socket-proxy:2375), reach the Docker API over
    // TCP via the read-only socket proxy instead of the raw unix socket. The
    // raw socket is host-root; the proxy exposes only GET /containers + /info.
    'docker_host' => env('RUNTIME_MONITOR_DOCKER_HOST'),
    'max_processes' => env('RUNTIME_MONITOR_MAX_PROCESSES', 6),
    'timeout_seconds' => env('RUNTIME_MONITOR_TIMEOUT_SECONDS', 3),
];
