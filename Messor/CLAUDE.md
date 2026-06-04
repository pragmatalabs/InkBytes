# Messor — Service Briefing (Claude Code handoff)

> *Read this first if you're working on Messor.*
> *Status: monorepo cleaned, v1 scope locked · Last updated: 2026-06-02*

## What this service is

Messor is the **24/7 harvester agent** of the InkBytes platform. Single
responsibility: scrape news outlets, dedup, stage JSON, emit one
`event.article.scraped` event per article. Nothing more.

Per [ADR-0005](./docs/adr/0005-messor-curator-responsibility-split.md):
Messor does **not** do NLP, clustering, or synthesis. That's Curator.

## Layout

```
Messor/
├── apps/
│   ├── scraper/                  ← THE service (cd here for code work)
│   │   ├── main.py               ← CLI: scheduled / one-shot / interactive
│   │   ├── core/
│   │   │   ├── application.py    ← DI + lifecycle
│   │   │   ├── config.py         ← YAML loader
│   │   │   ├── scraper.py        ← newspaper3k wrapper, dedup, filter
│   │   │   └── staging_store.py  ← JSON-file staging (replaces TinyDB)
│   │   ├── services/
│   │   │   ├── scraper_service.py
│   │   │   ├── outlet_service.py
│   │   │   ├── storage_service.py    ← local JSON + DO Spaces upload
│   │   │   ├── message_service.py    ← RabbitMQ publisher
│   │   │   ├── analytics_service.py
│   │   │   └── logging_service.py
│   │   ├── api/                  ← FastAPI surface (health, status)
│   │   ├── data/outlets/         ← seed JSON files (LATAM + global EN)
│   │   ├── env.example.yaml / env.yaml / env.local.yaml
│   │   ├── requirements.txt · pyproject.toml
│   └── platform/                 ← Laravel (deferred to post-v0)
├── packages/inkbytes/            ← shared kernel (Python pkg, pydantic v1)
│   └── inkbytes/{common,models,database}/   ← real source, self-contained (ADR-0007)
├── docs/                         ← contracts, architecture, ops, ADRs
├── infra/docker/                 ← Dockerfile, dev compose
├── scripts/                      ← dev-up.sh, dev-smoke.sh, commit-v1-docs.sh
```

## Where to pwd

```bash
cd /Volumes/Pragmata/Projects/InkBytes/Messor/apps/scraper
source .venv/bin/activate
```

## Bring up + run

```bash
# from repo root: dev infra (Postgres + RabbitMQ + MinIO)
cd /Volumes/Pragmata/Projects/InkBytes
bash orchestrator/scripts/up.sh

# venv: ALWAYS build with the native Python (arm64 on Apple Silicon).
# Never use `arch -x86_64 python3` — that produces an x86_64 venv whose
# compiled extensions (.so files) won't load under the native interpreter.
cd Messor/apps/scraper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

# verify architecture after install:
python3 -c "import platform; print(platform.machine())"  # must print arm64

# one cycle — starts FastAPI on :8050 + runs one scrape + exits
python main.py env.local.yaml --scrape

# continuous mode (production)
python main.py env.local.yaml --schedule
```

Smoke check:

```bash
bash /Volumes/Pragmata/Projects/InkBytes/Messor/scripts/dev-smoke.sh
```

## Messor admin (retired client → Backoffice)

The legacy React/MUI dashboard that lived at `Messor/client/` (:5174) was
**retired in B12.3** — the InkBytes **Laravel Backoffice** is now the single
admin (ADR-0001 "one admin"; see `docs/adr/0001`/`0006`). With it went the
client-only `:8050` endpoints (`/api/scrape/ws`, `/api/scrape/status`,
`/api/scrape/results`, `/api/scrape/session/{id}/view`).

The FastAPI `:8050` surface now serves only what the Backoffice consumes:
- `GET /api/scrapesessions` — paginated run history (reads `data/scrapes/*.db.json`)
- `GET /api/outlets` — outlet catalogue (reads `data/outlets/outlets.json`)

Scrape triggering, live logs, run history, and Outlets CRUD all live in the
Backoffice now; per-session results are durable in `public.scrape_sessions`
(Messor emits `scrape.session.completed` → Curator persists; ADR-0006).

**Do not** create a `standalone.py` or any bypass server — run everything
through `main.py` exactly as production does. See `api/routers/scrape.py`
for the remaining endpoint implementations.

## What Messor produces (the contract)

One RabbitMQ event per article on exchange `messor`, routing key
`event.article.scraped`. Schema: `inkbytes.article.v1`. Full spec:
[`docs/contracts.md`](./docs/contracts.md).

Curator codes against that JSON. If you change Messor's output shape,
**you change the contract** — bump the schema version, update the ADR,
and tell Curator's owner. Don't silently add fields.

## Required env vars (production)

```bash
export DO_SPACES_KEY='...'
export DO_SPACES_SECRET='...'
export RABBITMQ_URL='amqps://user:pass@host/vhost'
export PLATFORM_API_TOKEN='...'      # deferred in v0; future Laravel API
```

In dev with the orchestrator running, defaults in `env.local.yaml` point
at `localhost`.

## Code style (Python)

- snake_case for variables/functions, PascalCase for classes
- Imports: stdlib → third-party → local (one blank line between groups)
- Type hints on every public signature
- Google-style docstrings (Args / Returns / Raises)
- Specific `except` blocks; log + re-raise unless we have a fallback
- Pydantic **v1** (deliberately — see Anti-patterns below)

## Status checklist (live)

- [x] Monorepo migration (apps/, packages/, infra/, docs/) — INK-1
- [x] requirements.txt cleaned + pinned — INK-2
- [x] TinyDB + Strapi dropped — INK-5
- [x] Curator-shaped responsibilities removed (NLP, topics, clustering) — INK-11
- [x] `hermes` exchange renamed to `messor.logs` — ADR-0004
- [x] Sandbox-tested: imports clean, scrape pipeline runs
- [ ] Production Dockerfile + health endpoints — INK-3
- [ ] Env-var overlay via pydantic-settings — INK-4
- [ ] Tenacity retries + circuit breaker — INK-6
- [ ] Lock `inkbytes.article.v1` schema in `packages/contracts/events/` — INK-7
- [ ] `.do/app.yaml` autodeploy — INK-8
- [ ] CI: lint + test + image build — INK-9
- [ ] 7-day staging soak — INK-10

See [`docs/sprint-1-backlog.md`](./docs/sprint-1-backlog.md) for the full Sprint-1 plan.

## Anti-patterns to avoid

- **Don't call `newspaper3k.Article.nlp()`** — that's heuristic NLP, owned by Curator. We removed it in INK-11; don't add it back.
- **Don't populate** `entities`, `topics`, `summary`, `sentiment`, `factual`, `cluster`, `similars`, `related` on Article. Curator does. See [`docs/contracts.md`](./docs/contracts.md) §1.2.
- **Don't add `openai:` / `topics_extracted` / `clusters_path`** to `env.yaml`. Those are Curator config.
- **Don't upgrade pydantic to v2.** Messor's `Article` model uses v1 BaseModel; the shared `inkbytes` package depends on v1. Pydantic v2 lives in Curator only.
- **Don't import from `Curator/`.** Cross-service code is the RabbitMQ event JSON, not Python imports.

## Where to read more

| Topic | File |
|---|---|
| What v1 looks like (scope, DoD) | [`docs/v1-scope.md`](./docs/v1-scope.md) |
| C4 architecture + agent loop | [`docs/architecture.md`](./docs/architecture.md) |
| Output schema (the contract) | [`docs/contracts.md`](./docs/contracts.md) |
| Configuration reference | [`docs/configuration.md`](./docs/configuration.md) |
| Security + secrets | [`docs/security.md`](./docs/security.md) |
| 24/7 runbook | [`docs/operations.md`](./docs/operations.md) |
| Local-only quickstart | [`docs/local-dev.md`](./docs/local-dev.md) |
| Sprint-1 backlog | [`docs/sprint-1-backlog.md`](./docs/sprint-1-backlog.md) |
| All decision records | [`docs/adr/`](./docs/adr/) |
