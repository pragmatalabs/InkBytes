# Epic 03 — Data Architecture

> *Make schema changes safe to ship, fix the embedding-dimension mismatch before it bites, and separate legacy from new code paths.*

Risk-links: **R-011 (High)**, **R-004 (High)**, **R-006 (Medium)**, **R-010 (Medium)** · Sprints: 2 & 3 · Total: 13 pts

---

## IB-25 · Reset pgvector dimension to 1024 (bge-m3)

**As** the Curator, **I want** the `articles.embedding` column to be `vector(1024)` matching the Ollama `bge-m3` model, **so that** the pipeline doesn't crash on insert or silently get truncated.

### Acceptance criteria

```gherkin
Given the current schema declares `vector(1536)`
And the primary embedding provider is now bge-m3 (1024-dim)
When I apply the corrected migration
Then articles.embedding is `vector(1024)`
And EmbeddingService.cfg.dimensions == 1024 in config
And any existing rows with NULL or wrong-dim embeddings are dropped or re-enriched
And IVFFlat index is rebuilt at the new dimension
```

### Notes

- Two paths: (a) `ALTER TABLE articles DROP COLUMN embedding, ADD COLUMN embedding vector(1024)` then re-embed; (b) `TRUNCATE pages, entities, articles, events CASCADE` and re-run fixtures (faster for dev).
- For prod with real data: option (a) + a background re-embed job.
- This is R-011 — must close before v0 hits real volume.

**Sprint**: 2 · **Points**: 2 · **Risk**: R-011 · **Priority**: P0

---

## IB-26 · Schema migrations runner (replace `_ensure_schema` magic)

**As** the team, **I want** a real migrations system with versions and applied/pending tracking, **so that** any structural DB change is reproducible and reviewable.

### Acceptance criteria

```gherkin
Given Curator currently auto-applies 001_initial_schema.sql only if articles table is missing
When I introduce a `schema_migrations` table and a runner
Then every .sql file in db/migrations/ is recorded with version, applied_at, checksum
And re-running is idempotent (no-op when nothing new)
And `curator-cli db:status` shows pending + applied migrations
And `curator-cli db:migrate` applies pending ones in order
```

### Notes

- Tools to evaluate: `asyncpg-migrate`, `yoyo-migrations`, `sqitch`, hand-rolled.
- Recommend hand-rolled minimal (50 LOC) — full tools are over-engineered for v0+.
- Document protocol in `docs/architecture/views/data-architecture.md`.

**Sprint**: 3 · **Points**: 3 · **Risk**: R-011 follow-up · **Priority**: P1

---

## IB-27 · IVFFlat lists tuning playbook

**As** the Curator, **I want** clear rules for when to rebuild the pgvector IVFFlat index with different `lists` values, **so that** cluster latency stays under 100ms as data grows.

### Acceptance criteria

```gherkin
Given articles table has N rows
When N crosses 10k, 100k, 1M thresholds
Then a runbook step (or automated job) rebuilds the index with `lists = sqrt(N)`
And cluster query p99 stays below 150ms
And a test query plan is included in operations.md
```

### Notes

- Formula: `lists ≈ rows / 1000` for IVFFlat per pgvector docs.
- Index rebuild is online but takes locks; schedule for low-traffic window.
- Add `cluster_query_latency_ms` to /status endpoint to detect slowdown.

**Sprint**: 4 · **Points**: 2 · **Risk**: R-006 · **Priority**: P2

---

## IB-28 · Split inkbytes package into `inkbytes-legacy` and `inkbytes-contracts`

**As** the platform team, **I want** the legacy pydantic v1 models separated from the new pydantic v2 contracts, **so that** Curator can move forward without dragging Messor into a v2 migration we don't want yet.

### Acceptance criteria

```gherkin
Given today there's one `packages/inkbytes` (pydantic v1, used by Messor)
And Curator has its own `contracts/` with pydantic v2
When I refactor into `packages/inkbytes-legacy` (v1) and `packages/inkbytes-contracts` (v2)
Then Messor imports `inkbytes_legacy.models.articles`
And Curator imports `inkbytes_contracts.article_v1`
And the RabbitMQ JSON is the only cross-version boundary
And no Python file imports from both packages
```

### Notes

- Mechanical refactor. Pair with a ruff check that fails CI if mixed imports appear.
- Sets the stage for Curator to consume contracts as a real published package post-v1.

**Sprint**: 4 · **Points**: 3 · **Risk**: R-010 · **Priority**: P2

---

## IB-29 · Article retention + archival policy

**As** the platform owner, **I want** a clear policy for how long we keep raw articles, embeddings, and pages in Postgres, **so that** the DB doesn't grow unbounded and so we can answer DPO requests.

### Acceptance criteria

```gherkin
Given each table has rows with `created_at`
When I define retention policies
Then `articles` older than 180 days move to a cold table or to DO Spaces as JSON
And `pages` are kept indefinitely (they're the product)
And `entities` follow their parent article
And `scrape_sessions` are kept for 365 days then deleted
And a nightly job enforces the policy with logs
```

### Notes

- Move-to-cold: insert into `articles_archive` (same schema, no embedding) then delete from `articles`.
- Discuss with PO: retention has product implications (re-cluster needs recent history).
- Doc in `docs/architecture/views/data-architecture.md` §"Retention".

**Sprint**: 3 · **Points**: 3 · **Risk**: R-006 (DB size) · **Priority**: P2
