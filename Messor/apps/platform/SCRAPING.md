# Scraping Worker Control Panel

This document explains how to run the scraping queue and connect a remote worker command.

## Environment Variables

Add these variables to `apps/platform/.env` (or `.env.docker` if needed):

```dotenv
SCRAPING_REMOTE_HOST=user@remote-server
SCRAPING_COMMAND=/home/deploy/scraper/run.sh
SCRAPING_LOG_DIR=/home/deploy/scraper/logs
SCRAPING_PROCESS_TIMEOUT=
SCRAPING_SSH_BINARY=ssh
SCRAPING_SSH_PORT=22
SCRAPING_SSH_KEY_PATH=
SCRAPING_SSH_OPTIONS=BatchMode=yes,StrictHostKeyChecking=no
```

If `SCRAPING_REMOTE_HOST` is empty, `SCRAPING_COMMAND` runs locally on the app server.

## Queue Worker (Required)

The scraping runner is dispatched as a queued job on queue `scraping`.

Run this command on the application server:

```bash
php artisan queue:work --queue=scraping
```

For long-running scraping tasks, this is recommended:

```bash
php artisan queue:work --queue=scraping --tries=1 --timeout=0
```

## Supervisor Example

```ini
[program:messor-scraping-worker]
process_name=%(program_name)s_%(process_num)02d
command=php /var/www/html/artisan queue:work --queue=scraping --tries=1 --timeout=0 --sleep=2
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
numprocs=1
user=www-data
redirect_stderr=true
stdout_logfile=/var/www/html/storage/logs/supervisor-scraping-worker.log
stopwaitsecs=3600
```

After updating supervisor config:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart messor-scraping-worker:*
```
