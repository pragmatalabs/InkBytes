# ADR-0003 (system) — Isolate the Backoffice in its own Postgres schema; never `migrate:fresh` the pipeline

* **Status**: Accepted
* **Date**: 2026-06-02
* **Deciders**: Julián de la Rosa
* **Scope**: System-wide (refines the "one database" mechanics of ADR-0001)
* **Relates to**: [ADR-0001](./0001-consolidate-backend-into-laravel-backoffice.md) (Laravel Backoffice consolidation), [backend-architecture.md](../backend-architecture.md), [backend-handoff-review.md](../backend-handoff-review.md)

## Context

ADR-0001 mandates **one Postgres** for both Curator (pipeline) and the Laravel
Backoffice. The handoff review ([backend-handoff-review.md](../backend-handoff-review.md))
found that running both frameworks' migrations in the **same `public` schema**
is unsafe as originally specified:

1. **`php artisan migrate:fresh` drops *every* table in the schema** — including
   Curator's `events`, `articles`, `entities`, `pages`, `outlets` (live data:
   309 articles / 220 events / 29 pages) and the pgvector column. Phase 1.1's
   "done when `migrate:fresh` succeeds" would destroy the pipeline.
2. **`articles` name collision** — Curator's `articles` (`id TEXT`, `body_text`,
   `embedding vector(1536)`, enrichment fields) vs Laravel's legacy `articles`
   (`id bigint`, `external_id`, `source_id` FK, JSON). Same name, same DB,
   incompatible shapes.
3. **Two migration runners** — Laravel's `migrations` table + Curator's
   sentinel-table applier (`apply 001 if articles absent`) fight over the same
   tables.

ADR-0001 says "table ownership so migrations don't collide", but ownership
labels alone don't stop `migrate:fresh` or a name clash inside one schema.

## Decision

**One database, two Postgres schemas.**

1. **`public`** holds Curator's pipeline tables — `events`, `articles`,
   `entities`, `pages` — and the shared **`outlets`** catalogue (Curator's
   `002_outlets_table.sql` keeps the DDL). Curator's sentinel migrator is
   unchanged.
2. **`backoffice`** holds all Laravel-owned tables — `users`, `sessions`,
   `cache`, `jobs`, `curator_settings`, `api_keys`, `model_usage`, `customers`,
   `subscriptions`. Laravel's `pgsql` connection sets
   `'search_path' => 'backoffice,public'` and a migrations schema of
   `backoffice`, so `php artisan migrate` / `migrate:fresh` are **scoped to
   `backoffice` and cannot touch the pipeline tables**.
3. **`migrate:fresh` is never run against `public`.** Phase 1.1's done-criterion
   becomes a scoped `php artisan migrate` (backoffice schema), not `migrate:fresh`.
4. **Laravel does not define `articles` or `sources`.** Curator's
   `public.articles` is canonical; the legacy Laravel `articles`/`sources`
   migrations are removed (not ported). The Backoffice reads articles from
   `public` if it needs them.
5. **`outlets` stays in `public`; the Backoffice CRUDs it cross-schema** (model
   bound to `public.outlets`, reachable via the `search_path`). Curator's
   **startup auto-seed becomes seed-only-if-empty** so a Curator restart never
   overwrites admin edits.

## Consequences

**Positive**

- `migrate:fresh` is safe — it can't reach Curator's data.
- No table-name collisions; each framework migrates independently.
- Curator's heavy `outlets` reads/seed path is barely touched (one behaviour
  change: seed-if-empty).

**Negative / trade-offs**

- The Backoffice operates one table (`public.outlets`) outside its own schema —
  a small, documented cross-schema exception.
- Deviates from ADR-0001's "Backoffice owns `outlets` *via Laravel migrations*":
  here Curator owns the `outlets` **DDL**, the Backoffice owns its **data
  operations**. Recorded deliberately (ADR-0001 §3 invites ADRs for deviations).
- Two schemas to keep in mind when reasoning about the DB.

## Alternatives considered

- **Single `public` schema for both** (as originally handed off). Rejected:
  `migrate:fresh` and the `articles` clash make it unsafe.
- **Move `outlets` into `backoffice`, Curator reads it cross-schema.** Rejected
  for now: Curator's seed + frequent reads make it the heavier consumer; moving
  the table is more invasive than moving the one CRUD path.
- **Separate databases per service.** Rejected by ADR-0001 (defeats "one DB,
  one system of record"; reintroduces cross-store sync).

## Follow-ups (amends the handoff)

- **Phase 1.1**: set `search_path`/migrations schema to `backoffice`; DoD is a
  scoped `php artisan migrate`, **not** `migrate:fresh`; drop the legacy
  `articles`/`sources` migrations rather than create-then-delete.
- **Phase 1.2**: make Curator's outlets auto-seed idempotent (seed-if-empty);
  bind the Laravel outlets model to `public.outlets`.
- **Phase 3**: install `laravel/cashier` (not yet in `composer.json`).
