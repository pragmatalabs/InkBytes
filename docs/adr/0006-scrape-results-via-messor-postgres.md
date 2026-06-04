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

**Option B.** Messor persists per-session scrape results to a Messor-owned
**`public.scrape_sessions`** table (Postgres), and the Backoffice reads it (cross-schema
read, no writes — consistent with how it reads Curator's `public` tables under ADR-0003).

- **Messor stays the single owner of dedup logic** — it computes new/duplicate/total
  per outlet exactly as today and writes the result; the Backoffice only displays.
- The table lives in `public` (Messor/Curator pipeline domain), Backoffice-read-only.
- Decouples the results browser from the flaky `:8050` API and from file-staging
  retention; gives durable history.

## Consequences

**Positive**
- Durable, queryable run/session history independent of `:8050` uptime or file retention.
- One owner of "what is a duplicate" (Messor) — no logic duplication, no drift.
- Fits ADR-0003 ("one DB, owned tables, cross-schema reads are fine").
- Unblocks decommissioning `Messor/client/` and the dead `:8050 /api/scrape*` endpoints.

**Negative / cost**
- A real **Messor change**: it's file-based today, so Messor must also write sessions to
  Postgres (a new `scrape_sessions` writer + schema/migration on the Messor/Curator side).
- Two write paths during transition (files + DB) until the file staging is retired.

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
