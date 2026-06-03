# Backend Consolidation Handoff — Validation Review

> *Status: review · Owner: Julián de la Rosa · Reviewer: Claude Code · Date: 2026-06-02*
>
> Audit of [`backend-handoff.md`](./backend-handoff.md) against the actual codebase,
> before any tab starts. Verdict: **direction sound; Phase 1.1 as originally written is
> destructive.** Resolution recorded in
> [`adr/0003-backoffice-schema-isolation.md`](./adr/0003-backoffice-schema-isolation.md);
> the handoff has been patched accordingly.

## Verified codebase facts

| Fact | Source |
|---|---|
| Laravel platform is real: Laravel 13 + Inertia/React, on SQLite | `Messor/apps/platform` (`composer.json`, `config/database.php:20`) |
| Models present: `Source`, `ScrapeRun`, `Article`, `ScrapingJob`, `User` | `app/Models/` |
| Laravel migrations create `articles` **and** `sources` (legacy shapes) | `database/migrations/2026_04_12_000006`, `…000003` |
| Curator owns `public` tables `events`, `articles`, `entities`, `pages` (+pgvector) | `db/migrations/001_initial_schema.sql` |
| Curator also owns `outlets` and **seeds it from `outlets.json` on every startup** | `db/migrations/002_outlets_table.sql`, `core/application.py:45-52` |
| Curator applies SQL via sentinel tables (`apply 001 if articles absent`) | `services/database_service.py:39-50` |
| Laravel has `sanctum` + `breeze`; **no `cashier`** | `composer.json` |
| Live data at audit time: 31 outlets, 309 articles, 220 events, 29 pages | Postgres `inkbytes` |

## Findings

### 🔴 Blockers (would corrupt data / fail if run as written)

1. **`migrate:fresh` on the shared DB destroys Curator's pipeline.** It drops every
   table in the schema; Laravel + Curator share `inkbytes`/`public`. → wipes
   events/articles/entities/pages/outlets + the pgvector column.
2. **`articles` name collision.** Curator `articles` (`id TEXT`, `body_text`,
   `embedding vector(1536)`) vs Laravel `articles` (`id bigint`, `external_id`,
   `source_id` FK). Same name, incompatible shapes, one DB.
3. **`outlets` dual-ownership + auto-seed clobber.** Curator re-seeds `outlets` on
   every startup; Backoffice CRUD edits would be overwritten on the next Curator boot.
4. **Two migration runners** (Laravel `migrations` table vs Curator sentinel applier)
   race over the same tables.

### 🟡 Medium

- **Cashier not installed** — Phase 3 must `composer require laravel/cashier`.
- **Reader `/admin` currently live** (fixed + served via Curator `--api-only` on
  2026-06-02). Phase 1.2 deletes it — consistent with ADR-0001; the running
  Curator-for-admin simply becomes unnecessary.

### ✅ Sound as written
Phases **2.1** (DB config + env fallback + refresh), **2.2** (`model_usage` sink
alongside the existing log line — `cost_meter.py` is a clean extension point), **2.3**
(RMQ command consumer, no new HTTP), **3** (Cashier/Sanctum/Breeze). Table-ownership
*intent* is correct; only the **1.1/1.2 execution mechanics** were unsafe.

## Resolution (applied)

Recorded in [ADR-0003](./adr/0003-backoffice-schema-isolation.md) and patched into the
handoff:

1. **Two schemas, one DB.** Curator pipeline in `public`; Laravel in `backoffice`
   (`search_path=backoffice,public`). `migrate:fresh` becomes scoped to `backoffice`
   and can't touch the pipeline.
2. **Forbid `migrate:fresh` on `public`;** Phase 1.1 DoD is a scoped `php artisan migrate`.
3. **Laravel drops the legacy `articles`/`sources` migrations** (don't port); Curator's
   `public.articles` is canonical.
4. **Curator outlets auto-seed → seed-if-empty;** Backoffice CRUDs `public.outlets`.
5. **Phase 3 installs Cashier.**
