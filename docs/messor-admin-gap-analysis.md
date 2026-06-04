# Messor Admin (Laravel Backoffice) — Gap Analysis & Backlog

> *Status: analysis · Owner: Julián de la Rosa · Last updated: 2026-06-03*
>
> Scope: the **Laravel Backoffice** (`Messor/apps/platform`) — the single admin/control
> plane per [ADR-0001](./adr/0001-consolidate-backend-into-laravel-backoffice.md), built
> in handoff Phases 1.2–2.3. The legacy **Messor React client** (`Messor/client`, :5174)
> is a separate scraping console that now overlaps this admin (see Gap 4).
> Engineering truth: [STATUS.md](./STATUS.md). Target design: [backend-architecture.md](./backend-architecture.md).

## 1. What's been built

| Area | Routes / depth | State |
|---|---|---|
| Auth | Breeze: login, register, password reset, email verify, profile | ✅ working; **RBAC live** (admin/operator/viewer — B2, ADR-0005) |
| Outlets CRUD | index / store / update / destroy + region/lang/vertical filters | ✅ bound to `public.outlets` (Curator owns DDL) |
| API Keys | index / store / update / destroy / **test** | ✅ Laravel `encrypted` cast, masked, provider test |
| Curator Settings | edit / update (models, token caps, temperature, clustering thresholds) | ✅ live DB overlay, 30s refresh (ADR-0004) |
| Cost & Usage | index dashboard: by model / skill / day, per-1k-articles, per-page | ✅ read-only |
| Moderation | events+pages list; publish/unpublish/drop pages; resynthesize/recluster events | ✅ command-driven over RabbitMQ |
| Scraping | trigger / status / **stream** (live logs) | ✅ ops console (→ Messor FastAPI :8050) |
| Runtime | index / snapshot | ✅ system view |
| Dashboard | outlet-derived metrics | ✅ basic |
| Tests | 8 feature suites (63 tests) | ✅ |

DB: Backoffice tables live in the `backoffice` schema; Curator pipeline in `public`
(ADR-0003). `migrate:fresh` is scoped to `backoffice` and cannot touch Curator data.

## 2. Gaps by category

### Gap 1 — CRUD depth (tables work; UX/scale features thin)
- No **pagination** anywhere (Outlets renders all rows client-side — fine at 31, breaks at scale).
- No server-side **search**, **sort persistence**, or **bulk actions** (activate/deactivate/delete many).
- **Outlets**: no **health column** (last-scraped, article count, success rate — data exists in Curator's `public` tables), no **bulk import/export** (sync from `outlets.json`), no soft-delete/restore.
- **API Keys**: no **rotation history**, no **last-used** timestamp, no "one active key per provider" rule, no link to the spend each key drove.
- **Settings**: single global row — no **change history**, no validation against a known-model allowlist, no "reset to defaults," no diff-on-save.

### Gap 2 — Usage / observability (dashboard exists; analytics don't)
- ~~**Cost dashboard**: no **date-range filter**, no **CSV export**, no **budget thresholds + alerts**, no **cost-by-outlet / by-event** drill-down, no spend-vs-budget projection, no per-API-key attribution.~~ ✅ **DONE (B5)** — date-range filter (scopes all aggregates), CSV export, monthly budget + MTD-vs-budget + over-budget alert, **by-event** drill-down. **Deferred: by-outlet & per-API-key** — `model_usage` lacks `outlet_id`/`api_key_id`; would need Curator to capture those columns first.
- ~~**No unified health dashboard** (Messor :8050 / Curator :8060 / RabbitMQ queue depth / Postgres / last cycle time) — scattered across Runtime + the React client today.~~ ✅ **DONE (B6)** — read-only **System Health** screen (`/health`, all roles); each component (Postgres/Curator/Messor/RabbitMQ) probed defensively (~2s timeout + try/catch), queue depths surfaced, RabbitMQ creds kept server-side.
- ~~**No scraping run history / time-series** — the legacy Runs/Articles views were deleted in Phase 1.2 and nothing replaced articles-per-outlet-over-time, success rate, or dedup ratio.~~ ✅ **DONE (B4)** — read-only **Run History** screen (`/run-history`, all roles) live-reads Messor `GET /api/scrapesessions` defensively (~3s timeout + try/catch; unreachable → empty state, no hang). Recent-runs table (articles total/successful/failed, **run-level success rate**, outlets, duration) + summary cards + a dependency-free inline-**SVG** bars/sparkline (articles per run, colour = success rate, success-rate trend line). **Deferred: dedup ratio** (Messor doesn't expose it in this payload — future Messor-side enhancement) and **durable long-range history** (this is recent/staging-bounded live data; persistence is future).
- **No event/page analytics** (publish rate, sources-per-event distribution, freshness/staleness).

### Gap 3 — Admin-platform fundamentals (missing entirely)
- ~~**RBAC / roles** — single role; no admin vs operator vs viewer. Anyone who logs in can rotate keys, change Curator models, and drop live pages.~~ ✅ **DONE (B2)** — admin/operator/viewer enforced by the `role` middleware; see [ADR-0005](./adr/0005-backoffice-rbac.md).
- **Audit log** — no record of *who* published/dropped a page, changed a setting, or rotated a key. For an admin touching cost + live content, this is the highest-risk gap.
- **Alerting / notifications** — failed scrapes, stale outlets, pipeline stalls, cost-over-budget surface nowhere.
- **Programmatic API (Sanctum tokens)** — deferred to Phase 3.
- **Business layer** (customers / subscriptions / billing) — Phase 3, paused on Stripe keys.

### Gap 4 — Consolidation debt (ADR-0001 not fully realized)
- The **Messor React client (:5174)** still exists and duplicates scraping ops (WebSocket to Messor FastAPI :8050; the Backoffice `ScrapingJobController` also triggers/streams scrapes). ADR-0001 mandates **one admin** — the client should be folded into the Backoffice or retired. Two scraping consoles exist today.

### Gap 5 — UX / quality
- Inconsistent empty/loading/error states; no toast standard across all pages; mobile responsiveness unverified; real-time only on the scrape stream (other screens poll).

## 3. Prioritized backlog

Effort: S ≈ <½ day · M ≈ ~1 day · L ≈ multi-day. Priority P0 (do first) → P3.

| # | Pri | Item | Gap | Effort | Why / payoff |
|---|----|------|-----|--------|--------------|
| B1 | ✅ **DONE** | **Audit log** — record actor + action + target + before/after for every mutation (moderation, settings, key rotation, outlet CRUD) | 3 | M | Accountability for cost- and content-affecting actions; foundation for everything else |
| B2 | ✅ **DONE** | **RBAC** — roles (admin / operator / viewer) gating dangerous routes (keys, settings, moderation, scrape trigger). Custom `role` middleware (no spatie); last-admin guard; role changes audited. See [ADR-0005](./adr/0005-backoffice-rbac.md) | 3 | M | Stops any logged-in user from rotating keys / dropping pages |
| B3 | ✅ **DONE** | **Outlet health columns** — last-scraped, article count, events contributed + health chip (read from Curator `public.articles`, ADR-0003). *No success rate*: `public.articles` only holds successful scrapes; attempts/failures need Messor run history (B4) | 1,2 | M | Restores visibility deleted in 1.2; makes Outlets actionable |
| B4 | ✅ **DONE** | **Scraping run history / time-series** — read-only `/run-history` (all roles) live-reads Messor `/api/scrapesessions` (~3s timeout + try/catch; unreachable → empty state). Recent-runs table (articles total/successful/failed, **run-level success rate**, outlets, duration), summary cards, dependency-free inline-**SVG** bars + success-rate trend (no chart lib). Gives the **run-level success rate** B3 deferred at the outlet level. **Dedup ratio DEFERRED** (not in Messor's payload — future Messor-side) + **durable long-range history DEFERRED** (this is recent/staging-bounded live data; persistence is future). | 2 | L | Replaces the deleted Runs analytics; core ops insight |
| B5 | ✅ **DONE** | **Cost dashboard upgrades** — date-range filter (scopes all aggregates, default 30d), CSV export of filtered rows (`/model-usage/export`, streamed), monthly budget + MTD-vs-budget progress + over-budget alert (nullable `curator_settings.monthly_budget_usd`, admin-only, B1-audited), by-event drill-down (synth rows grouped by `event_id`, defensive `public.pages` headline join; enrich/NULL aggregated separately). **By-outlet & per-API-key DEFERRED**: `model_usage` carries neither `outlet_id` nor `api_key_id` — needs Curator to write those columns first. | 2 | M | Turns usage from descriptive to actionable; ties to MVP cost target |
| B6 | ✅ **DONE** | **Unified health dashboard** — Messor/Curator/RabbitMQ/Postgres + queue depth + last harvest. Read-only `/health` (all roles); each component defensive (~2s timeout + try/catch); RabbitMQ creds server-side only | 2 | M | One place to see "is the pipeline alive" |
| B7 | ✅ **DONE** | **CRUD scale features** — shared server trait (`PaginatesQueries`: page/per_page/q/sort/dir, allowlisted) + shared React pieces (`useListQuery`, `SortableTableCell`, `ListSearchField`, `ListPagination`). Applied: **Moderation** server-paginates `public.events` with headline search (`whereHas` on `public.pages`) + status filter (draft/published/dropped); **Model-Usage** by-event table server-paginated (`event_page`, CSV export still spans the full range); **Outlets** search (name/slug/url) + sortable columns + **bulk activate/deactivate/delete** (operator+, B1-audited `outlet.bulk_*` summary + per-row rows). | 1 | M | Needed before outlet/key/usage volume grows |
| B8 | ✅ **DONE** | **API Keys depth (reduced per [ADR-0004](./adr/0004-curator-config-from-db-keys-via-env.md))** — **one-active-per-provider** (app deactivates-then-activates the prior active key of the same provider in a transaction; **partial unique index `(provider) WHERE active`** as the DB safety net) + **rotation/change history view** (`/api-keys/history`, server-paginated filtered view of `audit_logs WHERE target_type='apikey'`, admin-only, secret-free). Auto-deactivation audited as `apikey.deactivated`. **last-used + spend-per-key = N/A by design** (Curator uses env keys, never reads DB keys — ADR-0004). | 1,2 | S | Operational hygiene for secrets |
| B9 | ✅ **DONE** | **Settings safety** — change history (B1 audit), model-name allowlist validation + Select dropdowns, numeric range checks, reset-to-defaults (audited). Allowlist + defaults centralized in `config/curator.php`; the create-table migration seeds from the same config | 1 | S | Prevents bad config reaching the live pipeline |
| B10 | ✅ **DONE** | **Outlet import/export** — `GET /outlets/export` streams all `public.outlets` rows as JSON in the exact `outlets.json` seed shape (round-trips, no timestamps; any authenticated role). `POST /outlets/import/preview` (operator+) parses + validates an uploaded file and returns a create/update/error diff **without writing**; `POST /outlets/import/apply` upserts-by-id the known columns only (sets `updated_at`, never DDL), B1-audited (`outlet.created`/`outlet.updated` per row + `outlet.imported` summary). UI: Export/Import buttons + preview-diff dialog gated to operator+. | 1 | S | Bridges the seed file and the live catalogue |
| B11 | ✅ **DONE** | **Alerting** — scheduled evaluator `alerts:evaluate` (every 5 min, `routes/console.php`) probes the B3/B4/B5/B6 signals and **upserts open alerts by `dedup_key`** into `backoffice.alerts` (deduped, no duplicate open rows). Four rules from `config/curator.php`: **over_budget** (MTD `model_usage` > `monthly_budget_usd`, flagship/deterministic), **stale_outlet** (active outlet not scraped in `stale_outlet_hours`, one per outlet), **scrape_low_success** (latest Messor session `success_rate` < `low_success_rate`, defensive HTTP — Messor-unreachable is NOT an alert), **pipeline_stalled** (no harvest in `pipeline_stalled_hours` OR RabbitMQ depth > `queue_backlog`). Each rule independently try/caught. **In-app only** (header bell badge via `HandleInertiaRequests` → `/alerts` server-paginated page; **Acknowledge** operator+, B1-audited `alert.acknowledged`); email/Notification deferred (single `raise()` funnel ready). **DEPLOY: needs the scheduler** (`php artisan schedule:work` / cron `schedule:run`). | 2,3 | M | Push problems instead of waiting to be asked |
| B12 | ✅ **DONE** | **React client (:5174) retired** — folded scraping ops into the Backoffice and decommissioned the legacy client. B12.1 (Messor emits `scrape.session.completed` → Curator upserts `public.scrape_sessions`), B12.2 (Backoffice read-only Scrape Results browser), B12.3 (**deleted `Messor/client/` + its launch configs + the dead `:8050 /api/scrape*` endpoints**; kept `/api/scrapesessions` + `/api/outlets` — the Backoffice's only consumers). See [ADR-0006](./adr/0006-scrape-results-via-messor-postgres.md) + [ADR-0001](./adr/0001-consolidate-backend-into-laravel-backoffice.md) | 4 | M/L | Realizes ADR-0001's "one admin"; removes duplication |
| B13 | ✅ **DONE** | **UX consistency** — shared toast provider (`ToastProvider` + `useToast`, one MUI Snackbar mounted in `AppLayout`, auto-surfaces Laravel `flash`; the 6 local-Snackbar pages migrated off their own state) + shared `<EmptyState>`/`<LoadingState>`/`<ErrorState>` (`Components/ListStates.jsx`) applied across all list pages so empty/in-flight/source-unreachable look uniform + mobile pass (drawer already collapses to a hamburger; wide tables scroll via MUI `TableContainer` `overflow-x:auto`; dialogs `fullWidth`/`maxWidth`). Presentation-only; suite unchanged at 126. **Completes the P0–P3 backlog.** | 5 | M | Polish |
| B14 | — | **Phase 3 (business layer)** — customers/subscriptions/Cashier/Sanctum/Reader gating | 3 | L | Tracked separately in the handoff; **paused on Stripe keys** |

## 4. Recommended sequencing
**B1 + B2 first** (audit + RBAC) — they protect every other action and are prerequisites for safely exposing the rest. Then the observability cluster **~~B3~~ → ~~B6~~ → ~~B5~~ → ~~B4~~** (cheap-to-rich: ~~outlet health~~, then ~~unified health~~, then ~~cost upgrades~~, then ~~run history~~). **~~B7~~–~~B11~~** as the catalogue/usage grows. **~~B12~~** (client consolidation) and **~~B13~~** (polish) when the feature set stabilizes. **The P0–P3 backlog (B1–B13) is now complete.** **B14** resumes when Stripe credentials + pricing decisions land.
