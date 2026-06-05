# ADR-0007 (system) — Container topology: per-service containers + Curator API/worker split

* **Status**: Accepted (Curator split implemented; prod compose drafted; deploy = D6)
* **Date**: 2026-06-04
* **Deciders**: Julián de la Rosa
* **Scope**: System-wide / deployment
* **Relates to**: [ADR-0001](./0001-consolidate-backend-into-laravel-backoffice.md) (one admin), [ADR-0003](./0003-backoffice-schema-isolation.md) (one DB), [ADR-0004](./0004-curator-config-from-db-keys-via-env.md), [ADR-0006](./0006-scrape-results-via-messor-postgres.md), [Messor ADR-0007](../../Messor/docs/adr/0007-self-contained-shared-kernel.md) (Messor Docker), [STATUS.md](../STATUS.md) (deploy D6)

## Context

InkBytes runs as several long-lived services (Messor harvester, Curator pipeline,
Laravel Backoffice, Reader) over shared infra (Postgres+pgvector, RabbitMQ, MinIO, and
now Ollama for local embeddings). The deploy target is a **single DigitalOcean droplet**
(STATUS D6). The dev orchestrator (`orchestrator/docker-compose.dev.yaml`) already
containerises infra + `messor`/`curator`/`reader`/`admin` (build:), and each app has a
Dockerfile (Curator `apps/curator/Dockerfile`; Messor `infra/docker/scraper.Dockerfile`).

Running these as **bare processes** (as in this dev session) caused real failures:
- Curator was a background `python main.py` — when it was killed, the **whole pipeline
  stalled silently** and the RabbitMQ queue backed up to ~13k messages; the Reader (which
  reads `:8060`) and Backoffice System Health went dark.
- **`--consume` couples the API and the consumer**: `main.py` set
  `long_running = args.consume or args.api_only`, so `--consume` *also* binds the FastAPI
  `:8060`. That made `--api-only` and `--consume` fight over the port and made it
  impossible to run more than one consumer — yet the consumer (LLM-latency-bound enrich +
  cluster + synthesize) is exactly the part that needs to scale.

## Decision

**1. Each service is its own container image** (already true in the dev compose). No
monolith, no shared interpreter — Messor (pydantic v1) and Curator (pydantic v2 + asyncpg
+ aio-pika + instructor) stay isolated; the cross-service contract remains RabbitMQ JSON
(ADR-0006) + the shared Postgres (ADR-0003).

**2. Curator = one image, multiple roles** (the load-bearing decision here):

| Role | CMD | Replicas | Binds :8060 | Purpose |
|---|---|---|---|---|
| **curator-api** | `--api-only` | 1 | yes | Read surface for Reader + Backoffice (status/events/outlets) |
| **curator-worker** | `--worker` | N (scalable) | **no** | The LLM pipeline: enrich → cluster → synthesize → DB |

`--worker` is **new** (this ADR): it runs the full consumer (`run_consumer` — articles +
scrape-sessions + commands) **without** binding the API port, so workers scale to N
replicas with no port clash. `--consume` (API + consumer combined) is retained for
single-process / dev use. Verified: `--worker` boots in REAL mode, binds the consumers,
serves no HTTP, and coexists with a live `--api-only` on `:8060`.

**3. The Laravel admin is one image, three roles** — `admin-web` (php-fpm + nginx),
`admin-queue` (`queue:work --queue=scraping`, the scrape-trigger jobs), `admin-scheduler`
(`schedule:run` cron, the B11 alert evaluator). These are the two background processes we
kept hand-starting; in prod they're supervised containers.

**4. Messor = harvester container** running `--schedule` (autonomous continuous harvest,
the documented production mode) plus its `:8050` API (Run History / System Health read it).

**5. `restart: always` + healthchecks on every service** — self-healing. The exact
"Curator killed → pipeline stalled → 13k backlog" failure from this session does not
happen when the runtime supervises and restarts the worker.

**6. One `orchestrator/docker-compose.prod.yaml` on the droplet**, reverse proxy
(Traefik/nginx) terminating TLS and routing the public Reader + the admin.

## Consequences

**Positive**
- Self-healing (restart policies) — no more silent pipeline stalls from a dead process.
- The bottleneck (LLM enrich) scales independently: bump `curator-worker` replicas to
  drain a backlog; `curator-api` stays a single lightweight replica.
- Dependency isolation per service; clean api/worker separation removes the `:8060`
  port-conflict footgun.
- Fits the existing dev compose + the single-droplet target.

**Negative / open items**
- **On-demand scrape trigger is dev-only.** Today the Backoffice `RunScrapingWorker` runs
  a **local shell command** (`bash -lc … main.py --scrape …`). Across containers the
  Backoffice can't `bash` into the Messor container. Prod options: (a) Messor on
  `--schedule` (autonomous; Backoffice = monitor) — the default in this topology; or (b) a
  trigger **bridge** — the Backoffice publishes a `scrape.requested` command Messor
  consumes (mirrors ADR-0006's emit→consume). **Follow-up.**
- **Admin-app identity is unresolved.** The dev compose declares `admin` =
  `Reader/apps/admin` (Next.js), but the admin we actually built (RBAC, audit, cost,
  moderation, alerting — ADR-0001/0005, B1–B13) is the **Laravel Backoffice** at
  `Messor/apps/platform`. ADR-0001's "one admin" must pick one. **Decide before the prod
  compose is final** (this is what the in-progress `*-refactor-findings.md` is mapping).
- More containers to orchestrate; secrets (Anthropic/OpenAI keys, APP_KEY, DB/RMQ creds)
  need a real mechanism (Docker secrets / env file / Doppler), not committed `.env`.
- Ollama embedding container (per 2026-06-04 lessons-learned) adds GPU/CPU + model-pull
  considerations on the droplet.

## Alternatives considered
- **All-in-one container / monolith** — rejected: couples Messor (v1) and Curator (v2)
  deps, no independent scaling, no isolation.
- **Bare processes + a supervisor (systemd/pm2)** — rejected: no dependency isolation, and
  it's exactly the fragile setup that stalled the pipeline this session.
- **Keep `--consume` as the only consumer mode** — rejected: it binds `:8060`, so workers
  can't scale and api/worker fight over the port.

## Follow-ups
1. `orchestrator/docker-compose.prod.yaml` (drafted alongside this ADR) — finalise once
   the admin-app decision lands.
2. The scrape-trigger bridge (Messor `scrape.requested` consumer) for on-demand harvests.
3. Secrets management + domain/TLS (Traefik) + the github-do-cicd pipeline (D6).
4. Decide managed Postgres (DO) vs containerised pgvector on the droplet.
