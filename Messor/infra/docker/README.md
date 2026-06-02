# Docker Baseline

This folder contains the Phase 2 container baseline for the monorepo migration.

## Files

- `docker-compose.yml` - orchestrates Laravel platform, PostgreSQL, Redis, and optional scraper
- `platform/php-fpm.Dockerfile` - PHP runtime for Laravel app/worker/scheduler
- `platform/node.Dockerfile` - Node runtime for Vite dev server
- `platform/nginx/default.conf` - nginx reverse proxy config for Laravel + Vite assets
- `scraper.Dockerfile` - Python runtime for scraper service

## Start

```bash
cd infra/docker
cp .env.example .env
docker compose up --build
```

## Optional Scraper Profile

```bash
docker compose --profile scraper up --build
```
