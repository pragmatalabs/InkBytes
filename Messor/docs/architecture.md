# Messor — Architecture

> *Status: Living doc · Owner: Julián de la Rosa · Last updated: 2026-06-01*

This document describes Messor's architecture using a **C4-style** layering
(Context → Container → Component) plus a **separation-of-concerns** view that
matches the actual code under `apps/scraper/`.

For the product framing, see [product-vision.md](./product-vision.md). For ops,
see [operations.md](./operations.md).

## 1. Context (C4 L1)

```text
                ┌──────────────────────────────────────────┐
                │              InkBytes Platform           │
                │  (Laravel API, winston-r reader, billing)│
                └───────────────────▲──────────────────────┘
                                    │ articles, sessions, outlets
                                    │ (REST + RabbitMQ events)
                          ┌─────────┴─────────┐
   Outlet sources ───────►│      MESSOR        │◄─── Operators
   (HTML, RSS, files)     │   harvester agent  │     (CLI + dashboard)
                          └─────────┬─────────┘
                                    │ raw artifacts (HTML, JSON)
                                    ▼
                          DigitalOcean Spaces
```

**Actors**

| Actor | Interaction |
|---|---|
| Outlet sources | Polled by Messor (HTTP / feeds / files) |
| InkBytes Platform | Receives article batches, scrape sessions, exposes outlet registry |
| RabbitMQ broker | Carries `articles-scraped`, `topics-extracted`, log messages |
| DO Spaces | Object store for staging files and historical archives |
| Operators | CLI commands, scheduled-mode tuning, React dashboard |

## 2. Containers (C4 L2)

The repo is a **monorepo**:

```text
Messor/
├── apps/
│   ├── platform/   # Laravel + Inertia + React (MUI)  — control plane / API
│   └── scraper/    # Python scraper service           — the agent (this doc)
├── packages/
│   └── contracts/  # Shared schemas (scaffold)
├── infra/
│   └── docker/     # Docker Compose, Dockerfiles, nginx
└── docs/           # This documentation
```

| Container | Tech | Role |
|---|---|---|
| `apps/scraper` | Python 3.10+, FastAPI, newspaper3k, BeautifulSoup, pika | The harvester agent (subject of this doc) |
| `apps/platform` | Laravel 11, Inertia, React + MUI | Outlet registry, article ingestion, admin |
| `client/` (legacy) | React + TS | Operator dashboard (being absorbed by platform) |
| RabbitMQ | External (`kloudsix.io` today, DO/CloudAMQP for prod) | Event bus + log fan-out |
| DO Spaces | S3-compatible | Raw + staged artifact store |
| Postgres | Managed DO (target) | System of record (via platform) |

## 3. Components — inside `apps/scraper` (C4 L3)

```text
┌─────────────────────────────────────────────────────────────┐
│                       apps/scraper                          │
│                                                             │
│  ┌─────────────┐    main.py     ┌────────────────────────┐  │
│  │   CLI       │──── invokes ──►│  Application           │  │
│  │ argparse    │                │  (core/application.py) │  │
│  └─────────────┘                │  - DI container         │  │
│         ▲                       │  - lifecycle owner      │  │
│         │                       │  - mode selector        │  │
│         │                       └─────────┬──────────────┘  │
│         │                                 │ wires            │
│         │                                 ▼                  │
│  ┌──────┴────────┐                ┌───────────────────────┐ │
│  │ APIServer     │◄──────uses─────┤ services/             │ │
│  │ (FastAPI)     │                │  ├─ outlet_service    │ │
│  │ core/api_…    │                │  ├─ scraper_service   │ │
│  └───────────────┘                │  ├─ storage_service   │ │
│         ▲                         │  ├─ message_service   │ │
│         │ HTTP                    │  ├─ analytics_service │ │
│   operators / platform            │  └─ logging_service   │ │
│                                   └──────────┬───────────┘ │
│                                              │              │
│                          ┌───────────────────┼──────────┐   │
│                          ▼                   ▼          ▼   │
│                  core/scraper.py     DO Spaces      RabbitMQ│
│                  (newspaper3k,       (artifacts)    (events)│
│                   ThreadPool)                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Component responsibilities (separation of concerns)

| Component | Single responsibility | Knows about | Doesn't know about |
|---|---|---|---|
| **Config** (`core/config.py`) | Load + expose YAML config | Filesystem, env vars | Services, transport |
| **LoggingService** | Structured logs to console/file/RabbitMQ | Config, RabbitMQ exchange | Business logic |
| **MessageService** | RabbitMQ connect, publish, consume, heartbeat | Config, pika, queues | Article content |
| **OutletService** | Resolve list of news outlets (API → local fallback) | Platform REST, local JSON | Scraping, storage |
| **ScraperService** | Run a scraping *session* per outlet, dedup | Outlets, scraper module, ThreadPool | Storage destinations |
| **core/scraper.py** | Actually fetch + parse an article via newspaper3k | HTTP, parsing libs | Business policy |
| **StorageService** | Persist sessions + upload to DO Spaces + push API | DO Spaces, Platform REST, local FS | NLP, clustering |
| **AnalyticsService** | Compute session-level stats | Sessions in memory | I/O |
| **APIServer** | FastAPI HTTP surface (`/scrape`, `/status`, …) | Services it exposes | Transport details |
| **CommandProcessor** | Interactive CLI verbs (SCRAPE, MOVE, CLEAN, EXIT) | All services via Application | HTTP |
| **Application** | Wire everything, choose mode, hold the lock | All of the above | None below itself |

### 3.2 Execution modes

| Mode | Trigger | Use case |
|---|---|---|
| **Interactive** | `python main.py` | Local dev, manual ops |
| **One-shot** | `python main.py --scrape` | Backfills, smoke tests |
| **Scheduled** | `python main.py --schedule` | **Production** — Docker container loop, interval from `scraping.schedule_interval_minutes` (default 60) |
| **Client** | `python main.py --client` | Launches React dashboard locally |

In production we run **scheduled mode** inside a container with
`restart: always`, plus the FastAPI surface for health/status checks.

## 4. The agent loop

```text
        ┌───────────────────────────────────────────┐
        │             scheduled-mode loop           │
        │                                           │
        │   ┌──► acquire process lock ──────────┐   │
        │   │           │                       │   │
        │   │           ▼                       │   │
        │   │   OutletService.get_outlets()     │   │
        │   │           │                       │   │
        │   │           ▼                       │   │
        │   │   for outlet in outlets (pool):   │   │
        │   │     ScraperService.create_..._session(outlet) │
        │   │       ├─ fetch via newspaper3k    │   │
        │   │       ├─ filter by language       │   │
        │   │       ├─ filter min_word_count    │   │
        │   │       ├─ dedup vs current + prev  │   │
        │   │       ├─ write staging JSON       │   │
        │   │       ├─ StorageService → DO Spaces│   │
        │   │       ├─ StorageService → Platform │   │
        │   │       └─ MessageService → RabbitMQ │   │
        │   │           │                       │   │
        │   │           ▼                       │   │
        │   │   AnalyticsService.summary()      │   │
        │   │           │                       │   │
        │   │           ▼                       │   │
        │   │   release lock                    │   │
        │   │           │                       │   │
        │   │           ▼                       │   │
        │   └─── sleep(schedule_interval) ──────┘   │
        └───────────────────────────────────────────┘
```

Key invariants:

1. **Single instance per host** — process lock prevents overlapping cycles.
2. **Idempotent per article** — dedup keyed by canonical URL + content hash.
3. **At-least-once delivery** — RabbitMQ events use confirm-mode (TODO if not
   already set; see ADR-0002).
4. **Crash-safe** — staging files are written before any cloud upload; a crash
   between staging and upload retries on next cycle.

## 5. Data flow

```text
Outlet → HTML/RSS ─► newspaper3k ─► Article{title, text, lang, url, hash}
                                        │
                                        ▼
                              Dedup (session + history)
                                        │
                                        ▼
            scraping_session.json (per-cycle, per-outlet)
                                        │
                ┌───────────────────────┼───────────────────────┐
                ▼                       ▼                       ▼
       DO Spaces                Platform REST            RabbitMQ event
       inkbytes/messor/         POST articles/batch      articles-scraped
       staging/{uuid}.json      POST scrapesessions      (downstream: Entopics)
```

## 6. Cross-cutting concerns

| Concern | How it's handled today | Production target |
|---|---|---|
| Configuration | YAML (`env.yaml`) with defaults | YAML + env-var overlay; **no secrets in repo** |
| Secrets | ⚠️ Committed in `env.yaml` (must rotate) | DO env vars / Doppler / 1Password |
| Logging | console + file + RabbitMQ exchange `hermes` | Add Better Stack / Axiom shipper |
| Metrics | AnalyticsService in-memory + session JSON | Prometheus exporter on FastAPI |
| Tracing | None | OpenTelemetry SDK around session + HTTP calls |
| Health | FastAPI `/status` (to confirm/add) | `/healthz` + `/readyz` for DO |
| Rate limiting | Per-thread HTTP, no global RPS cap | Token bucket per outlet domain |
| Retries | Implicit via newspaper3k | Tenacity wrapper with backoff + jitter |
| Lock | In-process threading.Lock | Add file/Redis lock for multi-host |

## 7. Failure modes & responses

| Failure | Detection | Response |
|---|---|---|
| Outlet 5xx / timeout | newspaper3k exception | Skip outlet this cycle, log, increment per-outlet error counter |
| All outlets fail | Session reports 0 articles | Page on-call; check egress/DNS |
| RabbitMQ down | Pika exception | Buffer events to local JSON queue (`data/rabbit/queue.json`), retry next cycle |
| DO Spaces 5xx | boto error | Keep staging file local, retry next cycle |
| Platform API down | HTTP non-2xx | Save session locally, retry next cycle |
| Concurrent cycle | Lock held | Skip cycle, log warning |
| Disk full (staging) | OS error | Crash → container restarts → ops alert |

## 8. Open questions / decisions pending

1. Confirm-mode publishing on RabbitMQ (ADR-0002).
2. Move from Strapi-style endpoints to Laravel platform REST cleanly.
3. Replace in-process ThreadPool with per-outlet workers via Celery/Bullmq.
4. Adopt `pydantic-settings` for config + secrets layering.
5. Drop `inkbytes` symlink to `src/inkbytes` in favor of `packages/contracts`.

## 9. Reference

- Code: `apps/scraper/core/application.py`, `apps/scraper/services/*`
- Config schema: [configuration.md](./configuration.md)
- Runbook: [operations.md](./operations.md)
- Production deploy: [deployment-digitalocean.md](./deployment-digitalocean.md)
- Decisions: [adr/](./adr/)
