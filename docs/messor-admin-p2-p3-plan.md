# Messor Admin — P2/P3 Implementation Plan (B7–B13)

> *Status: plan · Owner: Julián de la Rosa · Last updated: 2026-06-03*
>
> Forward plan for the remaining backlog in [messor-admin-gap-analysis.md](./messor-admin-gap-analysis.md).
> P0 (B1 audit, B2 RBAC) and P1 (B3 outlet health, B4 run history, B5 cost upgrades,
> B6 system health) are **done + shipped**. This covers **P2 (B7–B11)** and **P3
> (B12–B13)**. Grounded in the live code; no work started.

## Findings that reshape the backlog (read first)
1. **B8 is mostly blocked by [ADR-0004](./adr/0004-curator-config-from-db-keys-via-env.md).**
   `backoffice.api_keys` = `{id, provider, label, value, active, created_at, updated_at}` —
   no `last_used`, and **Curator reads provider keys from env, never from the DB**. So
   *last-used* and *spend-per-key* are **not trackable** unless ADR-0004 is reversed. Only
   *one-active-per-provider* and *rotation history* are feasible today. → **Gating decision (a).**
2. **B9's "change history" already exists.** `CuratorSettingController` already writes a
   `settings.updated` audit row (B1). B9 collapses to: model-allowlist validation +
   reset-to-defaults.
3. **B7: Audit Log already paginates.** The un-paginated, growth-prone lists are
   **Moderation (220 events), Model-Usage, Outlets** — the real B7 targets.

---

## B7 — Pagination / search / sort / bulk (P2 · M) ✅ DONE
**Diff:** AuditLog ✅ server-paginated; all other lists rendered every row client-side.

| Page | Need | Priority |
|---|---|---|
| Moderation (220 events) | server pagination + headline search + status filter | high |
| Model-Usage rows / by-event | pagination as `model_usage` grows | med |
| Outlets (31 today) | search + sort + **bulk activate/deactivate/delete** | med |
| Users / API Keys (small) | low | low |

**Decision (resolved):** shared mechanics (not a monolithic `<PaginatedTable>`) — a Laravel
trait + small composable React pieces, so each page keeps its bespoke row rendering.
**Shipped (branch `backend/b7-pagination-search-bulk`):**
- **Server:** `App\Http\Controllers\Concerns\PaginatesQueries` — `resolvePerPage` (allowlist
  `[10,25,50,100]`), `resolveSort` (column allowlist + asc/desc), `applySearch` (case-insensitive
  LIKE over caller-declared columns), `applySort`, `listState`. Every knob allowlisted so an
  arbitrary `?sort=`/`?per_page=` can't reach raw SQL. Mirrors AuditLog (paginate + withQueryString).
- **React:** `Hooks/useListQuery.js` (search/toggleSort/changePage/changePerPage → `router.get`,
  query-string preserved), `Components/SortableTableCell.jsx`, `Components/ListSearchField.jsx`
  (Enter-to-submit), `Components/ListPagination.jsx` (Laravel paginator → MUI `TablePagination`).
- **Moderation** (`/moderation`): server-paginates `public.events`; **headline search** via
  `whereHas('page')` against `public.pages` (defensive — no hard JOIN that 500s without the schema);
  **status filter** (draft/published/dropped); sortable status/sources/freshness. Per-event
  publish/unpublish/drop/resynthesize/recluster actions unchanged + operator-gated. Empty-paginator
  fallback when `public.*` is unreachable.
- **Model-Usage** (`/model-usage`): the **by-event** table is server-paginated under its own
  `event_page` param (headline join resolves the current page only). B5 date-range + budget widget
  intact; **CSV export still streams the full filtered range** (chunked, not one page).
- **Outlets** (`/outlets`): **search** (name/slug/url) + **sortable columns**; **bulk
  activate/deactivate/delete** of selected rows via `POST /outlets/bulk` (operator+, B2). Audited
  (B1): per-row `outlet.updated`/`outlet.deleted` + a summary `outlet.bulk_activated`/
  `outlet.bulk_deactivated`/`outlet.bulk_deleted` carrying the affected ids + count. No-op toggles
  skipped (no audit noise). B3 health columns + B10 import/export untouched.
- **Tests** (`PaginationSearchBulkTest`, 9): moderation pagination metadata + headline search +
  status filter; outlets search + sort-desc; bulk deactivate flips `active` + audits; bulk
  activate(no-op skip)/delete; bulk operator-gated; unknown-action rejected. Cross-schema reads
  reproduced via `ATTACH DATABASE … AS public` (DatabaseMigrations, no shipped DDL). ModelUsage
  test updated for the paginated `byEvent.events.data` shape.
- **Verification:** live Postgres — Moderation total=220/per_page=25, `q` narrows, published=29/
  draft=191; Model-Usage byEvent paginated + CSV rows == table rows (MATCH); Outlets search `cnn`→1,
  sort display_name desc → Wired/WSJ/Guardian; **bulk deactivate exercised live (28→26) then
  restored to 28, probe audit rows removed**. `public` counts unchanged (309/220/29/31). Full suite
  **98 green**; `npm run build` green.

## B8 — API-key depth (P2 · reduced per decision (a)) ✅ DONE
| Sub-feature | Feasible now? | Shipped |
|---|---|---|
| One-active-per-provider | ✅ constraint + UI | ✅ |
| Rotation history | ⚠️ already audited (B1); a dedicated view is easy | ✅ |
| Last-used timestamp | ❌ Curator uses env keys (ADR-0004) | N/A by design |
| Spend-per-key | ❌ `model_usage` has no `api_key_id` | N/A by design |

**Shipped (branch `backend/b8-apikey-depth`):**
- **One-active-per-provider.** `ApiKeyController@store`/`@update` wrap a transaction
  that **deactivates the previously-active key of the same provider, then activates the
  new one** (`deactivateActiveFor()` excludes the key being activated so it never
  self-trips). DB safety net: migration `…000001_add_one_active_per_provider_index…`
  adds a **partial unique index `(provider) WHERE active`** (driver-aware: Postgres +
  SQLite) on `backoffice.api_keys` so the invariant holds even under a race. The
  auto-deactivation is audited as **`apikey.deactivated`** (B1), secret-free
  (provider/label/masked last-4/active only).
- **Rotation/change history view.** `GET /api-keys/history` (admin-only) renders
  `ApiKeys/History.jsx` — a **server-paginated, filtered view of
  `audit_logs WHERE target_type='apikey'`** (reuses B7's `PaginatesQueries` +
  `useListQuery`/`SortableTableCell`/`ListPagination`). Sortable by when/action,
  action filter, expandable before/after. No key material — the B1 snapshots are
  already secret-free.
- **UI honesty.** Index + History pages carry a "Not tracked — Curator uses env keys
  (ADR-0004); last-used/spend N/A by design" note instead of empty columns.
- **Tests** (10 in `ApiKeysTest`, +6 for B8): create→active→supersede deactivates prior +
  audits `apikey.deactivated`; update→active supersedes; two providers each keep one
  active; partial unique index blocks a second active row per provider; history view
  paginated + secret-free (no `sk-`/`eyJ`); history admin-only. Full suite **104 green**;
  `npm run build` green.
- **Verification (live Postgres):** index present (`\d backoffice.api_keys` →
  `api_keys_one_active_per_provider UNIQUE … WHERE active`); A→B supersede gave anthropic
  active=1 with an `apikey.deactivated` masked-only audit row; anthropic+openai both
  active=1 (total 2); history rows contained no `sk-`/`eyJ`. **Probe keys + audit rows
  removed**, `backoffice.api_keys` back to 0; `public` counts unchanged (309/220/29/31).

## B9 — Settings safety (P2 · S) ✅ DONE
**Diff:** change-history ✅ (audit). Remaining: (a) validate model names against an **allowlist** so a typo can't reach the pipeline; (b) **reset-to-defaults** (defaults from Curator `config.py`).
**Decision (resolved):** allowlist + canonical defaults live in a **Laravel config array** (`config/curator.php`), not fetched from Curator.
**Shipped (branch `backend/b9-settings-safety`):**
- `config/curator.php` → `allowed_models.{enrich,synthesize}` (`claude-haiku-4-5`, `claude-sonnet-4-5`, `claude-opus-4-5`) + `defaults` (mirror config.py).
- `CuratorSettingController@update`: `Rule::in($allowlist)` on both model fields with clear 422 messages; numeric ranges tightened (temperature 0–1, similarity 0–1, tokens 1–32000, entity_overlap ≥0, min_sources ≥1, recent_window ≥1, budget nullable ≥0).
- Settings page: model fields are now **MUI Select dropdowns** sourced from the allowlist (no free-text typos); **Reset to defaults** button with a confirm dialog.
- `POST /settings/reset` (admin-only) restores `config('curator.defaults')`; audited as `settings.reset` (B1).
- **Single source of truth:** the create-table migration seeds from `config('curator.defaults')`, so seed + reset can't drift.
- Tests: allowlist rejection, allowlisted accept, temperature>1 reject, min_sources<1 reject, reset-restores-defaults+audited. Full suite 82 green; `npm run build` green; `public` counts unchanged (309/220/29/31).

## B10 — Outlet import/export (P2 · S) ✅ DONE
**Diff:** outlets in `public.outlets` (Curator owns DDL; Backoffice CRUDs data). Seed file: `Messor/apps/scraper/data/outlets/outlets.json`.
**Decision (resolved):** export = **download JSON** (chosen — no coupling to Messor's FS). Import = upload → validate → **diff preview → upsert by `id`** (operator+, audited).
**Shipped (branch `backend/b10-outlet-import-export`):**
- `GET /outlets/export` (any authenticated role) streams `application/json` of all `public.outlets` rows in the exact seed shape — `id, name, display_name, url, region, language, vertical, active, priority` (no timestamps), pretty-printed + unescaped slashes — so the file **round-trips** and can replace `outlets.json`.
- `POST /outlets/import/preview` (operator+) parses the upload, rejects a non-list/malformed file wholesale, validates each entry against the **same enums/ranges as the CRUD** (id slug regex, region/vertical `Rule::in`, priority 1–3, boolean active, url), and flashes a **diff preview** (create/update/error counts + rows) **without writing**.
- `POST /outlets/import/apply` (operator+) re-validates server-side, aborts if any row is invalid, then **upserts by `id`** in a transaction — known columns only, `updated_at` stamped, **no DDL**. Audited (B1): per-row `outlet.created`/`outlet.updated` + an `outlet.imported` summary (`{created,updated}`).
- `buildPreview()` is shared by preview + apply so the diff the admin sees can't diverge from what's applied.
- UI: Outlets page gains **Export JSON** (download, all roles) + **Import JSON** (file picker → preview-diff dialog with create/update/invalid tables → **Apply**, disabled while any row is invalid), import controls gated to operator+.
- Tests (7, `OutletImportExportTest`): export shape/round-trip + all-roles access, preview create=1/update=1/error=1 without writing, malformed-file rejection, apply upsert + B1 audit rows, apply-aborts-on-invalid, viewer-forbidden. The Curator-owned `public.outlets` is reproduced in tests via an `ATTACH DATABASE … AS public` (DatabaseMigrations, no shipped DDL) so the upsert runs against the real Eloquent model.
- **Verification:** export = 31 rows, field set matches `outlets.json` (MATCH: YES). Live apply exercised against Postgres (create→32 + update npr) then **restored to 31** with npr reverted. Full suite **89 green**; `npm run build` green.

## B11 — Alerting (P2 · M — builds on B3/B4/B5)
**Diff:** signals exist (B3 health, B4 success rate, B5 budget, B6 queue) but nothing pushes. No `Notifications` dir; `MAIL_*` configured.
**Open decisions:** (1) **channel** — in-app bell / email / both; (2) **evaluation** — Laravel **scheduler** (cron) vs event-driven. *Default: scheduled evaluator + `alerts` table + in-app bell; email later.*
**Rules:** failed/low-success scrape (B4), stale outlet (B3 Old/Never), cost over budget (B5 MTD>budget), pipeline stalled (B6 queue backlog / no harvest in X h). Alerts acknowledgeable + audited.
**Steps:** `alerts` table → scheduled evaluator job → in-app bell + alerts page → (opt) mail → tests. **Deploy note:** needs the Laravel scheduler running (`schedule:work` / cron).

## B12 — React client (:5174) fate (P3 · M/L — see decision (b))
Reconfirmed: the Backoffice already has **more** than the :5174 client (Scraping trigger + SSE logs + Postgres run history + full Outlets CRUD). **The one real gap is the per-session scrape-results browser** (per-outlet article counts / dedup / timestamps); the rest is decommission.
**Gating decision (b):** results-browser data source — A / B / C (below).
**Steps:** pick A/B/C → build results browser → verify the trigger path end-to-end → delete `Messor/client/` + its launch configs + the now-dead `:8050 /api/scrape*` endpoints (verify sole consumer) → ADR extending ADR-0001. Net-new consolidation, independent of Phase 3.

## B13 — UX polish (P3 · M)
**Diff:** a toast/flash pattern exists in ~6 files but isn't standardized; empty/loading/error states inconsistent; mobile unverified.
**Steps:** one shared snackbar provider → consistent empty/loading/error components across lists → mobile pass (drawer, tables→cards). Do last; low risk.

---

## The two gating decisions (everything else has a clear default)

> **DECIDED 2026-06-03:** (a) **KEEP** env keys (ADR-0004 reaffirmed) — B8 ships
> one-active-per-provider + rotation history only. (b) **B12 = Option B**
> (Messor → Postgres `scrape_sessions`) — see [ADR-0006](./adr/0006-scrape-results-via-messor-postgres.md).
> Both items are now unblocked for implementation.

### Decision (a) — ADR-0004: keep Curator on env keys, or reverse it? → **KEEP**

**What ADR-0004 says today:** Curator loads the real provider keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) from **environment variables**. The Backoffice `api_keys` table is **management-only** — it stores keys encrypted (Laravel `encrypted` cast), masks them in the UI, and can "test" them, but **Curator never reads or decrypts those DB rows**. It was decided this way to avoid cross-language crypto (Python re-implementing Laravel's AES-256-CBC envelope keyed on `APP_KEY`), which is fragile to maintain and bought nothing for v0.

**Why this blocks half of B8:** because Curator never *uses* the DB key, there is:
- no "the key was used at HH:MM" event to stamp → **no `last_used`**, and
- nothing tying an LLM call to a key (`model_usage` has no `api_key_id`) → **no spend-per-key**.

| Option | Unlocks | Cost / risk |
|---|---|---|
| **KEEP env keys** (recommended for now) | one-active-per-provider + rotation history (audit). | B8 stays reduced; keys live in two places — env (what Curator actually uses) + the DB table (admin record-keeping). Mild inconsistency, zero new risk. Keys are deployed via env/secrets, not the UI. |
| **REVERSE → Curator reads DB keys** | last-used timestamps, spend-per-key attribution, in-UI rotation that takes effect with no redeploy, one source of truth for secrets. | Cross-language decryption to build + maintain (decrypt Laravel's cast in Python, **or** re-encrypt with a scheme both speak, e.g. Fernet); a new ADR superseding 0004; **new security surface** (Curator now pulls secrets from the DB); a migration of the env keys into the table. Real effort (M–L) + a security review. |

**Recommendation:** **KEEP** for now and ship the feasible B8 subset (one-active-per-provider + rotation-history view), marking last-used/spend "N/A by design." Reverse **only** when "which key cost how much / is this key still in use" becomes a real operational need (multiple keys, per-key billing). It's reversible later without rework — flipping it is additive.

### Decision (b) — B12: data source for the scrape-results browser → **Option B**

The only functional gap when folding the :5174 client into the Backoffice is the **per-session scrape-results browser** (each harvest session → per-outlet article counts, dedup stats, timestamps). Today that data lives in Messor's file-based staging (`data/scrapes/*.db.json`), surfaced only by the old client. Where should the Backoffice read it from?

| Option | How | Pros | Cons |
|---|---|---|---|
| **A · Proxy Messor `:8050`** | Backoffice calls `GET /api/scrapesessions` (B4 already does this for run history) | fastest to build; reuses the B4 defensive-HTTP pattern; zero Messor change | couples the UI to the **flaky `:8050`** process (keeps dying) and to file-based staging (ephemeral, retention-bounded); no durable history |
| **B · Messor → Postgres** (recommended) | Messor persists a `scrape_sessions` table in `public`; Backoffice reads it | decouples from `:8050`; durable history; matches **ADR-0003** "one DB, owned tables" | a real **Messor change** — it's file-based today, so Messor must learn to write sessions to Postgres (the biggest of the three) |
| **C · Backoffice worker records** | extend the Backoffice `RunScrapingWorker` to persist per-outlet results itself | no `:8050`/`:5174` dependency at all | **duplicates Messor's staging/dedup logic** in Laravel; a second place that "understands" scrape results |

**Recommendation:** **B** for the durable, architecture-aligned answer (but it's the largest, needing Messor work) — **or A** as a fast interim that reuses B4's proxy if you want the browser now and accept the `:8050` coupling. **C** only if you specifically want zero Messor dependency. Then build the browser, verify the trigger path, decommission `Messor/client/`, and record an ADR extending ADR-0001 ("one admin").

---

## Recommended sequence
| Order | Item | Effort | Decision needed first? |
|---|---|---|---|
| 1 | **B9** settings safety ✅ DONE | S | ✅ allowlist = Laravel config |
| 2 | **B10** outlet import/export ✅ DONE | S | ✅ export = download |
| 3 | **B7** pagination/search/bulk ✅ DONE | M | ✅ shared trait + composable React pieces |
| 4 | **B8** one-active + rotation view ✅ DONE | S | ✅ (a) decided: KEEP — ship reduced |
| 5 | **B11** alerting | M | channel + scheduler |
| 6 | **B12** client consolidation | M/L | ✅ (b) decided: Option B (ADR-0006) |
| 7 | **B13** UX polish | M | — |

**Cheapest first value:** **B9 → B10** (both S, no blocking decision). Both gating
decisions are now made (KEEP env keys; B12 = Messor→Postgres), so the whole P2/P3
sequence is unblocked.
