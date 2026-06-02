# Messor — Production Deployment on DigitalOcean

> *Status: v1 · Target: DO App Platform or single Droplet · Last updated: 2026-06-01*

This document covers the production deployment of `apps/scraper` (Messor) on
DigitalOcean. The companion services (`apps/platform`, RabbitMQ, Postgres,
Spaces) are covered separately.

## 1. Two valid topologies

### Option A — DigitalOcean App Platform (recommended for v1)

```text
┌──────────────────────────────────────────────────────────┐
│   DO App Platform                                        │
│                                                          │
│   ┌────────────────┐  ┌────────────────┐                 │
│   │ messor-scraper │  │ inkbytes-      │                 │
│   │ (worker)       │  │ platform       │                 │
│   │ schedule loop  │  │ Laravel + nginx│                 │
│   └────────┬───────┘  └────────┬───────┘                 │
│            │                   │                          │
└────────────┼───────────────────┼─────────────────────────┘
             ▼                   ▼
       DO Spaces           DO Managed Postgres
       (inkbytes bucket)   (system of record)

             RabbitMQ (CloudAMQP or DO Managed) — over AMQPS
```

Pros: managed TLS, env vars, autodeploy from GitHub, no server to babysit.
Cons: less control over networking; cold-start on deploys.

### Option B — Single Droplet with Docker Compose

```text
┌────────────────────────── DO Droplet (Ubuntu 24.04) ─────────────────────┐
│                                                                          │
│   nginx (TLS, Let's Encrypt)                                             │
│      │                                                                   │
│      ├──► platform container (Laravel + PHP-FPM)                         │
│      └──► messor-scraper container (Python scheduled)                    │
│                                                                          │
│   docker volumes:  /var/data/messor                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

Pros: cheap (one $24/mo Droplet), full control. Cons: you own the OS.

Pick **Option A** for v1 unless cost is the binding constraint.

## 2. Container image

Use the existing `Messor/docker/Dockerfile`. Recommended hardening before prod:

```dockerfile
# Production-grade Dockerfile sketch (place at apps/scraper/Dockerfile)
FROM python:3.11-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libxml2-dev libxslt1-dev curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY apps/scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import nltk; nltk.download('punkt')"

COPY apps/scraper/ ./
COPY src/inkbytes /app/inkbytes      # until packages/contracts replaces this

USER 10001:10001                     # non-root
ENV PYTHONUNBUFFERED=1 \
    MESSOR_MODE=production

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD curl -fs http://127.0.0.1:8050/healthz || exit 1

CMD ["python", "main.py", "--schedule"]
```

Build:

```bash
docker build -f Messor/docker/Dockerfile -t inkbytes/messor:$(git rev-parse --short HEAD) .
```

## 3. Env vars to set in DO

Set in App Platform → component → Environment Variables (mark all as
**encrypted/secret**):

```
MESSOR_API_BASE_URL=https://platform.inkbytes.app/api
PLATFORM_API_TOKEN=...
DO_SPACES_KEY=...
DO_SPACES_SECRET=...
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
DO_SPACES_BUCKET=inkbytes
RABBITMQ_URL=amqps://user:pass@host/vhost
OPENAI_API_KEY=...
LOG_LEVEL=INFO
SCHEDULE_INTERVAL_MINUTES=60
```

The container reads `env.yaml` for non-secret defaults and overlays these env
vars at boot (roadmap: `pydantic-settings`).

## 4. App spec (DO App Platform)

```yaml
# .do/app.yaml (excerpt)
name: inkbytes
services:
  - name: messor-scraper
    github:
      repo: pragmatalabs/InkBytes
      branch: master
      deploy_on_push: true
    dockerfile_path: Messor/docker/Dockerfile
    instance_size_slug: basic-xs
    instance_count: 1
    run_command: python main.py --schedule
    health_check:
      http_path: /healthz
      initial_delay_seconds: 30
    envs:
      - { key: MESSOR_API_BASE_URL,  scope: RUN_TIME, type: GENERAL }
      - { key: PLATFORM_API_TOKEN,   scope: RUN_TIME, type: SECRET  }
      - { key: DO_SPACES_KEY,        scope: RUN_TIME, type: SECRET  }
      - { key: DO_SPACES_SECRET,     scope: RUN_TIME, type: SECRET  }
      - { key: RABBITMQ_URL,         scope: RUN_TIME, type: SECRET  }
      - { key: OPENAI_API_KEY,       scope: RUN_TIME, type: SECRET  }
```

## 5. CI/CD

GitHub Actions:

1. **`ci.yml`** — on PR: lint (ruff/black), test (pytest), build image, push
   to GHCR/DO Container Registry as `:pr-{n}`.
2. **`release.yml`** — on push to `master`: tag image as
   `:master-{sha}` and `:latest`; DO App Platform autodeploys.

Use a separate `staging` app spec pointing at a `staging` Spaces bucket and a
non-prod RabbitMQ vhost.

## 6. Rollback

```bash
doctl apps create-deployment <APP_ID> --image inkbytes/messor:<prev-sha>
```

Or in App Platform UI: Deployments → Roll back. Sessions in flight finish on
their own; the next cycle uses the rolled-back image.

## 7. Smoke test after deploy

1. `curl https://<app-url>/healthz` → 200
2. `curl https://<app-url>/status`  → last cycle in the last `interval+15` min
3. Check DO Spaces: a new object under `messor/staging/` since deploy
4. Check RabbitMQ management: messages flowing on `articles-scraped`
5. Check platform DB: row count on `articles` increased

## 8. Cost shape (rough, monthly)

| Item | Tier | ~USD |
|---|---|---|
| App Platform service (basic-xs) | 1 instance | 12 |
| DO Spaces (250 GB) | base + bandwidth | 5 |
| Managed Postgres (db-s-1vcpu-1gb) | shared | 15 |
| CloudAMQP Little Lemur (or DO managed broker) | shared | 0–19 |
| Log shipping (Better Stack / Axiom free tier) | small | 0–25 |
| **Total** | | **~32–75** |

Costs scale with outlet count + article volume, dominated by Spaces and DB.

## 9. See also

- [security.md](./security.md) for secret rotation before deploy
- [operations.md](./operations.md) for the runbook after deploy
- [configuration.md](./configuration.md) for env-var ↔ YAML mapping
