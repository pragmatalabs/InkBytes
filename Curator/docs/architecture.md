# Curator — Architecture

> *Status: v0 · Owner: Julián de la Rosa · Last updated: 2026-06-02*

Curator is a single Python service that turns Messor's harvested articles
into reader-ready one-pagers. For v0 it collapses what the long-term
architecture splits into three services (Entopics, Synochi, Unitas).

## Context (C4 L1)

```text
                     ┌──────────────────────────────────────┐
                     │   READER (Reader/apps/web, Next.js)  │
                     └──────────────────▲───────────────────┘
                                        │ GET /events, /events/{id}
                                        │
                     ┌──────────────────┴───────────────────┐
                     │              CURATOR                  │
                     │   3 skills: enrich · cluster · synth │
                     └──┬───────┬────────┬───────┬──────────┘
                        │       │        │       │
                  RabbitMQ   Postgres   Spaces  Anthropic
                  (messor)   (events,  (raw     (Haiku)
                             pgvector) articles)
                        ▲
                        │ event.article.scraped
                        │
                     ┌──┴────────────┐
                     │    MESSOR     │
                     └───────────────┘
```

## Containers (C4 L2)

```text
Curator/
├── apps/curator/             single Python service (FastAPI + asyncio)
│   ├── main.py               CLI entry: --consume | --fixture | --api-only
│   ├── core/
│   │   ├── application.py    DI, lifecycle, pipeline orchestrator
│   │   ├── config.py         YAML + env-var overlay
│   │   └── api_server.py     FastAPI: /healthz /readyz /status /events*
│   ├── services/
│   │   ├── llm_service.py    Anthropic via instructor; stub mode offline
│   │   ├── embedding_service.py  OpenAI text-embedding-3-small; stub
│   │   ├── database_service.py   asyncpg + pgvector
│   │   └── message_service.py    aio-pika consumer
│   ├── skills/
│   │   ├── enrich.py         Skill 1
│   │   ├── cluster.py        Skill 2
│   │   └── synthesize.py     Skill 3
│   ├── contracts/            Pydantic v2 models for the v1 event schema
│   ├── prompts/              Haiku prompts (.md files for diff-ability)
│   └── db/migrations/        SQL — events, articles, entities, pages
```

## Component model (C4 L3 — the skills)

Each skill is a class with a single async `run()` method. Composition:

```text
Application._handle_event(event)
    │
    ├─► db.upsert_article_raw(article, spaces_key)        ← contract row
    │
    ├─► enrich.run(article)                                ← Skill 1 (LLM)
    │       returns EnrichmentResult
    │
    ├─► embed.embed(title + text[:4000])                   ← OpenAI
    │       returns list[float] (1536)
    │
    ├─► db.write_enrichment(...)                           ← persist
    │
    ├─► cluster.run(article_id, embedding, entities, …)    ← Skill 2 (DB)
    │       returns ClusterResult(event_id, source_count, …)
    │
    └─► if source_count >= min_sources_to_publish:
            synthesize.run(event_id)                       ← Skill 3 (LLM)
            publishes a pages row, sets events.status='published'
```

## Concurrency

- One asyncio event loop.
- A `Semaphore(max_concurrent_articles)` caps how many ENRICH+CLUSTER
  pipelines run in parallel. Default 4.
- aio-pika prefetch is 4 — matches the semaphore.
- Postgres pool: `pool_min`..`pool_max` (default 2..10).

## Data flow

```text
RabbitMQ msg (JSON ArticleScrapedEvent)
   │
   ▼
Pydantic validate → ArticleV1
   │
   ▼
Postgres INSERT INTO articles (raw fields)
   │
   ▼
Haiku ENRICH → EnrichmentResult
   │
   ▼
OpenAI embed → vector(1536)
   │
   ▼
Postgres UPDATE articles SET enriched_at, topic, …, embedding
            INSERT INTO entities …
   │
   ▼
SQL find-nearest with pgvector <=> + entity overlap
   │
   ├─ match  → UPDATE event_id; recompute source_count
   └─ no match → INSERT INTO events …
   │
   ▼
if source_count ≥ min_sources_to_publish:
    SELECT all articles in cluster
    Haiku SYNTHESIZE → PageV1
    INSERT INTO pages …
    UPDATE events SET status='published'
```

## Cross-cutting concerns

| Concern | v0 | Production target |
|---|---|---|
| Config | YAML + env-var overlay | same |
| Secrets | env vars only | DO env vars / Doppler |
| Logging | structlog → stdout | + RabbitMQ exchange `curator.logs` (post-v0) |
| Metrics | none | Prometheus on FastAPI |
| Tracing | none | OpenTelemetry around each skill |
| Retries | none | tenacity wrappers on LLM + DB + RMQ |
| Idempotency | `articles.id` PK ON CONFLICT DO NOTHING | + outbox table for events |
| Cost guard | none | per-cycle $ cap + circuit breaker |

## Operating modes

| Mode | Command | When |
|---|---|---|
| Fixture | `python main.py --fixture fixtures/sample_article.json` | Offline dev (no broker, no API keys) |
| Consumer | `python main.py --consume` | Production; consumes RabbitMQ forever |
| API only | `python main.py --api-only` | Diagnostics; runs the HTTP surface only |

## Production deploy

Same Droplet as Messor + Reader. Single `docker-compose.prod.yaml` in the
parent `orchestrator/`. Container reads `env.yaml` for topology and env
vars for secrets.

## Failure modes

| Failure | Detection | Response |
|---|---|---|
| Anthropic 5xx / rate limit | LlmService raises | Tenacity (D3) — retry with backoff; drop on persistent failure |
| OpenAI embed fails | EmbeddingService raises | Hold the article (no event_id); retry on next consume cycle |
| Postgres unreachable | asyncpg raises | aio-pika requeues the message |
| Bad JSON from LLM | instructor re-prompts up to N times, then raises | Drop the article, log, alert |
| Cluster query slow | observe via `/status` p95 | Reduce `recent_window_hours` |
| Outbox / dedup | `articles.id` PK | ON CONFLICT DO NOTHING |

## What we don't do (v0)

- No agent framework (LangGraph, CrewAI, AutoGen). Three sequential
  function calls don't need one.
- No fine-tuning. Haiku zero-shot with the prompts in `prompts/` is the
  whole strategy.
- No multi-LLM routing. One vendor (Anthropic) for v0. Locked.
- No vector DB outside Postgres. pgvector is enough for ~10⁶ articles.

## See also

- [`Messor/docs/contracts.md`](../../Messor/docs/contracts.md) — input contract
- [`docs/configuration.md`](./configuration.md) — every env knob
- [`docs/adr/0001-curator-collapses-pipeline.md`](./adr/0001-curator-collapses-pipeline.md)
