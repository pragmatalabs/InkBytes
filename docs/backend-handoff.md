# InkBytes — Backend Consolidation Handoff (for Claude Code agents)

> *Status: v1 · Owner: Julián de la Rosa · Last updated: 2026-06-02 (reviewed + patched for DB safety)*
>
> **Purpose.** This is the handoff for building the consolidated backend. Open one
> Claude Code tab per assignment below, paste its kickoff prompt, and the agent has
> everything it needs. The decision is locked in
> [`adr/0001-consolidate-backend-into-laravel-backoffice.md`](./adr/0001-consolidate-backend-into-laravel-backoffice.md);
> the design is in [`backend-architecture.md`](./backend-architecture.md).
>
> ⚠️ **Phases 1.1/1.2 were patched after a codebase audit** — the original
> `migrate:fresh` step would have destroyed Curator's live data. Read
> [`adr/0003-backoffice-schema-isolation.md`](./adr/0003-backoffice-schema-isolation.md)
> and [`backend-handoff-review.md`](./backend-handoff-review.md) before any DB work.

## 0. Read first (every agent, ~5 min)

1. [`docs/STATUS.md`](./STATUS.md) — live system state.
2. [`docs/backend-architecture.md`](./backend-architecture.md) — the target. **This is the spec.**
3. [`docs/adr/0001-consolidate-backend-into-laravel-backoffice.md`](./adr/0001-consolidate-backend-into-laravel-backoffice.md) — the decision + table ownership.
4. [`docs/adr/0003-backoffice-schema-isolation.md`](./adr/0003-backoffice-schema-isolation.md) — **DB-safety mechanics (read before any DB work)**, and [`docs/backend-handoff-review.md`](./backend-handoff-review.md) — why.
5. The area `CLAUDE.md` for the service you're touching (`Messor/`, `Curator/`, `Reader/apps/web/`).

## 1. Golden rules (do not violate)

- **One admin.** All CRUD goes in the Laravel Backoffice (`Messor/apps/platform`).
  Never add admin pages to the Reader. If you find `Reader/apps/web/app/admin/`, it
  is being deleted — do not extend it.
- **One database, two schemas.** Postgres + pgvector only. No SQLite. Curator's
  pipeline lives in the **`public`** schema; the Backoffice migrates into a
  **`backoffice`** schema (`search_path=backoffice,public`). See
  [ADR-0003](./adr/0003-backoffice-schema-isolation.md).
- **🚫 Never `php artisan migrate:fresh` against `public`.** Laravel migrations are
  scoped to `backoffice`; `migrate:fresh` on `public` would drop Curator's live
  pipeline data. Use scoped `php artisan migrate` only.
- **Table ownership** (so migrations don't collide):
  - *Curator owns* (`public`, pipeline writes): `events`, `articles`, `entities`,
    `pages`, **and the `outlets` DDL** (the Backoffice CRUDs `public.outlets` but does
    not own its schema — ADR-0003).
  - *Backoffice owns* (`backoffice` schema, Laravel migrations): `curator_settings`,
    `api_keys`, `model_usage`, `customers`, `subscriptions`, `users`.
  - **Laravel must NOT define `articles` or `sources`** — Curator's `public.articles`
    is canonical; the legacy Laravel `articles`/`sources` migrations are removed.
  - Touch only the tables your assignment owns. Read across the line is fine; schema
    changes across the line are not.
- **Secrets.** `api_keys` rows are encrypted at rest (Laravel `encrypted` cast),
  masked in the UI, never logged, never returned in full over the API. Env vars stay
  the bootstrap fallback. Never paste a key into chat.
- **Reuse the stack.** Breeze (auth), Sanctum (API tokens), Cashier (Stripe). Don't
  hand-roll auth or billing.
- **Conventions.** Pydantic v2 in Curator; ADRs for non-trivial decisions; prompts as
  `.md` files. Update `docs/STATUS.md` when a phase lands.

## 2. Run order & dependencies

```
Phase 1.1 ─▶ Phase 1.2 ─▶ Phase 2.1 ─▶ Phase 2.2
                                   └──▶ Phase 2.3
                                          └──▶ Phase 3
```

- **1.1 must finish before everything** (it moves Laravel onto Postgres).
- **1.2 depends on 1.1.** 2.1/2.2/2.3 depend on 1.2. 3 depends on 2.1 (needs auth/roles in place).
- 2.2 and 2.3 can run in parallel tabs once 2.1 is merged.
- Don't run 1.1 and 1.2 in two tabs at once — they both touch Laravel DB config/migrations.

Task IDs in the tracker: 1.1=#13, 1.2=#14, 2.1=#15, 2.2=#16, 2.3=#17, 3=#18.

---

## Tab A — Phase 1.1 · Point Laravel at shared Postgres, drop SQLite

**Goal.** Laravel runs on the same Postgres+pgvector Curator uses, **isolated in a
`backoffice` schema**; SQLite gone.
**cd:** `Messor/apps/platform`
**Read:** `config/database.php`, `.env.example`, `backend-architecture.md` §4,
**`adr/0003-backoffice-schema-isolation.md`** (the DB-safety mechanics).
**Do:** set `DB_CONNECTION=pgsql` pointing at the orchestrator Postgres with
`'search_path' => 'backoffice,public'` and the migrations/default schema =
`backoffice` (create the schema if absent); remove the sqlite connection + any
`database.sqlite`; **delete the legacy `create_articles` and `create_sources`
migrations** (do not port them — Curator's `public.articles` is canonical); run the
**scoped** `php artisan migrate` (creates Laravel's tables in `backoffice` only);
confirm Breeze login and the existing pages load (Sources/Runs/Articles views that
depended on the dropped tables will be reworked in 1.2).
**Don't:** ❌ run `php artisan migrate:fresh` against `public`; ❌ create new feature
tables here; ❌ touch Curator's `public` pipeline tables.
**Done when:** `php artisan migrate` succeeds into the `backoffice` schema, Curator's
`public` tables/data are untouched (verify counts unchanged), and Breeze auth works.
Update `STATUS.md`.

**Kickoff prompt:**
> Read `docs/backend-architecture.md`, `docs/adr/0001-consolidate-backend-into-laravel-backoffice.md`, and **`docs/adr/0003-backoffice-schema-isolation.md`**, then `cd Messor/apps/platform`. Switch the app from SQLite to the shared Postgres+pgvector (same instance Curator uses, `orchestrator/docker-compose.dev.yaml`), with the Laravel connection scoped to a **`backoffice` schema** (`search_path=backoffice,public`, migrations schema `backoffice`). Remove SQLite config/files and **delete the legacy `articles`/`sources` migrations** (Curator's `public.articles` is canonical — do not recreate them). Run a **scoped `php artisan migrate`** (NOT `migrate:fresh`, which would drop Curator's live `public` data) and verify Breeze auth works and Curator's `public` row counts (articles/events/pages) are unchanged. Follow `docs/backend-handoff.md` §1.

---

## Tab B — Phase 1.2 · One `outlets` table + full CRUD; delete the duplicates

**Goal.** A single `outlets` table is the catalogue; the Backoffice has real CRUD;
the duplicates are gone.
**cd:** `Messor/apps/platform` (+ reference `Curator/apps/curator/db/migrations/002_outlets_table.sql`)
**Read:** Laravel `app/Models/Source.php`, `SourceController.php`, the Curator outlets
migration, `backend-architecture.md` §4–5.
**Do:** bind a Laravel model to **`public.outlets`** (Curator owns the DDL; match its
schema: region/language/vertical/priority/active); build create/update/delete + list
in the admin (Inertia/React/MUI); migrate any rows from the old `sources` data into
`public.outlets`; **make Curator's startup outlets auto-seed idempotent
(seed-only-if-empty)** in `Curator/apps/curator/core/application.py` so a Curator
restart never overwrites admin edits; **delete** `Reader/apps/web/app/admin/`. (The
legacy `sources`/`articles` migrations were already removed in 1.1 — nothing to drop
here.)
**Don't:** ❌ change the `outlets` columns Curator/Messor depend on; ❌ move `outlets`
out of `public`; ❌ re-introduce a Laravel-owned `articles`/`sources` table.
**Done when:** an admin can CRUD an outlet, Messor/Curator pick it up, **and a Curator
restart does not revert the edit**; Reader `/admin` gone. Update `STATUS.md`.

**Kickoff prompt:**
> Read `docs/backend-architecture.md` §4–5, `docs/adr/0003-backoffice-schema-isolation.md`, and `docs/backend-handoff.md` §1. In `Messor/apps/platform`, build full CRUD against the shared **`public.outlets`** table (schema in `Curator/apps/curator/db/migrations/002_outlets_table.sql`; Curator owns the DDL) in the Inertia/React/MUI admin, and migrate old `sources` rows into it. Make Curator's startup outlets seed **idempotent (seed-if-empty)** in `core/application.py` so restarts don't clobber admin edits. Delete the `Reader/apps/web/app/admin/` page. Don't move `outlets` out of `public` or recreate a Laravel `articles`/`sources` table.

---

## Tab C — Phase 2.1 · DB-backed Curator config (settings + API keys)

**Goal.** Curator's models, thresholds, and API keys live in DB rows the admin edits.
**cd:** `Curator/apps/curator` and `Messor/apps/platform`
**Read:** `Curator/apps/curator/core/config.py`, `backend-architecture.md` §4 & §6.
**Do:** add Laravel migrations for `curator_settings` (enrich/synthesize model, token
caps, temperature, clustering thresholds) and `api_keys` (provider, encrypted value);
update `config.py` to load from these tables with env as fallback, plus a refresh
(poll or `curator.config.changed` RMQ signal); build Backoffice Settings + API-keys
screens (masked, with a "test key" action).
**Don't:** log or expose raw keys; don't remove the env fallback.
**Done when:** changing the synthesize model in the admin changes Curator's behavior
without a redeploy; keys are encrypted + masked. Update `STATUS.md`.

**Kickoff prompt:**
> Read `docs/backend-architecture.md` §6 and `docs/backend-handoff.md` §1. Add Backoffice-owned `curator_settings` and `api_keys` tables (Laravel migrations), make `Curator/apps/curator/core/config.py` load model/threshold/key config from Postgres with env fallback + a refresh signal, and build masked Settings + API-keys admin screens with a key-test action. Keys must use Laravel's `encrypted` cast, never be logged, and never be returned unmasked.

---

## Tab D — Phase 2.2 · Persist model usage + cost dashboard

**Goal.** Every LLM call's tokens+cost is stored and visible in the admin.
**cd:** `Curator/apps/curator` and `Messor/apps/platform`
**Read:** `Curator/apps/curator/services/cost_meter.py`, `backend-architecture.md` §4.
**Do:** add a `model_usage` table (call label, model, input/output tokens, cost, event
id, timestamp); extend `cost_meter.py` to insert one row per completed call; build a
read-only Backoffice dashboard (spend by model, by day, projected per 1000 articles,
per page).
**Don't:** replace the existing log line — add the DB sink alongside it.
**Done when:** a harvest produces `model_usage` rows and the dashboard renders real
spend. Update `STATUS.md`.

**Kickoff prompt:**
> Read `docs/backend-architecture.md` §4 and `Curator/apps/curator/services/cost_meter.py`. Add a `model_usage` table, make the cost meter persist one row per completed LLM call (tokens + cost + model + event), and build a read-only usage/cost dashboard in the Laravel Backoffice (by model, by day, per 1000 articles, per page). Follow `docs/backend-handoff.md` §1.

---

## Tab E — Phase 2.3 · Events/Pages moderation + re-run commands

**Goal.** Admins can review and re-run synthesis without touching the DB by hand.
**cd:** `Messor/apps/platform` (+ a consumer in `Curator/apps/curator`)
**Read:** Curator `pages`/`events` schema (`db/migrations/001`), `core/api_server.py`,
`backend-architecture.md` §6.
**Do:** Backoffice screens to list/review events + pages, publish/unpublish/drop, and
buttons that publish `re-synthesize` / `re-cluster` commands on RabbitMQ; add the
matching consumer in Curator. No new Curator HTTP endpoints beyond existing reads.
**Done when:** an admin re-synthesizes an event from the UI and the page updates.
Update `STATUS.md`.

**Kickoff prompt:**
> Read `docs/backend-architecture.md` §6 and `Curator/apps/curator/db/migrations/001_initial_schema.sql`. Build Events/Pages moderation in the Laravel Backoffice (review, publish/unpublish/drop) and re-synthesize/re-cluster actions that publish commands over RabbitMQ for Curator to consume — add the consumer in Curator, no new HTTP surface. Curator owns `events`/`pages`; Backoffice only issues commands and reads.

---

## Tab F — Phase 3 · Business layer (customers, subscriptions, roles, Reader gating)

**Goal.** Paying customers and subscriptions managed in the Backoffice; Reader gated.
**cd:** `Messor/apps/platform` and `Reader/apps/web`
**Read:** `backend-architecture.md` §4–5, `mvp-plan.md` §9 (pricing/gating).
**Do:** **install Cashier first** (`composer require laravel/cashier` — not yet in
`composer.json`; Sanctum + Breeze already are); add `customers` + `subscriptions` via
**Laravel Cashier** (Stripe) in the `backoffice` schema; staff `users` + roles;
programmatic API keys via **Sanctum**; wire Reader subscriber gating (Laravel issues a
token/session, Reader verifies — Reader stays read-only).
**Don't:** put billing logic in the Reader; don't store card data yourself (Stripe).
**Done when:** a test customer subscribes via Stripe Checkout and the Reader unlocks
full pages for them. Update `STATUS.md`.

**Kickoff prompt:**
> Read `docs/backend-architecture.md` §4–5 and `docs/mvp-plan.md` §9. In the Laravel Backoffice add customers + subscriptions via Laravel Cashier (Stripe), staff users + roles, and Sanctum programmatic API keys. Wire Reader subscriber gating where Laravel issues and the Reader verifies — the Reader stays read-only and has no admin/billing code. Follow `docs/backend-handoff.md` §1.

---

## 3. Definition of done (whole effort)

- One admin (Laravel Backoffice); the Reader has no `/admin`.
- One Postgres, two schemas (`public` = Curator pipeline, `backoffice` = Laravel); no
  SQLite; legacy `sources` and the duplicate `articles` gone; single `public.outlets`.
- Curator reads models/thresholds/keys from DB (env fallback) and writes `model_usage`.
- Admin can: CRUD outlets, edit Curator settings + keys (masked), see spend, moderate
  events/pages and re-run synthesis, manage customers + subscriptions + staff roles.
- `docs/STATUS.md` updated after each phase; ADRs added for any deviation from
  `backend-architecture.md`.
