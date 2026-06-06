#!/bin/sh
# InkBytes Backoffice — production entrypoint (php-fpm container)
# Waits for Postgres, runs migrations, caches config, starts FPM.
set -e
cd /var/www/html

APP_ENV="${APP_ENV:-production}"

echo "[entrypoint] Waiting for Postgres..."
until php artisan db:monitor --databases=pgsql 2>/dev/null; do
    echo "[entrypoint] db not ready, retrying in 3s..."
    sleep 3
done

echo "[entrypoint] Running migrations..."
php artisan migrate --force

echo "[entrypoint] Caching routes / views / config..."
if [ "$APP_ENV" = "production" ] || [ "$APP_ENV" = "staging" ]; then
    php artisan route:cache
    php artisan view:cache
    php artisan config:cache
else
    php artisan route:clear
    php artisan view:clear
    php artisan config:clear
fi

echo "[entrypoint] Fixing storage permissions..."
chown -R www-data:www-data storage/ bootstrap/cache/ 2>/dev/null || true

echo "[entrypoint] Starting nginx + php-fpm via supervisord..."
exec "$@"
