# InkBytes — Production Deployment Log

> *Status: Live on Hostinger VPS (82.112.250.139) · Last updated: 2026-06-06 · 26 Docker fixes documented*

## Live deployment (Hostinger VPS — galvanic.cloud)

| Surface | URL | Status |
|---|---|---|
| Reader (Next.js) | https://inkbytes.galvanic.cloud | ✅ Live |
| Backoffice (Laravel/Inertia) | https://admin.inkbytes.galvanic.cloud | ✅ Live |
| Curator API | internal :8060 | ✅ Healthy |
| Curator Worker | internal | ✅ Healthy |
| Messor | internal :8050 | ✅ Healthy, 34 outlets |
| Postgres + pgvector | internal | ✅ Healthy |
| RabbitMQ | internal | ✅ Healthy |
| MinIO | internal | ✅ Healthy |
| Ollama (bge-m3) | host galvanic ollama | ✅ bge-m3, 10 GB limit |

**Admin login:** `admin@inkbytes.test` / `admin2026!`  
**Reader demo:** password `letmein`  
**Data:** 7,369 articles · 362+ published pages  
**LLM:** DeepSeek-chat (enrich) + DeepSeek-reasoner (synthesize)

---

## Server facts (Hostinger VPS)

- **Host:** 82.112.250.139, Ubuntu (Hostinger KVM)
- **Docker:** pre-installed
- **RAM:** 15.62 GB total
- **Disk:** 193 GB, ~45 GB used
- **Traefik:** host-network mode, file-based routing at `/docker/traefik/config/`
- **Ollama:** shared `galvanic` project container, `inkbytes_inkbytes-internal` network connected
- **Deploy path:** `/docker/inkbytes`
- **Registry:** GitHub Container Registry `ghcr.io/pragmatalabs` (free)
- **SSH key:** `~/.ssh/galvanic_id`

---

## Architecture on this host

```
Traefik (host network, :80/:443)
  ├── inkbytes.galvanic.cloud → 127.0.0.1:18050 (Reader)
  ├── admin.inkbytes.galvanic.cloud → 127.0.0.1:18051 (Backoffice)
  ├── ai.galvanic.cloud → Open WebUI
  └── ollama.galvanic.cloud → Ollama API

inkbytes_inkbytes-internal (bridge network):
  inkbytes-reader (port 18050) → inkbytes-curator-api
  inkbytes-backoffice (port 18051) → inkbytes-postgres, inkbytes-rabbitmq
  inkbytes-messor → inkbytes-rabbitmq
  inkbytes-curator-api → inkbytes-postgres, inkbytes-rabbitmq
  inkbytes-curator-worker → inkbytes-postgres, inkbytes-rabbitmq
  ollama (connected via docker network connect)

galvanic_ollama-net (bridge network):
  ollama ← Open WebUI
```

---

## Memory budget

| Container | Limit | Typical usage |
|---|---|---|
| inkbytes-reader | 512 MB | ~40 MB |
| inkbytes-backoffice | 512 MB | ~100 MB |
| inkbytes-curator-api | 512 MB | ~100 MB |
| inkbytes-curator-worker | 1 GB | ~110 MB idle, 400 MB enriching |
| inkbytes-messor | 1.5 GB | ~400 MB scraping, 30 MB idle |
| inkbytes-postgres | unlimited (self-limits) | ~115 MB |
| inkbytes-rabbitmq | unlimited (self-limits) | ~130 MB |
| inkbytes-minio | unlimited (self-limits) | ~115 MB |
| ollama | 10 GB | 15 MB idle, 1–9 GB per loaded model |
| Open WebUI | unlimited | ~610 MB |
| **Total reserved** | **~14 GB** | **~1.5–2 GB idle** |

---

## Operational commands

```bash
# SSH into server
ssh -i ~/.ssh/galvanic_id root@82.112.250.139

# All InkBytes containers
docker ps --filter 'name=inkbytes-' --format 'table {{.Names}}\t{{.Status}}'

# Live Messor scraping log
docker logs -f inkbytes-messor 2>&1 | grep -v DEBUG

# Live Curator enrichment log
docker logs -f inkbytes-curator-worker 2>&1 | grep -v DEBUG

# Resource usage
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'

# DB access
docker exec -it inkbytes-postgres psql -U inkbytes -d inkbytes

# Redeploy after git push
cd /docker/inkbytes && git pull origin master && \
  docker compose -f infra/docker-compose.prod.yml --env-file infra/.env up -d

# Rebuild all images on server
cd /docker/inkbytes && \
  docker build -t ghcr.io/pragmatalabs/inkbytes-reader:latest -f Reader/apps/web/Dockerfile Reader/apps/web/ && \
  docker build -t ghcr.io/pragmatalabs/inkbytes-backoffice:latest -f Messor/apps/platform/Dockerfile Messor/apps/platform/ && \
  docker build -t ghcr.io/pragmatalabs/inkbytes-curator:latest -f Curator/apps/curator/Dockerfile Curator/ && \
  docker build -t ghcr.io/pragmatalabs/inkbytes-messor:latest -f Messor/infra/docker/scraper.Dockerfile Messor/ && \
  docker compose -f infra/docker-compose.prod.yml --env-file infra/.env up -d

# After reboot: reconnect Ollama to inkbytes network
docker network connect inkbytes_inkbytes-internal ollama 2>/dev/null || true

# Backup DB
docker exec inkbytes-postgres pg_dump -U inkbytes inkbytes | gzip > /tmp/inkbytes-$(date +%Y%m%d).sql.gz

# Migrate data from pragmata-001 to this server
ssh root@67.205.136.61 \
  "docker exec inkbytes-postgres pg_dump -U inkbytes -d inkbytes --schema=public --no-owner --no-privileges --format=custom" \
  | docker exec -i inkbytes-postgres pg_restore \
    -U inkbytes -d inkbytes --schema=public --clean --if-exists --no-owner --no-privileges --single-transaction
```

---

## Known post-reboot tasks

After every VPS reboot, run:
```bash
docker network connect inkbytes_inkbytes-internal ollama 2>/dev/null || true
cd /docker/inkbytes && docker compose -f infra/docker-compose.prod.yml --env-file infra/.env up -d
```

**TODO**: automate this with a systemd oneshot or Docker `--network` flag in the galvanic compose when inkbytes network exists.

---

## Deploy kit highlights

| File | Purpose |
|---|---|
| `infra/docker-compose.prod.yml` | Full production stack (Hostinger/Traefik host-network pattern) |
| `infra/.env.production.example` | All env vars documented (no secrets) |
| `infra/deploy.sh` | Idempotent on-host deploy (git pull → pull/build → up) |
| `infra/scripts/server-bootstrap.sh` | One-time server setup |
| `/docker/traefik/config/inkbytes.yml` | Traefik file routing for this host |
| `.github/workflows/deploy.yml` | CI/CD via GHCR + SSH (needs secrets) |
| `Makefile` | `make deploy`, `make cycle`, `make backup`, etc. |

---

## 26 Docker fixes during first deploy

### 1. Reader — no Dockerfile
`Reader/apps/web/Dockerfile` created. `next.config.ts`: added `output: 'standalone'`.

### 2. Reader — empty `public/` dir
`Reader/apps/web/public/.gitkeep` added. Git doesn't track empty dirs.

### 3. Reader — healthcheck used `wget` (absent in node:20-alpine)
Changed to `node -e "require('http').get(...)"`.

### 4. Messor — `packages/inkbytes` outside build context
`scraper.Dockerfile`: `COPY packages /workspace/packages` before pip install.

### 5. Messor — `logs/` dir missing at startup
`scraper.Dockerfile`: `RUN mkdir -p logs/ data/scrapes/`.

### 6. Messor — `env.yaml` gitignored
`Messor/.gitignore`: whitelisted `!apps/scraper/env.yaml`. Template committed.

### 7. Backoffice — `storage/` gitignored
`Dockerfile`: `RUN mkdir -p storage/app/public storage/framework/...`.

### 8. Backoffice — inline `php -r` Dockerfile parse error
Removed broken inline patch. Added `trustProxies` directly in `bootstrap/app.php`.

### 9. Backoffice — `npm ci` lock file mismatch
Changed to `npm install --no-audit`.

### 10. Backoffice — nginx can't serve PHP files (two-container design)
Combined nginx+fpm in one image via supervisord. `nginx-backoffice.conf` + `supervisord.conf` added.

### 11. Curator — `env.yaml` gitignored
`Curator/.gitignore` updated. `Curator/apps/curator/env.yaml` committed (all `__SET_VIA_ENV__`).

### 12. Curator — `parents[4]` IndexError in Docker path depth
`application.py`: `try/except IndexError` around monorepo path navigation. `data/outlets.json` bundled.

### 13. `backoffice` schema not created before migrations
Manual `CREATE SCHEMA IF NOT EXISTS backoffice;` before first deploy. Now in bootstrap instructions.

### 14. Shared Ollama instead of own container (pragmata-001)
Removed `inkbytes-ollama` from compose. Used `infra-ollama` on `infra-shared` network.

### 15. Embeddings `base_url` seeded as `localhost`
`UPDATE backoffice.curator_settings SET embeddings_base_url = 'http://ollama:11434/v1'`.

### 16. LLM seeded as `anthropic` (quota exhausted)
`UPDATE backoffice.curator_settings SET llm_provider='deepseek', enrich_model='deepseek-chat', synthesize_model='deepseek-reasoner'`.

### 17. SCRAPING_COMMAND not in Backoffice container env
Added to `environment:` block in compose (env file is for substitution, not auto-injection).

### 18. Worker healthcheck — `pgrep`/`ps` absent in python:slim
Changed to `python3 -c "open('/proc/1/cmdline').read()"`.

### 19. RabbitMQ management URL wrong in Docker
Added `RABBITMQ_MANAGEMENT_URL: http://inkbytes-rabbitmq:15672` to Backoffice env.

### 20. Scrape sessions pika threading bug
Documented in deployment-log. Not fixed (post-v0 — pika channel not thread-safe in scraper threads).

### 21. Messor dedup ordering bug
`scraper.py`: staging files sorted newest-first before hash comparison.

### 22. Traefik file-based routing (Hostinger — host network mode)
No `traefik-public` network. Containers publish `127.0.0.1:18050/18051`. `/docker/traefik/config/inkbytes.yml` created.

### 23. Reader auth redirect uses `0.0.0.0:3000` behind Traefik
`app/api/auth/route.ts`: `externalBase()` reads `x-forwarded-proto` + `x-forwarded-host`.

### 24. Ollama on `127.0.0.1:11434` (not reachable via `host.docker.internal`)
`docker network connect inkbytes_inkbytes-internal ollama`. Curator uses `http://ollama:11434/v1`.

### 25. APP_KEY empty in .env (heredoc expanded locally)
`php -r "echo 'base64:'.base64_encode(random_bytes(32));"` on server. Patched `.env` directly.

### 26. `deploy.resources.limits` not enforced (Swarm syntax)
Changed to `mem_limit` + `cpus` (standalone Docker Compose syntax). Applies correctly now.

---

## Pending items

See `docs/STATUS.md` for the full list. Key ones:

1. **`inkbytes.news` DNS** — add `A inkbytes.news → 82.112.250.139` and `A admin.inkbytes.news → 82.112.250.139` when ready, update `/docker/inkbytes/infra/.env` and Traefik config
2. **GitHub Secrets for CI/CD** — set `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`, `GITHUB_TOKEN` for auto-deploy on push to master
3. **Ollama post-reboot reconnect** — automate `docker network connect inkbytes_inkbytes-internal ollama` on reboot
4. **GHCR packages visibility** — set `ghcr.io/pragmatalabs/inkbytes-*` packages to public (or add `GHCR_TOKEN` to server `.env` for private pull)
5. **Phase 3 / Stripe** — subscriber gating blocked on pricing decisions
6. **`public.scrape_sessions`** — Messor threading bug prevents session events reaching Curator; Run History (B4) works via Messor API fallback
7. **Approach B entity embeddings** — event-level pgvector embeddings for better related-events similarity (corpus >1000 events)
