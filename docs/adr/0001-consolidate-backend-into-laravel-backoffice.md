# ADR-0001 (system) — Consolidate the backend into a single Laravel Backoffice

* **Status**: Accepted
* **Date**: 2026-06-02
* **Deciders**: Julián de la Rosa
* **Scope**: System-wide (Messor platform + Curator + Reader)
* **Relates to**: [`docs/backend-architecture.md`](../backend-architecture.md), [`Curator/docs/adr/0001`](../../Curator/docs/adr/0001-curator-collapses-pipeline.md), [`Messor/docs/adr/0005`](../../Messor/docs/adr/0005-messor-curator-responsibility-split.md)

## Context

After v0 proved end-to-end, three independent control surfaces started to form:

- The **Laravel platform** (`Messor/apps/platform`, Laravel 13 + Inertia/React/MUI,
  Breeze + Sanctum) — scoped only to Messor, read-only, on **SQLite**.
- **Curator** — holds the real system of record (Postgres + pgvector) but is
  configured by **env vars only** and tracks LLM usage **in memory**.
- A nascent **`/admin` in the Reader** (Next.js) duplicating the Laravel outlets view.

This was heading toward two admins, two databases, and duplicated `outlets`/
`sources` and `articles`. The product also needs admin units that exist nowhere yet:
API-key management, model-usage/cost, customers, and subscriptions.

## Decision

1. **One backend/admin.** Promote the Laravel platform into the **InkBytes
   Backoffice** — the single admin/control plane for Messor, Curator, customers, and
   billing. Delete the Reader `/admin`; the Reader stays public and read-only.
2. **One database.** Point Laravel at the existing **Postgres + pgvector** and drop
   SQLite. Collapse `sources`/`outlets` into one `outlets` table and remove the
   duplicate `articles` copy.
3. **Curator becomes a managed worker.** Its API keys, model selection, and
   clustering thresholds move into DB tables (`curator_settings`, `api_keys`) the
   Backoffice edits; Curator reads them at boot / on a refresh signal. Token usage is
   persisted to `model_usage` (replacing the in-memory cost meter). Re-run/
   re-synthesize are Backoffice commands published over RabbitMQ.
4. **Reuse the stack.** Auth via Breeze, programmatic tokens via Sanctum, billing via
   **Laravel Cashier** (Stripe). No hand-rolled auth or billing.

Table ownership: Curator owns the pipeline tables it writes (`events`, `articles`,
`entities`, `pages`); the Backoffice owns operational/business tables (`outlets`,
`curator_settings`, `api_keys`, `model_usage`, `customers`, `subscriptions`,
`users`).

## Alternatives considered

- **Build the admin in Curator (FastAPI).** Rejected: would re-implement auth and
  billing in Python and discard the working Laravel/Breeze/Sanctum/Cashier stack.
- **Build the admin in the Reader (Next.js).** Rejected: single JS stack is
  appealing, but duplicates auth/CRUD/ORM and couples the public site to admin code.
- **Keep databases separate, sync over HTTP.** Rejected: adds sync logic and a second
  source of truth for the same `outlets`/`articles` with no isolation benefit at v0
  scale (one Droplet, one Postgres).

## Consequences

**Positive**: one admin, one database, no duplicated tables; API keys and model spend
become first-class and queryable; business features (customers, subscriptions) land
on a stack already built for them; the Reader stays a thin, safe public surface.

**Negative / watch**: Laravel and Curator now share a Postgres, so table-ownership
discipline matters (this ADR sets it). Secrets live in `api_keys` and must be
encrypted at rest, masked in UI, and never logged; env remains the bootstrap
fallback.

**Migration**: phased — (1) unify the DB and outlets, (2) Curator-as-worker +
Curator admin screens, (3) business layer. See `docs/backend-architecture.md` §8.
