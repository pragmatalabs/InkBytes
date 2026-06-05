# InkBytes — End-to-End Architecture & Runtime Flow

> *Status: v1 · Owner: Julián de la Rosa · Last updated: 2026-06-04*
>
> A single-document tour of how InkBytes works at runtime: the services, the data
> stores, the message topology, and the four flows (harvest → process → read →
> operate). Engineering truth lives in [`STATUS.md`](./STATUS.md); the backend
> consolidation decision is [`adr/0001`](./adr/0001-consolidate-backend-into-laravel-backoffice.md);
> schema isolation is [`adr/0003`](./adr/0003-backoffice-schema-isolation.md).

## 1. What InkBytes is

A paid, ad-free news reader. For every newsworthy **event**, the reader sees one
elegant page synthesized from multiple sources — headline, ~200-word synthesis,
entity context, and an evidence rail of quoted snippets with links. The reader pays
to skip the noise.

That promise is produced by a **harvest → process → read** pipeline, with a single
Laravel **Backoffice** beside it as the control plane.

## 2. Services & ports

| Service | Tech | Port | Role |
|---|---|---|---|
| **Messor** | Python (FastAPI, newspaper3k) | 8050 | Harvester — fetch, dedup, stage, publish events |
| **Curator** | Python (FastAPI + aio-pika) | 8060 | LLM pipeline — enrich, cluster, synthesize; 3 queue consumers |
| **Reader** | Next.js (React) | 3000 | Public site — renders published pages (read-only) |
| **Backoffice** | Laravel 13 + Inertia/React/MUI | 8011 | The single admin / control plane |
| PostgreSQL + pgvector | — | 5432 | System of record (two schemas) |
| RabbitMQ | — | 5672 / 15672 | Event bus + management HTTP API |
| DO Spaces / MinIO | S3 | 9000 | Raw + staged article artifacts |

Bring the stack up locally: `bash orchestrator/scripts/up.sh`. The Backoffice also
needs two background processes for its async features: `php artisan queue:work
--queue=scraping` (runs scrape jobs) and `php artisan schedule:work` (runs the alert
cron).

## 3. Topology at a glance

```text
                                exch: messor (topic)                     exch: curator.commands (topic)
News outlets ─fetch─▶ Messor ─event.article.scraped────▶ Curator ◀─publish/unpublish/drop──── Backoffice
  (31, EN+ES)        :8050   ─event.scrape.session.completed─▶  :8060   ─resynthesize/recluster─┘   :8011
                       │                                          │                                  │
                       └─artifacts─▶ DO Spaces (S3)               │ writes public.*                  │ reads public.* (RO)
                                                                  ▼                                  ▼ R/W backoffice.*
   Reader :3000 ──GET /events, /events/{id}──▶ Curator     PostgreSQL + pgvector  :5432
   (public, ISR cache, pwd gate)                           ├── public      (Curator owns)
                                                           │     events · articles · entities · pages · outlets · scrape_sessions
                                                           └── backoffice  (Laravel owns)
                                                                 users(+role) · curator_settings · api_keys · model_usage
                                                                 audit_logs · alerts · scraping_jobs
   Curator polls backoffice.curator_settings every 30s (live config; no redeploy)
```

## 4. The four flows

### Flow 1 — Harvest (Messor)

A run starts on Messor's own schedule **or** from the Backoffice "▶ Iniciar
Scraping" button, which dispatches a queued `RunScrapingWorker`. That worker shells
the Messor one-shot harvester (`--no-api`, optionally `--outlets=slug,…` and
`--limit=N`). Selected slugs are allowlisted against `public.outlets` and bounded
(`1..200`), so a `bbc; rm -rf /` style argument is rejected at validation and never
reaches a shell.

Messor then:

1. Resolves the outlet catalogue,
2. Fetches articles via newspaper3k,
3. Dedups and filters by language + minimum word count,
4. Stages JSON and uploads raw + staged artifacts to Spaces,
5. **Publishes one `event.article.scraped` message per article** (`inkbytes.article.v1`)
   to the `messor` topic exchange,
6. At end of run, emits a single `event.scrape.session.completed` carrying per-outlet
   stats.

### Flow 2 — Process (Curator)

Curator runs three queue consumers on the bus. The main one drains
`curator.articles-scraped` and applies three skills per article:

1. **ENRICH** — one Haiku 4.5 call → `{entities[], topic, sentiment, factuality,
   summary_50w, keywords}`.
2. **Embed + CLUSTER** — OpenAI `text-embedding-3-small` (1536-dim) → pgvector cosine
   search (≥ 0.62) gated by entity overlap → assign/create an `event_id`.
3. **SYNTHESIZE** — once an event has **≥ 2 distinct sources**, one Haiku call writes
   the reader-facing `pages` row (headline, ~200-word synthesis, evidence rail).

Every LLM call is metered (`CostMeter`) and persisted to `backoffice.model_usage`
(fire-and-forget, non-fatal). Two side consumers: `curator.scrape-sessions` upserts
`public.scrape_sessions`; `curator.commands` applies moderation (Flow 4). All writes
land in the `public` schema that Curator owns.

### Flow 3 — Read (Reader)

The Next.js Reader calls Curator directly: `GET /events` (list) and `GET
/events/{id}` (page), via `CURATOR_API_URL`, with ISR caching (60s list / 300s page)
behind a shared demo-password gate. It only ever reads published pages — no admin,
no write path.

### Flow 4 — Operate (Backoffice)

The Laravel app is the **single admin** (ADR-0001). It owns the `backoffice` schema
and reads `public.*` **read-only** across schemas (ADR-0003 — it never writes
Curator's tables). Surfaces: Outlets CRUD (`public.outlets`), Curator Settings, API
Keys, Cost & Usage, Moderation, Run History, Scrape Results, System Health, Alerts,
Audit Log, and Users/RBAC.

Two indirect loops make Curator "part of the backend" without the backend writing its
tables:

- **Live config:** Curator **polls `backoffice.curator_settings` every 30s**, so an
  admin changing a model or threshold takes effect with no redeploy (ADR-0004).
- **Moderation via commands:** publish / unpublish / drop / re-synthesize / re-cluster
  are published on the `curator.commands` exchange; Curator consumes and applies the
  write.

## 5. Message topology (RabbitMQ)

| Exchange | Type | Routing key | Consumer queue | Purpose |
|---|---|---|---|---|
| `messor` | topic | `event.article.scraped` | `curator.articles-scraped` | per-article enrich/cluster/synthesize |
| `messor` | topic | `event.scrape.session.completed` | `curator.scrape-sessions` | durable per-run scrape results |
| `curator.commands` | topic | `page.publish` / `page.unpublish` / `page.drop` / `event.resynthesize` / `event.recluster` | `curator.commands` | Backoffice moderation actions |

The Backoffice publishes commands via the **RabbitMQ management HTTP API** (Guzzle) —
no AMQP package added on the PHP side.

## 6. Data model (one Postgres, two schemas)

Schema isolation (`search_path=backoffice,public`) lets one database safely back both
services without migration collisions. **Rule: never `migrate:fresh` against `public`.**

**`public` — Curator owns (pipeline writes):**
`events` (clusters), `articles` (Messor-harvested + enriched in place, with `embedding
vector(1536)`), `entities` (per article), `pages` (one reader-facing one-pager per
published event; `published_at` nullable for unpublish/drop), `outlets` (the
catalogue the Backoffice CRUDs), `scrape_sessions` (per-run results).

**`backoffice` — Laravel owns (Laravel migrations):**
`users` (+`role`: admin/operator/viewer), `curator_settings` (single live row of LLM
models/token caps/temperature + clustering thresholds + display-only budget),
`api_keys` (provider/label/active + `encrypted` value, masked in UI), `model_usage`
(per-call tokens + cost), `audit_logs`, `alerts`, `scraping_jobs`, plus framework
tables.

## 7. Boundaries worth remembering

- **API keys stay env-only.** Curator reads keys from the environment and never
  decrypts `backoffice.api_keys` — this avoids cross-language (Python↔Laravel) AES
  crypto. The DB rows are an admin convenience + audit surface (ADR-0004).
- **The Reader is the only public surface** and is strictly read-only. Never give it
  admin endpoints or write access.
- **One admin.** All CRUD lives in the Backoffice; the old Reader `/admin` and legacy
  Messor React client are retired (ADR-0001, B12.3).
- **Pydantic boundary:** v1 in Messor (legacy), v2 in Curator (new). The contract
  between them is the RabbitMQ JSON, not shared Python types.

## 8. Current state (per STATUS.md)

The full loop is proven on real infrastructure: a 3-outlet harvest produced **309
articles → 220 events → 29 published pages**, rendering in the Reader. The Backoffice
backlog **B1–B13 is complete** (audit log, RBAC, outlet health, cost dashboard,
health dashboard, alerting, pagination/search, import/export, scrape-results browser,
UX polish). Remaining for v0: **DigitalOcean deploy** and a **continuous scheduled
harvest cycle** (today's pages came from manual runs + a recluster).

## Related documents

- [`STATUS.md`](./STATUS.md) — live status (authoritative)
- [`backend-architecture.md`](./backend-architecture.md) — backend target design
- [`product.md`](./product.md) — mission, audience, differentiation
- [`mvp-plan.md`](./mvp-plan.md) — the one-week v0 plan
- ADRs: [`0001`](./adr/0001-consolidate-backend-into-laravel-backoffice.md) ·
  [`0003`](./adr/0003-backoffice-schema-isolation.md) ·
  [`0004`](./adr/0004-curator-config-from-db-keys-via-env.md) ·
  [`0006`](./adr/0006-scrape-results-via-messor-postgres.md) ·
  [`Curator/0001`](../Curator/docs/adr/0001-curator-collapses-pipeline.md) ·
  [`Messor/0005`](../Messor/docs/adr/0005-messor-curator-responsibility-split.md)
