# InkBytes — Production Deployment Log

> *Status: Live · Droplet: pragmata-001 (67.205.136.61) · Last updated: 2026-06-06*

## Deployment summary

| Surface | URL | Status |
|---|---|---|
| Reader (Next.js) | https://inkbytes.org | 🟡 Waiting DNS `A inkbytes.org → 67.205.136.61` |
| Backoffice (Laravel/Inertia) | https://admin.inkbytes.org | ✅ Live — Let's Encrypt cert issued |
| Curator API | http://inkbytes-curator-api:8060 (internal) | ✅ Healthy |
| Curator Worker | internal | ✅ Healthy |
| Messor | http://inkbytes-messor:8050 (internal) | ✅ Healthy, 33 outlets |
| Postgres + pgvector | internal | ✅ Healthy |
| RabbitMQ | internal | ✅ Healthy |
| MinIO | internal | ✅ Healthy |
| Ollama (bge-m3) | shared `infra-ollama` | ✅ bge-m3 pulled |

**Admin login:** `admin@inkbytes.test` / `inkbytes2026`

---

## Droplet facts

- **Host:** pragmata-001, 67.205.136.61, Ubuntu 22.04 LTS
- **Docker:** 29.2.1 / Compose v5.1.0
- **Traefik:** shared `infra-traefik-1`, Let's Encrypt resolver named `letsencrypt`
- **Shared Ollama:** `infra-ollama` on `infra-shared` network — bge-m3 pulled 2026-06-06
- **Deploy path:** `/opt/inkbytes`
- **Disk at deploy:** 155 GB total, ~27 GB free (84% used — shared with many projects)

---

## First-deploy fixes (issues found during D6, 2026-06-06)

Every fix below is committed to `master`. This log captures WHY each change was needed.

### 1. Reader — no Dockerfile existed
**File:** `Reader/apps/web/Dockerfile` (created)  
**Also:** `Reader/apps/web/next.config.ts` — added `output: 'standalone'`  
**Why:** The Reader app had no production Dockerfile. Next.js standalone mode is required for a minimal Docker image (`server.js` + static assets, no dev server).

### 2. Reader — `public/` empty, Docker COPY failed
**File:** `Reader/apps/web/public/.gitkeep` (created)  
**Why:** All placeholder SVGs were deleted in R1. Git doesn't track empty dirs, so `public/` was missing from the cloned repo on the server. `COPY --from=builder /app/public ./public` failed with "not found". Added `.gitkeep` so the directory is tracked.

### 3. Reader — healthcheck used `wget` (not in node:20-alpine)
**File:** `infra/docker-compose.prod.yml` — healthcheck changed from `curl` to `node -e "..."`  
**Why:** The compose healthcheck overrode the Dockerfile's HEALTHCHECK. Both used `curl`/`wget` which are absent in the minimal Alpine Node image. Changed to `node -e "require('http').get(...)"`.

### 4. Messor — `packages/inkbytes` not in Docker build context
**File:** `Messor/infra/docker/scraper.Dockerfile`  
**Why:** `requirements.txt` has `-e ../../packages/inkbytes` (editable install of the shared kernel). The Dockerfile only copied `apps/scraper/` — the `packages/` directory was outside the container. Added `COPY packages /workspace/packages` before pip install.

### 5. Messor — `logs/` directory missing
**File:** `Messor/infra/docker/scraper.Dockerfile`  
**Why:** Messor's logging config writes to `logs/messor.log` at startup. The directory doesn't exist in the image. Added `RUN mkdir -p logs/ data/scrapes/`.

### 6. Messor — `env.yaml` gitignored by `Messor/.gitignore`
**File:** `Messor/.gitignore` — added `!apps/scraper/env.yaml` exception; `Messor/apps/scraper/env.yaml` committed  
**Why:** `Messor/.gitignore` explicitly ignores `env.yaml`. The Docker CMD is `python main.py env.yaml --schedule`, which requires the file to exist. Added a gitignore exception and committed the production template (all secrets are `__SET_VIA_ENV__` placeholders).

### 7. Backoffice — `storage/` directory missing
**File:** `Messor/apps/platform/Dockerfile`  
**Why:** `storage/` is gitignored in Laravel. The `COPY . .` instruction doesn't include it. Added `RUN mkdir -p storage/app/public storage/framework/{cache/data,sessions,testing,views} storage/logs bootstrap/cache`.

### 8. Backoffice — inline PHP `RUN php -r "..."` parse error
**File:** `Messor/apps/platform/Dockerfile` — removed broken block  
**Also:** `Messor/apps/platform/bootstrap/app.php` — added `trustProxies(at: '*')` directly in source  
**Why:** The Dockerfile tried to patch `bootstrap/app.php` inline using `php -r "..."` with `\$` variables. Docker's Dockerfile parser treated `\$f` as an unknown instruction. Fixed by adding `trustProxies` directly in the PHP source (the correct approach) and removing the fragile inline patch.

### 9. Backoffice — `npm ci` lock file mismatch
**File:** `Messor/apps/platform/Dockerfile` — changed `npm ci` to `npm install --no-audit`  
**Why:** The Node version in `node:20-alpine` introduced new transitive deps not in the committed `package-lock.json`. `npm ci` refuses mismatches. Using `npm install` bypasses the strict check while still installing correct versions.

### 10. Backoffice — separate nginx container can't serve PHP app files
**Files:** `Messor/apps/platform/Dockerfile`, `infra/docker-compose.prod.yml`, `Messor/apps/platform/infra/docker/nginx-backoffice.conf`, `Messor/apps/platform/infra/docker/supervisord.conf`  
**Why:** The original design had two containers: `inkbytes-backoffice` (nginx) + `inkbytes-backoffice-fpm` (php-fpm). The nginx container (official `nginx:alpine`) doesn't have the Laravel files — it can't serve `public/` static assets or forward PHP requests to files that don't exist on its disk. **Fixed by combining both into one image** (nginx + php-fpm via supervisord). The Backoffice image now runs:
- supervisord → nginx (`:80`) + php-fpm (`:9000`, localhost)
- nginx proxies PHP to `127.0.0.1:9000` (same container)
- Static files served by nginx directly from `/var/www/html/public/`

### 11. Curator — `env.yaml` missing from Docker image
**File:** `Curator/apps/curator/env.yaml` committed; `Curator/.gitignore` updated  
**Why:** Curator requires `env.yaml` to exist at startup (`CuratorConfig.load()` raises `FileNotFoundError`). The file was gitignored by `Curator/.gitignore` (has `data/` and other patterns). Added the file as a committed production template — all secrets are `__SET_VIA_ENV__` placeholders, overridden at runtime by Docker env vars.

### 12. Curator — `parents[4]` IndexError in Docker
**File:** `Curator/apps/curator/core/application.py`  
**Also:** `Curator/apps/curator/data/outlets.json` committed  
**Why:** `Path(__file__).resolve().parents[4]` navigates to the monorepo root to find `outlets.json`. In Docker the app is at `/app/core/application.py` (only 2 parent levels), not the 4 of the local monorepo. Wrapped in `try/except IndexError` with fallback to `/app/data/outlets.json`. Bundled `outlets.json` into the Curator image at `data/outlets.json`.

### 13. `backoffice` PostgreSQL schema not created before migrations
**Manual fix:** `CREATE SCHEMA IF NOT EXISTS backoffice;` + `php artisan migrate:fresh`  
**Why:** Laravel migrations create tables in the schema specified by `search_path=backoffice,public`. If `backoffice` schema doesn't exist, Postgres silently falls back to `public`. Curator then can't find `backoffice.curator_settings` (schema-qualified). On first deploy: create the schema, then run migrations. The entrypoint now handles this automatically on subsequent deploys (`migrate --force` runs after schema exists from the first deploy).

### 14. Ollama — using shared `infra-ollama` instead of own container
**Files:** `infra/docker-compose.prod.yml`, `infra/.env.production.example`  
**Why:** pragmata-001 already runs `infra-ollama` (shared across projects). Running a second Ollama container wastes ~500 MB RAM on a tight droplet. Removed `inkbytes-ollama` and `inkbytes-ollama-init` services. Added `infra-shared` external network to Curator containers. Pulled `bge-m3` into the shared Ollama manually (`docker exec infra-ollama ollama pull bge-m3`).

### 15. Embeddings `base_url` seeded as `localhost` (wrong in Docker)
**Manual fix:** `UPDATE backoffice.curator_settings SET embeddings_base_url = 'http://infra-ollama:11434/v1'`  
**Why:** The migration seed copies defaults from `config/curator.php` which has `http://localhost:11434/v1` (correct for dev, wrong in Docker where the service is `infra-ollama`). Fixed directly in the DB. Future deploys: update the seed default in `config/curator.php` to use an env-configurable value.

### 16. LLM provider seeded as `anthropic` (quota exhausted)
**Manual fix:** `UPDATE backoffice.curator_settings SET llm_provider='deepseek', enrich_model='deepseek-chat', synthesize_model='deepseek-reasoner'`  
**Why:** Anthropic quota exhausted until 2026-07-01. Switched to DeepSeek in the Backoffice settings. Curator picks up within 30 seconds (DB polling, ADR-0004).

### 17. Scraping button → 422 (SCRAPING_COMMAND not in container env)
**Files:** `infra/docker-compose.prod.yml`, `Messor/apps/scraper/api/routers/scrape.py`, `Messor/apps/platform/infra/docker/supervisord.conf`  
**Why:** Three sub-issues:
- (a) `SCRAPING_COMMAND` was in `infra/.env` but not in the Backoffice container's `environment:` block — Docker Compose env files are for variable substitution, not auto-injection into all containers. Added explicitly.
- (b) The queue worker (`php artisan queue:work --queue=scraping`) wasn't running — added to supervisord.
- (c) From inside Docker, `docker exec` doesn't work (no socket). Added `POST /api/scrape/trigger` endpoint to Messor's FastAPI (runs scrape in a background thread). SCRAPING_COMMAND = `curl POST http://inkbytes-messor:8050/api/scrape/trigger`.

### 18. Worker healthcheck — `pgrep`/`ps` absent in python:slim
**File:** `infra/docker-compose.prod.yml`  
**Why:** Python's slim image strips most system utilities. Healthcheck using `pgrep` or `ps` fails with "executable not found". Changed to `python3 -c "open('/proc/1/cmdline').read()"` — reads the PID 1 cmdline via procfs, available on all Linux containers.

---

## Pending items after deploy

1. **`inkbytes.org` DNS** — add `A inkbytes.org → 67.205.136.61` at registrar. Let's Encrypt will auto-issue once DNS resolves.
2. **`inkbytes-backoffice-fpm` stale container** — the old separate fpm container is stopped but still in compose. Remove the `inkbytes-backoffice-fpm` service entry in a future compose cleanup.
3. **Seed defaults** — update `config/curator.php` to use `http://infra-ollama:11434/v1` as the prod embeddings URL default so it doesn't need a manual DB fix after `migrate:fresh`.
4. **Anthropic quota resets 2026-07-01** — switch back to Anthropic via Backoffice Settings if desired.
5. **GitHub Secrets** — set `DIGITALOCEAN_ACCESS_TOKEN`, `DO_REGISTRY`, `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY` for CI/CD auto-deploy on push.

---

## Runtime operations

```bash
# SSH into the server
ssh root@67.205.136.61

# View all InkBytes containers
docker ps --filter 'name=inkbytes-' --format 'table {{.Names}}\t{{.Status}}'

# Follow Curator logs
docker logs -f inkbytes-curator-worker

# Follow Messor logs
docker logs -f inkbytes-messor

# Follow Backoffice logs (nginx + fpm + queue-worker via supervisord)
docker logs -f inkbytes-backoffice

# Open Postgres
docker exec -it inkbytes-postgres psql -U inkbytes -d inkbytes

# Redeploy after a git push (pulls + restarts changed containers)
cd /opt/inkbytes && bash infra/deploy.sh

# Force rebuild a single service
docker build -t registry.digitalocean.com/pragmata/inkbytes-curator:latest \
  -f Curator/apps/curator/Dockerfile Curator/
docker compose -f infra/docker-compose.prod.yml --env-file infra/.env \
  up -d --force-recreate inkbytes-curator-api inkbytes-curator-worker

# DB backup
bash /opt/inkbytes/scripts/backup.sh

# RabbitMQ management UI (SSH tunnel)
ssh -L 15683:localhost:15683 root@67.205.136.61
# Then open: http://localhost:15683 (user: messor / pass: from .env)

# MinIO console (SSH tunnel)
ssh -L 9030:localhost:9030 root@67.205.136.61
# Then open: http://localhost:9030
```

---

## Architecture decisions made during deploy

| Decision | Rationale |
|---|---|
| Combined nginx+fpm in one Backoffice container | Two-container nginx+fpm requires shared volume for static files; single container via supervisord is simpler and sufficient for an admin-only tool |
| Shared `infra-ollama` for embeddings | Saves ~500 MB RAM; bge-m3 pulled once into shared instance |
| `POST /api/scrape/trigger` in Messor | Docker container can't run `docker exec` — HTTP endpoint over internal network is the clean alternative |
| `backoffice` schema created manually on first deploy | Laravel doesn't auto-create schemas; `migrate:fresh` runs after schema exists |
| DeepSeek as default LLM (post-deploy) | Anthropic quota exhausted until July 1; DeepSeek-chat (enrich) + DeepSeek-reasoner (synthesize) at ~$2/1000 articles |
