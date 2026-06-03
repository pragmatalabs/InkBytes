# InkBytes — Backend & Admin Architecture

> *Status: v1 (proposed) · Owner: Julián de la Rosa · Last updated: 2026-06-02*
>
> The target shape for the InkBytes backend: one Laravel **Backoffice** as the
> single admin/control plane, Messor and Curator as managed workers, and one
> shared Postgres as the system of record. Decision recorded in
> [`docs/adr/0001-consolidate-backend-into-laravel-backoffice.md`](./adr/0001-consolidate-backend-into-laravel-backoffice.md).
> Engineering truth: [`STATUS.md`](./STATUS.md). Product framing: [`product.md`](./product.md).

## 1. Why this exists

As of 2026-06-02 the v0 pipeline works, but the control surfaces are fragmenting:

- The **Laravel platform** (`Messor/apps/platform`) is scoped only to Messor and
  is read-only (index pages, no real CRUD). It runs on **SQLite**.
- **Curator** holds the real system of record (Postgres + pgvector) but takes its
  API keys and model choice **from env only**, and tracks token usage **in memory**
  (`cost_meter.py`) — so spend is not queryable.
- A **second admin** is forming in the Reader (`Reader/apps/web/app/admin/`),
  duplicating the Laravel Sources view.

Left alone this produces two admins, two databases, and duplicated `outlets`/
`sources` and `articles`. This document consolidates them.

## 2. Principles

- **One admin.** All CRUD lives in one place. The Reader stays public and read-only.
- **One source of truth.** A single Postgres. No SQLite, no cross-DB sync.
- **Workers, not mini-backends.** Messor and Curator do work; they read their
  config from the DB the Backoffice owns and write their outputs/usage back.
- **Reuse what's installed.** Laravel Breeze (auth), Sanctum (API tokens), Cashier
  (Stripe) — don't hand-roll auth or billing.
- **Lean before featureful.** Remove redundancy first; add business features last.

## 3. Target topology

```text
FRONTENDS
  Public Reader (Next.js, read-only)        InkBytes Backoffice (Laravel + Inertia/React/MUI)
        │ reads published-pages API                 │ owns all admin/CRUD
        ▼                                           ▼
SHARED DATA ── PostgreSQL + pgvector (single system of record) ── DO Spaces (S3, artifacts)
        ▲                                           ▲
        │ writes pages/usage                        │ reads config / writes results
WORKERS
  Messor (Python harvester) ──RabbitMQ──▶ Curator (Python LLM pipeline)
```

Component responsibilities:

| Component | Owns | Reads | Writes |
|---|---|---|---|
| **Backoffice (Laravel)** | All admin/CRUD, auth, billing | Everything in Postgres | outlets, settings, api_keys, customers, subscriptions, users |
| **Reader (Next.js)** | Public reading experience | published pages (API) | — |
| **Messor (Python)** | Harvesting | `outlets` | `articles` (raw), RabbitMQ events, Spaces |
| **Curator (Python)** | Enrich/cluster/synthesize | `outlets`, `curator_settings`, `api_keys` | `articles` (enriched), `events`, `pages`, `entities`, `model_usage` |

## 4. Unified data model (one Postgres)

**Keep (Curator already owns, pipeline writes):** `events`, `articles`, `entities`,
`pages`. These stay as-is.

**Consolidate:** collapse Laravel `sources` (SQLite) and Curator `outlets`
(Postgres) into the **single `outlets` table** in Postgres. The Backoffice does the
CRUD; Messor and Curator read it. The Reader `/admin` outlets view is deleted.

**Add (Backoffice-owned, new tables):**

| Table | Purpose | Notes |
|---|---|---|
| `curator_settings` | Model selection, token caps, temperature, clustering thresholds | One active row (or key/value); Curator reads at boot + on refresh signal |
| `api_keys` | Anthropic / OpenAI / Spaces credentials | Encrypted at rest (Laravel `encrypted` cast); masked in UI; env is bootstrap fallback |
| `model_usage` | Per-call tokens + cost, by label/model/day/event | Curator writes; powers the usage dashboard. Replaces in-memory `cost_meter` |
| `customers` | Reader subscribers | Distinct from staff `users` |
| `subscriptions` | Plan, status, Stripe IDs | Managed by Laravel Cashier |
| `users` + roles | Staff/admin accounts | Breeze + a roles column or a light policy layer |
| Sanctum tokens | Programmatic API keys for B2B/admin scripts | Already available via Sanctum |

**Delete:** Laravel `sources` table + the duplicate `articles` table in SQLite;
the whole SQLite connection; the Reader `/admin` page.

## 5. Admin units (CRUD surfaces in the Backoffice)

Operations
: **Outlets** (full CRUD, region/language/vertical/priority/active) · **Runs &
scheduling** (trigger, view history, set cadence) · **Events / Pages** (review,
publish / unpublish / re-synthesize, drop low-quality clusters).

Curator (treated as backend)
: **Settings** (enrich/synthesize model, token caps, temperature, clustering
thresholds) · **API keys** (Anthropic / OpenAI / Spaces — encrypted, masked,
testable) · **Model usage & cost** (read dashboard: spend by model, by day, per
1000 articles, per page).

Business
: **Customers** · **Subscriptions / billing** (Stripe via Cashier) · **Staff users
& roles** · **Programmatic API keys** (Sanctum).

## 6. How Curator becomes "part of the backend"

Curator stays a separate Python process (it needs pgvector, embeddings, the LLM
client) but stops being self-configured:

1. **Config from DB.** `core/config.py` keeps env as the bootstrap fallback but, in
   normal operation, loads `curator_settings` and `api_keys` from Postgres. A
   lightweight refresh (poll, or a `curator.config.changed` RabbitMQ signal from
   the Backoffice) lets the admin change a model without a redeploy.
2. **Usage to DB.** `cost_meter.py` gains a sink that inserts each completed call
   into `model_usage` (it already computes tokens + cost). The Backoffice reads it.
3. **Control via the bus.** "Re-synthesize this event" / "re-run clustering" become
   Backoffice actions that publish a command Curator consumes — no new HTTP surface
   on Curator beyond the existing read endpoints.

Net: the admin sees and controls Curator (keys, models, spend, re-runs) without
Curator owning any of that logic.

## 7. Redundancies removed by this change

1. Two admins → one (delete Reader `/admin`).
2. `sources` (SQLite) + `outlets` (Postgres) → one `outlets`.
3. `articles` stored twice → one (Curator's Postgres copy).
4. Two databases → one Postgres (drop SQLite).
5. In-memory cost tracking → persisted `model_usage`.
6. (Already done) root `database/`/`common/`/`models/` folded into the shared
   kernel; `src/` remains a legacy duplicate to retire.

## 8. Phased build path

Each phase ships independently and leaves the system working. Tracked in the build
task list.

**Phase 1 — Unify the database (remove redundancy, no new features)**
Point Laravel at Postgres; migrate `sources` into the shared `outlets` table; give
the Backoffice full CRUD on outlets; delete SQLite, the duplicate `articles`/
`sources` tables, and the Reader `/admin` page.

**Phase 2 — Curator as a managed worker**
Add `curator_settings`, `api_keys`, `model_usage`; Curator reads config / writes
usage; Backoffice ships Settings, API-keys, and Usage-&-cost screens, plus
Events/Pages moderation and re-run commands over RabbitMQ.

**Phase 3 — Business layer**
Customers, Cashier subscriptions, staff roles, and Reader subscriber gating
(Laravel issues, Reader verifies).

## 9. Risks & notes

- **Secrets in DB.** `api_keys` must be encrypted at rest and never logged or
  returned unmasked. Env stays the fallback so a fresh boot works before the table
  is seeded.
- **Shared DB coupling.** Laravel and Curator share Postgres; agree table ownership
  (this doc) so migrations don't collide. Curator owns pipeline tables; Laravel owns
  operational/business tables.
- **Reader isolation.** The Reader must only ever read published pages; never give
  it admin endpoints or write access.

## Related

- [`docs/adr/0001-consolidate-backend-into-laravel-backoffice.md`](./adr/0001-consolidate-backend-into-laravel-backoffice.md)
- [`Curator/docs/architecture.md`](../Curator/docs/architecture.md)
- [`Messor/docs/adr/0005-messor-curator-responsibility-split.md`](../Messor/docs/adr/0005-messor-curator-responsibility-split.md)
- [`STATUS.md`](./STATUS.md) · [`mvp-plan.md`](./mvp-plan.md)
