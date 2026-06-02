<?php

$timeout = env('SCRAPING_PROCESS_TIMEOUT');
$sshOptionsRaw = env('SCRAPING_SSH_OPTIONS', 'BatchMode=yes,StrictHostKeyChecking=no');

return [
    'remote_host' => env('SCRAPING_REMOTE_HOST'),
    'command' => env('SCRAPING_COMMAND'),
    'log_dir' => env('SCRAPING_LOG_DIR', '/tmp/scraping'),
    'process_timeout' => is_numeric($timeout) ? (float) $timeout : null,
    'ssh_binary' => env('SCRAPING_SSH_BINARY', 'ssh'),
    'ssh_port' => (int) env('SCRAPING_SSH_PORT', 22),
    'ssh_key_path' => env('SCRAPING_SSH_KEY_PATH'),
    'ssh_options' => array_values(array_filter(array_map(
        static fn (string $option): string => trim($option),
        explode(',', (string) $sshOptionsRaw)
    ))),
];
