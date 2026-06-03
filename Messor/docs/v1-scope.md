# Messor — v1 Scope (Simple by Design)

> *Status: v1 target · Owner: Julián de la Rosa · Last updated: 2026-06-01*
>
> This document is the **new target** for Messor. It supersedes the broader
> roadmap in [product-vision.md](./product-vision.md) for v1 only. Everything
> not listed under "In scope" is **explicitly out** until v1 is shipping in
> production for 30 days.

## 0. Principle

> One agent. One job. One way to do it.

Messor v1 is a single-purpose, single-instance harvester that runs on
DigitalOcean, scrapes a fixed list of outlets on a schedule, deduplicates,
stores artifacts in DO Spaces, and emits one event type to RabbitMQ. Nothing
else.

## 1. In scope (v1)

| Capability | Choice |
|---|---|
| Runtime | Python 3.11 + Docker, `restart: always` on DO App Platform |
| Mode | Scheduled only (`python main.py --schedule`) — default 60 min cycle |
| Sources | Outlets list = static JSON file in repo (`apps/scraper/data/outlets/news_outlets_sources.json`) |
| Article fetch | `newspaper3k` |
| Dedup | URL + content hash, session-local + last-N-sessions |
| Languages | en, es (only) |
| Artifact store | DO Spaces, one bucket, two prefixes (`messor/staging/`, `messor/history/`) |
| Event bus | RabbitMQ, one exchange `messor`, one queue `articles-scraped` |
| Health | FastAPI `/healthz` + `/status` on `:8050`, internal-only |
| Logs | stdout (DO captures) + RabbitMQ exchange `messor.logs` for fan-out |
| Secrets | Env vars only (`DO_SPACES_KEY`, `DO_SPACES_SECRET`, `RABBITMQ_URL`) |
| Deploy | DO App Platform autodeploy from `master` |

## 2. Out of scope (deferred)

Each of these is **deferred to v2+**. Don't build them, don't wire them, don't
configure them.

| Removed | Reason |
|---|---|
| TinyDB | Replaced by stateless run + DO Spaces. No local DB. |
| Couchbase | Not needed; Postgres on platform side is enough. |
| Strapi CMS integration | Replaced by Laravel platform; one path, not two. |
| `platform_api` POST batches | v1 publishes events; platform consumes via worker. |
| Interactive CLI mode | Removed from production image. Dev-only. |
| `--client` flag (auto-open browser) | Dev convenience, not prod. |
| `--scrape` one-shot | Achievable via `docker exec`; not a first-class mode. |
| Embedded React dashboard (`client/`) | Moved under `apps/platform`. Out of `apps/scraper`. |
| OpenAI integration | Not Messor's concern; lives downstream (Synochi/Unitas). |
| `entopics`/`synochi`/`unitas` coupling | Pure pub/sub via RabbitMQ. No imports across services. |
| Multi-host horizontal workers | One instance is fine until > 200 outlets. |
| Celery / Beatbits orchestration | One scheduled loop is enough. |
| Configurable saving modes | One mode: stage local → upload Spaces → emit event. |
| `hermes` / `mefisto` / `walkway` NestJS gateways | Skipped. Reader uses platform Laravel API directly. |
| TinyDB slicing settings | Dead config. |
| `bifrost`, `goldengate`, GoldenGate CDC | Out of band; future integration. |
| Multiple frontends (Angular, Fuse, PowerDesktop) | One frontend: `winston-r` (Next.js). |
| OpenTelemetry tracing | Logs are enough for v1. Add when we have > 1 service in prod. |
| Outlet trust scoring | v2. v1 trusts all approved outlets equally. |

## 3. The whole picture (v1)

```text
┌───────────────────────────────────────────────────┐
│           Messor v1 (single container)            │
│                                                   │
│  Scheduled loop → for outlet in outlets:          │
│     fetch → parse → dedup → JSON file             │
│           ↓                ↓                      │
│   DO Spaces upload    RabbitMQ publish            │
└───────────────────────────────────────────────────┘
              │                    │
              ▼                    ▼
       inkbytes bucket     articles-scraped queue
              │                    │
              └──── consumed by ───┴── Entopics (separate service, v2)

   Platform (Laravel + Postgres, separate) reads events too,
   stores article rows for the reader (winston-r).
```

Everything else in the original architecture diagram is **v2+**.

## 4. Code surface (v1 target)

```text
Messor/
├── apps/
│   └── scraper/                  # the only production app in v1
│       ├── main.py               # CLI entrypoint
│       ├── core/
│       │   ├── application.py    # DI + lifecycle
│       │   ├── config.py         # YAML + env-var overlay
│       │   ├── scraper.py        # newspaper3k wrapper
│       │   └── api_server.py     # FastAPI /healthz + /status
│       ├── services/
│       │   ├── outlet_service.py     # reads local JSON in v1
│       │   ├── scraper_service.py    # the agent loop body
│       │   ├── storage_service.py    # DO Spaces only in v1
│       │   ├── message_service.py    # RabbitMQ only
│       │   └── logging_service.py
│       ├── data/
│       │   └── outlets/news_outlets_sources.json
│       ├── env.example.yaml      # committed template (no secrets)
│       └── env.yaml              # gitignored, local override
├── docs/                         # this directory
├── infra/
│   └── docker/                   # single Dockerfile + compose
└── apps/platform/                # Laravel, separate concern, separate doc
```

**Deleted from v1**: `Messor/api/`, `Messor/scraping/`, `Messor/spaces/`,
`Messor/__main__.py`, root `docker-compose.yaml`, `Messor/env.do.yaml`,
TinyDB usage, Strapi config block.

## 5. Boot path (v1)

```text
container start
  └─► main.py --schedule
        └─► Application(env.yaml + env vars)
              ├─► Config           (load + validate)
              ├─► LoggingService   (stdout + RabbitMQ)
              ├─► MessageService   (connect, retry, heartbeat)
              ├─► OutletService    (read local JSON)
              ├─► StorageService   (DO Spaces only)
              ├─► ScraperService   (wires the above)
              ├─► APIServer        (FastAPI /healthz, /status — separate thread)
              └─► scheduled loop forever
```

## 6. RabbitMQ event (v1 schema)

One event type, versioned:

```json
{
  "schema": "inkbytes.article.v1",
  "session_id": "IKPGRB-2026-06-01T00:00:00Z",
  "outlet": { "id": "bbc", "name": "BBC News" },
  "article": {
    "url": "https://www.bbc.com/news/world-...",
    "canonical_url": "...",
    "hash": "sha256:...",
    "title": "...",
    "text": "...",
    "language": "en",
    "published_at": "2026-06-01T00:00:00Z",
    "scraped_at": "2026-06-01T00:01:00Z",
    "word_count": 612
  },
  "spaces_key": "messor/staging/<session>/<hash>.json"
}
```

Frozen for v1. Schema evolution → ADR + new version (`.v2`).

## 7. Definition of Done (v1)

Messor is **v1 production-ready** when *all* of the following are true:

- [ ] Single Docker image builds reproducibly from `master`.
- [ ] Scheduled mode runs forever in a container without manual intervention.
- [ ] `env.example.yaml` is committed; real `env.yaml` is gitignored.
- [ ] All secrets read from env vars; none in the image or in git.
- [ ] DO App Platform deploys autodeploy from `master`.
- [ ] `/healthz` returns 200 within 30s of start.
- [ ] `/status` reports last cycle and per-outlet counters.
- [ ] One cycle ends-to-end produces: 1 staging JSON, 1 DO Spaces object per
      outlet with articles, 1 RabbitMQ event per article.
- [ ] Duplicates across last 5 sessions are dropped before publishing.
- [ ] Container restart resumes cleanly; in-flight work either completes or
      is retried next cycle.
- [ ] 7 consecutive days of green cycles in staging before promoting to prod.

## 8. Simplification summary (vs. current state)

| Layer | Current state (many) | v1 (one) |
|---|---|---|
| Outlet registry | Platform API + local JSON fallback + Strapi | Local JSON file only |
| Article egress | REST POST + RabbitMQ + Spaces | RabbitMQ + Spaces |
| Storage | TinyDB + local JSON + Spaces + Postgres + Couchbase | Spaces only (Messor side) |
| Modes | interactive, one-shot, scheduled, client | Scheduled only |
| Shared models | `inkbytes` symlink + `models` + `xModels` + `common` | Inlined into `apps/scraper`; extract later |
| Frontends | Angular × 3 + Laravel + Next.js | Next.js (`winston-r`) only |
| API gateways | hermes + mefisto + walkway (NestJS) | None — winston-r calls platform Laravel directly |
| Logs sinks | console + file + RabbitMQ | stdout + RabbitMQ |
| Config | YAML with embedded secrets | YAML template + env-var secrets |

## 9. Order of work (suggested)

1. **Sanitize secrets** (this PR): replace tokens in `env.yaml` with
   placeholders, add `env.example.yaml`, gitignore real config.
2. **Rotate all leaked keys** in their providers (outside the repo).
3. **Trim production image**: remove `--client` and interactive CLI from the
   prod image (still available in dev image).
4. **Add `/healthz` + `/status`** if not present; bind to `0.0.0.0:8050`.
5. **Drop TinyDB and Strapi code paths** from `apps/scraper`.
6. **Add `pydantic-settings`-based config loader** with env-var overlay for
   every secret in `configuration.md` §4.
7. **Add Tenacity retries** around `core/scraper.py` and DO Spaces upload.
8. **Lock the v1 event schema** in `packages/contracts/events/article-v1.json`.
9. **Wire DO App Platform** with `.do/app.yaml`.
10. **Run 7 days in staging**, then promote.

## 10. What this does NOT change

- The Notion product narrative.
- The downstream pipeline (Entopics / Synochi / Unitas) — they keep doing
  what they do, just consuming the RabbitMQ event.
- The reader (`winston-r`) — out of scope for this milestone.
- The platform (`apps/platform`) — has its own scope; consumes events on its
  own queue if/when needed.

---

**Related**: [product-vision.md](./product-vision.md) ·
[architecture.md](./architecture.md) ·
[deployment-digitalocean.md](./deployment-digitalocean.md) ·
[security.md](./security.md)
