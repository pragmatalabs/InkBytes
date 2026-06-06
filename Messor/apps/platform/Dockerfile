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
RUN npm install --no-audit --ignore-scripts

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

# Ensure storage + cache dirs exist (storage/ is gitignored so may be absent)
RUN mkdir -p \
      storage/app/public \
      storage/framework/cache/data \
      storage/framework/sessions \
      storage/framework/testing \
      storage/framework/views \
      storage/logs \
      bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache \
    && chmod -R 775 storage bootstrap/cache

# trustProxies is set directly in bootstrap/app.php (no inline patch needed)

COPY infra/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["php-fpm"]
