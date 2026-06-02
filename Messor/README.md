# Messor Monorepo

Messor is now being migrated to a monorepo architecture with a Laravel + Inertia + React (MUI) platform and a Python-based scraper service.

## Monorepo Structure

```text
apps/
  platform/        # Laravel API + Inertia React (Vite) + MUI
  scraper/         # Legacy Python scraper stack (migrated from repo root)
packages/
  contracts/       # Shared contracts/schemas (scaffold)
infra/
  docker/          # Docker Compose, Dockerfiles, nginx config
```

## Phase 1 + 2 Status

Implemented:
- Monorepo scaffolding (`apps/`, `packages/`, `infra/`)
- Laravel app bootstrapped in `apps/platform`
- Inertia React scaffolding enabled in Laravel
- MUI added and wired globally via theme provider
- Python scraper moved to `apps/scraper`
- Root `main.py` compatibility wrapper preserved
- Docker baseline added for:
  - Laravel PHP-FPM app
  - Laravel queue worker
  - Laravel scheduler
  - Node/Vite dev server
  - nginx reverse proxy
  - PostgreSQL
  - Redis
  - Python scraper service profile

## Local Development

### Platform (Laravel + Inertia + MUI)

```bash
cd apps/platform
composer install
npm install --legacy-peer-deps
php artisan migrate
php artisan serve
npm run dev
```

### Scraper (Python)

```bash
cd apps/scraper
python3 main.py env.yaml
```

Backward-compatible root entrypoint still works:

```bash
python3 main.py
```

## Docker (Phase 2 Baseline)

```bash
cd infra/docker
cp .env.example .env

docker compose up --build
```

Services:
- Platform HTTP: `http://localhost:8080`
- Platform Vite HMR: `http://localhost:5173`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Optional scraper profile:

```bash
docker compose --profile scraper up --build
```

## Next Phases

- Replace legacy Strapi-dependent data paths with Laravel/PostgreSQL domain models
- Move scraping result ingestion into Laravel jobs/events
- Introduce shared typed contracts in `packages/contracts`
- Remove legacy frontend/API artifacts after parity
