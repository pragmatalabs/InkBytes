# ADR-0006 (system) — Scrape-results browser reads Messor-persisted sessions in Postgres

* **Status**: Accepted (decision made; implementation tracked as backlog B12)
* **Date**: 2026-06-03
* **Deciders**: Julián de la Rosa
* **Scope**: System-wide (Messor harvester + Backoffice)
* **Relates to**: [ADR-0001](./0001-consolidate-backend-into-laravel-backoffice.md) (one admin), [ADR-0003](./0003-backoffice-schema-isolation.md) (one DB, owned tables), [messor-admin-p2-p3-plan.md](../messor-admin-p2-p3-plan.md) (B12), [messor-admin-gap-analysis.md](../messor-admin-gap-analysis.md) (Gap 4)

## Context

ADR-0001 mandates a single admin (the Laravel Backoffice) and calls for retiring the
legacy Messor React client (`Messor/client`, :5174). Reconfirmed against the code, the
Backoffice already covers everything the client does (scrape trigger, SSE logs,
Postgres-backed run history, full Outlets CRUD) **except one feature**: the
**per-session scrape-results browser** — each harvest session with per-outlet article
counts, dedup stats, and timestamps.

That result data, including the **new-vs-duplicate** determination, is computed and
owned by **Messor (Python)** in its file-based staging (`data/scrapes/*.db.json`).
The open question was where the Backoffice should read it from:

- **A · Proxy Messor `:8050`** — call `/api/scrapesessions`. Fast (B4 already does this),
  but couples the UI to the flaky `:8050` process and to ephemeral, retention-bounded
  staging files; no durable history.
- **C · Backoffice re-derives** — extend the Laravel `RunScrapingWorker` to record
  results itself. Avoids the API/client, but **duplicates Messor's dedup logic** in PHP
  (a second source of truth that drifts when Messor changes) and quietly couples to
  Messor's staging file format anyway.
- **B · Messor → Postgres** — Messor persists its already-computed session results to a
  shared table; the Backoffice reads it.

## Decision

**Option B.** Per-session scrape results become durable in a
**`public.scrape_sessions`** table (Postgres), and the Backoffice reads it (cross-schema
read, no writes — consistent with how it reads Curator's `public` tables under ADR-0003).

**Mechanism (refined 2026-06-04, B12.1): Messor emits, Curator persists.**
Rather than give Messor a Postgres connection, Messor **emits** a
`scrape.session.completed` event over its existing RabbitMQ `messor` topic exchange
(routing key `event.scrape.session.completed`); **Curator consumes it and upserts
`public.scrape_sessions`**. This keeps Messor Postgres-free (it already owns RabbitMQ
publishing) and keeps the DB owner (Curator) as the sole writer, matching the existing
`event.article.scraped` emit→consume pattern.

- **Messor stays the single owner of dedup/result computation** — it computes
  new/duplicate/total per outlet exactly as today and emits the result; **Curator**
  writes the row; the Backoffice only displays.
- The table lives in `public` (Messor/Curator pipeline domain), DDL owned by a
  **Curator migration** (`004_scrape_sessions.sql`), Backoffice-read-only.
- Decouples the results browser from the flaky `:8050` API and from file-staging
  retention; gives durable history.
- **Granularity:** one event per harvest *run* (across all outlets), keyed by a stable
  run id `session-<unix_ts>` (matching the `/api/scrapesessions` run-level view, with a
  per-outlet `outlets[]` array). Curator upserts `ON CONFLICT (session_id)` so a re-emit
  refreshes the same row. Messor accumulates per-outlet stats at the run boundary
  (`execute_scraping_process`) and emits once at the end.

## Consequences

**Positive**
- Durable, queryable run/session history independent of `:8050` uptime or file retention.
- One owner of "what is a duplicate" (Messor) — no logic duplication, no drift.
- Fits ADR-0003 ("one DB, owned tables, cross-schema reads are fine").
- Unblocks decommissioning `Messor/client/` and the dead `:8050 /api/scrape*` endpoints.

**Negative / cost**
- A real **Messor change**: Messor must emit a new run-level event (a `scrape_sessions`
  emitter on the existing publish path). The schema/migration + the actual write live on
  the **Curator** side (Curator owns `public` DDL + is the consumer). Messor gains **no**
  Postgres dependency.
- Two record paths during transition (file staging + the emitted event → DB) until the
  file staging is retired.

## Status update (2026-06-04)
- **B12.1 done.** Curator migration `004_scrape_sessions.sql` (+ applier registration),
  Curator consumer (`consume_scrape_sessions` → `_handle_scrape_session` → upsert), and
  Messor emit (`publish_scrape_session_completed` + run-boundary accumulation in
  `scraper_service.execute_scraping_process`) all landed and round-trip-verified on live
  infra.
- **B12.2 done.** Backoffice read-only **Scrape Results** browser: `ScrapeSession` model
  (bound to `public.scrape_sessions`, read-only), `ScrapeResultsController` (B7-paginated
  list + per-session `outlets[]` detail, defensive empty-state), `GET /scrape-results`
  (all-authenticated), nav entry, `ScrapeResults/Index.jsx`. Empty + populated paths
  verified live (probe row inserted then deleted; table left at 0). **B12.3** (decommission
  `Messor/client/` + dead `:8050 /api/scrape*` endpoints) remains.

## Alternatives considered
- **A (proxy :8050)** — rejected as the durable answer (couples to a flaky service +
  ephemeral files); acceptable only as a *temporary interim* reusing B4's proxy if the
  browser is wanted before Messor's persistence lands.
- **C (Backoffice re-derives)** — rejected: duplicates Messor's dedup domain logic in PHP
  and still couples to the staging file format; "zero dependency" is largely illusory.

## Related decision (same planning round)
- **ADR-0004 reaffirmed — KEEP Curator on env keys.** The Backoffice `api_keys` table
  stays management-only; Curator does not read DB keys. Consequence: backlog **B8** ships
  *one-active-per-provider* + *rotation history* only; *last-used* and *spend-per-key*
  are "N/A by design" unless ADR-0004 is later reversed.

## Follow-ups (B12 implementation, when scheduled)
1. Define `public.scrape_sessions` schema (session id, started/ended, per-outlet counts,
   new/duplicate/total, success rate) — Messor/Curator-side migration.
2. Add the Messor writer (persist on session completion, alongside or replacing file staging).
3. Backoffice **Scrape Results** browser (sessions list + per-session detail), read-only.
4. Verify the trigger path end-to-end, then decommission `Messor/client/` + its launch
   configs + the now-dead `:8050 /api/scrape*` endpoints (verify sole consumer first).
