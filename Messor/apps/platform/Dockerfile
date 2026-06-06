# InkBytes Backoffice — multi-stage production Dockerfile
# Stage 1: build Vite assets (node)
# Stage 2: PHP-FPM runtime with pre-built assets baked in
#
# The nginx container (nginx:1.27-alpine) is separate (see infra/docker-compose.prod.yml)
# and serves static files + proxies PHP requests to this container on :9000.

# ── Stage 1: Node (Vite asset build) ─────────────────────────────────────────
FROM node:20-alpine AS node-builder
WORKDIR /app

COPY package*.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build        # emits public/build/


# ── Stage 2: PHP-FPM runtime ─────────────────────────────────────────────────
FROM php:8.4-fpm-alpine AS runtime

# System deps
RUN apk add --no-cache \
    git curl unzip bash libpng-dev libjpeg-turbo-dev freetype-dev \
    libpq-dev oniguruma-dev icu-dev libzip-dev gettext

# PHP extensions
RUN docker-php-ext-configure gd --with-freetype --with-jpeg && \
    docker-php-ext-install -j$(nproc) \
      pdo_pgsql pgsql mbstring exif bcmath zip gd intl pcntl

# Composer
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

WORKDIR /var/www/html

# Composer deps first (cache layer)
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader --no-scripts

# Application source
COPY . .

# Pre-built Vite assets from stage 1
COPY --from=node-builder /app/public/build ./public/build

# Laravel bootstrap
RUN php artisan package:discover --ansi || true

# Permissions
RUN chown -R www-data:www-data storage bootstrap/cache && \
    chmod -R 775 storage bootstrap/cache

# Laravel trust proxies for Traefik (inline patch — idempotent)
# If bootstrap/app.php already has trustProxies this is a no-op.
RUN php -r "
\$f = 'bootstrap/app.php'; \$c = file_get_contents(\$f);
if (strpos(\$c, 'trustProxies') === false) {
    \$c = str_replace(
        '\$app->withMiddleware(function (Middleware \$middleware) {',
        '\$app->withMiddleware(function (Middleware \$middleware) { \$middleware->trustProxies(at: \"*\");',
        \$c
    );
    file_put_contents(\$f, \$c);
}
" || true

COPY infra/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["php-fpm"]
