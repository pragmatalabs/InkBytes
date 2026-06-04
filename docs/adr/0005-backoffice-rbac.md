# ADR-0005 (system) — Role-based access control in the Backoffice (admin / operator / viewer), built on Laravel's own middleware

* **Status**: Accepted
* **Date**: 2026-06-03
* **Deciders**: Julián de la Rosa
* **Scope**: Laravel Backoffice (`Messor/apps/platform`)
* **Relates to**: [ADR-0001](./0001-consolidate-backend-into-laravel-backoffice.md) (single admin plane), [ADR-0003](./0003-backoffice-schema-isolation.md) (`backoffice` schema owns `users`), B1 audit log, gap-analysis item **B2**

## Context

Until now the Backoffice had a **single role**: anyone who could log in could
rotate provider API keys, change the live Curator model/threshold settings, and
drop or unpublish live event pages. The gap analysis ([messor-admin-gap-analysis.md](../messor-admin-gap-analysis.md))
flagged this (Gap 3 / item **B2**) as a top-priority risk — these actions touch
real spend and live reader-facing content. B1 (audit log) made actions
*accountable*; B2 makes the dangerous ones *gated*.

## Decision

Introduce **three roles** on `backoffice.users.role` (string, default
`viewer`), enforced server-side by a small custom middleware, with cosmetic
hide/disable in the React layer.

### Role matrix

| Capability | admin | operator | viewer |
|---|:---:|:---:|:---:|
| Dashboard, Outlets list, Cost & Usage, Moderation view, Runtime, Scraping status/stream | ✅ | ✅ | ✅ |
| Outlets create/update/delete | ✅ | ✅ | ❌ |
| Scraping trigger | ✅ | ✅ | ❌ |
| Moderation actions (publish/unpublish/drop/resynthesize/recluster) | ✅ | ✅ | ❌ |
| Curator Settings (view + write) | ✅ | ❌ | ❌ |
| API Keys (view + store/rotate/delete/test) | ✅ | ❌ | ❌ |
| Audit Log (view) | ✅ | ❌ | ❌ |
| User / role management | ✅ | ❌ | ❌ |

Tiers are **inclusive**: admin satisfies the operator gate. New self-service
Breeze registrations default to `viewer`; the dev seed admin
(`admin@inkbytes.test`) is `admin`.

### Mechanism

* **`User` model** gains `role` (fillable, not hidden so it rides along on the
  Inertia-shared `auth.user`) plus helpers `isAdmin()`, `isOperator()`
  (admin OR operator), `isViewer()`, `hasRole($tier)`, and a `ROLES` constant.
* **`EnsureUserHasRole` middleware**, registered as the route alias `role`.
  Usage: `->middleware('role:admin')` or `->middleware('role:operator')`.
  Returns **403** on insufficient role. This is the **source of truth**.
* **`routes/web.php`** groups routes by tier: read-only routes carry no role
  middleware; mutation routes sit under `role:operator`; the sensitive sections
  (keys, settings, audit log, users) sit under `role:admin`.
* **React layer** reads `auth.user.role` via a `useAuthRole()` hook and
  hides/disables gated controls and nav entries. This is **cosmetic only** —
  the middleware is the real gate.
* **User management** (`UserController`, admin-only): lists users and changes
  roles. A **last-admin safeguard** blocks demoting the only remaining admin
  (never leave the Backoffice with zero admins). Role changes are **audited**
  via the B1 recorder as `user.role_changed`.

## Why built-in middleware, not spatie/laravel-permission

* **No new dependency.** v0 needs exactly three flat roles gating a fixed set of
  routes — not arbitrary permissions, role hierarchies, teams, or a
  database-driven permission registry. A 20-line middleware + one string column
  covers it; spatie adds 4 tables, caching concerns, and a migration surface for
  a problem we don't have.
* **Schema isolation stays trivial (ADR-0003).** One nullable column on the
  existing `backoffice.users` table — no extra tables to keep inside the
  `backoffice` schema and away from Curator's `public.*`.
* **Transparency.** The gate is one readable class; the route→role mapping is
  visible in `routes/web.php`. No magic.
* **Reversible.** If real granular permissions are ever needed (Phase 3 business
  layer), swapping the alias for spatie is mechanical — the route groups already
  express intent.

### Role as an app-level string, not a DB check constraint

`role` is validated at the application layer (the middleware + `UserController`
`Rule::in(User::ROLES)`) rather than a Postgres `CHECK` constraint, so the
SQLite test DB and Postgres prod DB behave identically and the allowed set lives
in one place (the `User::ROLES` constant).

## Consequences

* **Positive**: any logged-in user can no longer rotate keys, change live
  Curator config, or drop pages. Accountability (B1) + gating (B2) together.
  Zero new packages; one column; tests run unchanged on SQLite.
* **Negative / trade-offs**: roles are flat (no per-resource permissions); the
  `viewer` default means an admin must promote new registrants before they can
  act (intentional — least privilege). The last-admin guard is enforced in the
  controller, not the DB, so a future direct SQL `UPDATE` could still zero out
  admins (acceptable: DB access is already privileged).
* **Testing note**: the `role` middleware runs before the controller, so a
  forbidden role gets its 403 before any Postgres-backed controller logic — which
  is why the gating feature tests assert cleanly on the SQLite test DB even for
  routes that read Curator's `public.*` tables.

## Alternatives considered

* **spatie/laravel-permission** — rejected: over-built for three flat roles; adds
  tables + dependency (see above).
* **Laravel Gates/Policies only** — Gates suit per-model authorization, but the
  gating here is route-shaped (whole sections), so route-alias middleware is the
  cleaner fit. The `User` role helpers leave the door open to add Policies later.
* **Per-permission flags** (booleans per capability) — more granular than needed;
  three named tiers are easier to reason about and audit.
