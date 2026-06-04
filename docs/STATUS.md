# InkBytes — Overall Status

> *Status: v0 pipeline proven end-to-end · Owner: Julian · Last updated: 2026-06-04*

## TL;DR

The full v0 pipeline runs end-to-end on real infrastructure:
**Messor (harvest) → RabbitMQ → Curator (enrich + cluster + synthesize) → Reader (pages)**.
A 3-outlet harvest (CNN + NPR + AP) produced **29 multi-source event pages** that
render in the Reader. The monorepo is consolidated and pushed to GitHub.

## Live system state (local dev, 2026-06-02)

| Service | Port | State |
|---|---|---|
| Curator API + consumer | 8060 | up |
| Reader (Next.js) | 3000 | up |
| Postgres + pgvector | 5432 | up |
| RabbitMQ | 5672 | up |
| MinIO (S3 stand-in) | 9000 | up |

**Curator DB:** 309 articles · 309 enriched · 220 events · **29 pages published**
(7 three-source, 22 two-source). All real Haiku 4.5 + OpenAI `text-embedding-3-small`.

Bring the stack up: `bash orchestrator/scripts/up.sh`. Curator consumes from RabbitMQ;
Messor publishes per-article `event.article.scraped` events on the `messor` exchange.

## Repository

- **Canonical remote:** https://github.com/pragmatalabs/InkBytes (branch `master`, in sync).
- **Monorepo tracks:** `Messor/`, `Curator/`, `Reader/`, `orchestrator/`, `docs/`, root `CLAUDE.md`.
- `.gitignore` default-ignores the root and re-includes only the active stack; build/dep
  junk (`node_modules`, `.venv`, `.next`, `__pycache__`) and secrets (`.env*`,
  `*.local.yaml`, `.secrets.env`) are excluded.
- Tuned Curator runtime values are baked into `Curator/apps/curator/core/config.py`
  defaults, so a fresh clone works without the gitignored `env.local.yaml`.

## What was fixed (this session)

**Messor**
- Session summary no longer clobbers the staged articles file (writes `.session.json`).
- `LoggingService` forwards `%`-style args (was crashing the publish loop after 1 article).
- `docs/contracts.md` reconciled with the real `inkbytes.article.v1` event shape.

**Curator**
- `cluster.py` returns the authoritative distinct-outlet `source_count` (was suppressing
  synthesis for genuine 2-source events).
- Defaults promoted in `config.py`: `max_tokens_enrich 1500`, `max_tokens_synth 2500`,
  `similarity_threshold 0.62`, `entity_overlap_min 1`.
- Added `scripts/recluster.py` (re-clusters existing embeddings + synthesizes; no re-enrich).

## v0 Definition of Done (from docs/mvp-plan.md)

- [x] Curator runs end-to-end on real LLM
- [x] At least one outlet returned ≥ 5 articles via Messor (3 outlets, 319 articles)
- [x] First event pages in `pages` table (29 multi-source pages, hand-checkable)
- [x] Reader renders events at localhost:3000
- [ ] DO Droplet running docker-compose.prod.yaml
- [ ] 24h of green scheduled cycles + first paying user invited

## Open items / next steps

0. **Backend consolidation (in progress):** Laravel Backoffice is the single admin
   ([root ADR-0001](./adr/0001-consolidate-backend-into-laravel-backoffice.md)). The
   build handoff ([backend-handoff.md](./backend-handoff.md)) was **audited + patched
   for DB safety** ([review](./backend-handoff-review.md),
   [ADR-0003 schema isolation](./adr/0003-backoffice-schema-isolation.md)).
   - **Phase 1.1 DONE** (branch `backend/phase-1.1-laravel-postgres`): Laravel moved off
     SQLite onto the shared Postgres+pgvector, isolated in a `backoffice` schema
     (`search_path=backoffice,public`). 10 Laravel tables migrated into `backoffice`;
     Curator's `public` data untouched (articles=309, events=220, pages=29, outlets=31).
     Legacy `sources`/`articles` migrations deleted; `scrape_runs` + its `add_view_tracking`
     alter also deleted (FK-depended on the dropped `sources`); `scraping_jobs` kept.
     Breeze auth boots against Postgres.
   - **Phase 1.2 DONE** (merged): Outlets CRUD in the Backoffice bound to `public.outlets`
     (Curator owns the DDL; no Laravel migration). Dead Sources/Runs/Articles surface
     (models, services, controllers, pages, API routes, seeders, tests) retired; Dashboard
     rewritten on outlet metrics. Curator's startup outlet seed is now **seed-if-empty**
     (count guard) so admin edits survive restarts. **Reader `/admin` + its proxy deleted.**
     Frontend builds; 25 Laravel tests pass.
   - **Phase 2.1 DONE** (branch `backend/phase-2.1-curator-config`): DB-backed Curator
     config + key management ([ADR-0004](./adr/0004-curator-config-from-db-keys-via-env.md)).
     Two Backoffice-owned tables migrated into `backoffice`: `curator_settings`
     (LLM models/token caps/temperature + clustering thresholds, single live row,
     seeded from config.py defaults) and `api_keys` (provider/label/active +
     `encrypted`-cast `value`). Curator `core/config.py` overlays
     `backoffice.curator_settings` (schema-qualified) over env/YAML and re-reads it on
     a 30s poll, so an admin edit changes pipeline behaviour **without a redeploy**;
     env/YAML stays the fallback when the row/table is absent. **API keys stay env-only**
     — Curator never reads/decrypts `api_keys` (avoids Python↔Laravel AES crypto). New
     admin screens: **Curator Settings** (edit tunables) + **API Keys** (list/create/
     rotate/delete, masked to last-4, with a "test key" provider check). 32 Laravel
     tests pass (7 new); frontend builds; `public` counts unchanged (309/220/29/31).
   - **Phase 2.2 DONE** (branch `backend/phase-2.2-model-usage`): model usage +
     cost dashboard. New Backoffice-owned table `backoffice.model_usage` (Laravel
     migration owns the DDL): `call_label`, `model`, `input_tokens`, `output_tokens`,
     `cost_usd` (decimal), nullable `event_id` (Curator's text event id, no cross-schema
     FK), `created_at` (timestamptz); indexed on `(model)` and `(created_at)`. Curator's
     `CostMeter` gains an async **DB sink** (`set_sink`): every completed LLM call now
     persists one row via `DatabaseService.record_model_usage(...)` (schema-qualified
     INSERT) **alongside** the unchanged in-memory totals + COST log line. The write is
     fire-and-forget (`loop.create_task`) and **non-fatal** — any DB/logging failure is
     caught and logged, never breaking the pipeline. New read-only admin screen **Cost &
     Usage**: spend by model, by skill, by day, plus projected **per-1000-articles** and
     **per-page** (derived from live `public.articles`/`public.pages` counts). 34 Laravel
     tests pass (2 new); frontend builds; `public` counts unchanged (309/220/29/31);
     `model_usage` left empty (synthetic verification rows cleaned up).
   - **Phase 2.3 DONE** (branch `backend/phase-2.3-moderation`): events/pages
     moderation + re-run commands. New read-only Backoffice screen **Moderation**
     lists Curator's `public.events` + their `public.pages` (headline, source count
     via `evidence_rail`, freshness, published-at, cost) with **Publish / Unpublish /
     Drop** and **Re-synthesize / Re-cluster** actions. The Backoffice **never writes**
     events/pages (ADR-0003): each action publishes a JSON command over RabbitMQ and
     Curator applies the write. Command transport is the **RabbitMQ management HTTP API**
     via Guzzle (`CuratorCommandService`) — **no AMQP composer package** added (see
     lessons-learned). Commands ride a new durable topic exchange `curator.commands`
     (queue `curator.commands`) with routing keys `page.publish` / `page.unpublish` /
     `page.drop` / `event.resynthesize` / `event.recluster`; payload `{"id": "<target>"}`.
     Curator extends its aio-pika layer with a command consumer (`MessageService.consume_commands`
     + `Application._handle_command`), wired into `run_consumer` and a focused
     `main.py --consume-commands` harness (no FastAPI :8060 bind, so it coexists with a
     running `--api-only` Curator). Handlers: publish→`published_at=NOW()`+event
     `published`; unpublish→`published_at=NULL`+event `draft`; drop→`published_at=NULL`+
     event `dropped` (no hard delete — row retained, revivable); resynthesize/recluster
     re-run the existing skills. **Curator migration `003_pages_moderation.sql`** makes
     `public.pages.published_at` **nullable** (was `NOT NULL`) so unpublish/drop have a
     clean toggle; the moderation state of record stays `events.status`
     (`draft|published|dropped`, already in 001). 40 Laravel tests pass (6 new);
     frontend builds; verified end-to-end no-LLM (unpublish→publish toggled
     `public.pages.published_at`; `event.resynthesize` dispatched stub synthesis);
     `public` counts unchanged (events=220, pages=29).
   - **Phase 3 PAUSED** (business layer: customers/subscriptions/roles + Reader gating):
     blocked on Stripe test credentials + pricing/gating decisions (Owner). Scope when
     resumed: `composer require laravel/cashier`, `customers`/`subscriptions` in
     `backoffice`, staff roles, Sanctum tokens, Reader subscriber gating (Laravel issues,
     Reader verifies, Reader stays read-only).
   - **Backoffice UX hardening (Phase A) DONE:** drove the live app and fixed what made
     it *look* broken — seeded a dev admin (`admin@inkbytes.test`, login wall was just an
     un-run seeder); fixed MUI v7 `<Grid item>` → `size` truncation on Curator Settings +
     Cost & Usage; deepened the Control Center with **live pipeline metrics** (articles/
     enriched/events/pages/spend/last-harvest via cross-schema reads); rebranded
     Laravel→InkBytes (logo + "InkBytes Backoffice"). 40 tests pass; verified in-browser.
     Next: gap-analysis P0s — ~~B1 audit log~~ (DONE), ~~B2 RBAC~~ (DONE);
     P1s — ~~B3 outlet health~~ (DONE).
   - **B1 audit log DONE** (branch `backend/b1-audit-log`): records *who did what to
     which target, with before/after* for every state-changing admin action. New
     Backoffice-owned table **`backoffice.audit_logs`** (Laravel migration; columns
     `actor_id`/`actor_name`/`actor_email` snapshots, `action`, `target_type`,
     `target_id`, `before`/`after` jsonb, `ip`, `created_at` timestamptz; indexed on
     `action`, `(target_type,target_id)`, `created_at`). `App\Models\AuditLog::record()`
     is a **best-effort** static recorder (try/catch + `Log::warning` — an audit hiccup
     never 500s the underlying action) that snapshots the authed user + request IP.
     Wired into every mutation: Outlets (created/updated/deleted), API Keys
     (created/updated/deleted — **secret-free**: only provider/label/masked last-4/active,
     never raw or encrypted key), Curator Settings (updated, before/after diff), and
     Moderation commands (`page.published`/`unpublished`/`dropped`,
     `event.resynthesize`/`recluster`). New read-only **Audit Log** screen
     (`/audit-log`, nav entry) with newest-first table, expandable before/after JSON,
     server-side pagination (25/page), and filter by action and/or actor. **45 Laravel
     tests pass** (5 new, incl. one asserting key material is never persisted); frontend
     builds (manifest includes the page); verified the recorder + apikey/outlet wiring
     against Postgres via tinker; `public` counts unchanged (articles=309, events=220,
     pages=29, outlets=31).
   - **B2 RBAC DONE** (branch `backend/b2-rbac`): three roles on
     **`backoffice.users.role`** (string, default `viewer`; migration
     `2026_06_03_000005`, promotes the seed admin to `admin`). Gating is
     server-side via a custom **`EnsureUserHasRole`** middleware (route alias
     `role`) — **no spatie, no new packages** (ADR-0005). Route→role mapping in
     `routes/web.php`: read-only routes ungated (dashboard, outlets.index,
     model-usage, moderation.index, runtime, scraping status/stream);
     **`role:operator`** on outlets store/update/destroy + scraping.trigger +
     all moderation action POSTs; **`role:admin`** on api-keys.*, settings.*,
     audit-log, and the new users routes. Matrix: admin=everything,
     operator=outlets/scraping/moderation mutations (no keys/settings/users),
     viewer=read-only. The React layer reads `auth.user.role` (shared by
     `HandleInertiaRequests`) via a `useAuthRole()` hook to hide/disable gated
     controls + nav entries — **cosmetic only; middleware is the real gate**.
     New **admin-only Users screen** (`/users`, `UserController` index +
     updateRole) with a role selector and a **last-admin safeguard** (cannot
     demote the only admin → zero-admin lockout blocked); role changes audited
     as `user.role_changed` (B1). New registrations default to `viewer`. Profile
     page shows the current role chip. **63 Laravel tests pass** (18 new across
     `RoleAccessTest` + `UserManagementTest`); `npm run build` green; verified
     against Postgres: `users.role` present, seed admin=`admin`, role-change
     audit row written; `public` counts unchanged (articles=309, events=220,
     pages=29, outlets=31).
   - **B3 outlet health columns DONE** (branch `backend/b3-outlet-health`):
     the Outlets index now shows per-outlet **Articles**, **Events
     contributed**, **Last scraped** (relative time), and a **Health chip**.
     `OutletController@index` runs ONE grouped cross-schema query against
     Curator's `public.articles` (`GROUP BY outlet_id`, joined to
     `public.outlets.id` — the slug; ADR-0003 read-only, never writes
     `public.*`), wrapped in try/catch so the page still renders (stats null/0)
     if the table is absent (SQLite tests / un-migrated Curator). **No success
     rate is shown** — `public.articles` only holds successfully-scraped
     articles, so attempts/failures (a true rate) need Messor run history (B4);
     we surface volume + recency + events instead. Health derives from
     active-flag + recency: inactive→grey "Inactive", active+never-scraped→
     yellow "Never", <24h→green "Healthy", <7d→amber "Stale", else→red "Old".
     CRUD/validation and B1 audit / B2 RBAC (role-gated Edit/Delete) untouched.
     **64 Laravel tests pass** (1 new `OutletHealthTest` asserting the defensive
     empty-stats fallback; full enriched payload verified against Postgres via
     tinker: apnews art=158/evt=132/recent last_scraped, bbc 0/null);
     `npm run build` green; `public` counts unchanged (articles=309, events=220,
     pages=29, outlets=31). *SQLite caveat: the populated join is Postgres-only;
     the test exercises the fallback, the live payload is tinker-verified — same
     approach as B1/B2.*
   - **B6 unified health dashboard DONE** (branch `backend/b6-health-dashboard`):
     new read-only **System Health** screen (`/health`, `health.index`, nav
     entry; **all authenticated roles**, no role gate) answering "is the
     pipeline alive?" at a glance. `HealthController@index` builds a structured
     payload with **four independently defensive** components — every external
     call has a **~2s timeout + try/catch** so a down/slow service degrades to
     `down`/`unreachable` (never a 500, never a hang): **postgres** (cross-schema
     `public.*` counts + `MAX(scraped_at)`, ADR-0003 read-only), **curator** (GET
     :8060/status, articles/events/pages_published + latency), **messor**
     (reachability via GET :8050/api/scrapesessions?page=1&limit=1 — no /health
     exists — + latency), **rabbitmq** (mgmt /api/overview + /api/queues, per-queue
     depth for `curator.articles-scraped`/`articles-scraped`/`curator.commands` +
     latency). New config `services.curator.url` / `services.messor.url`
     (`CURATOR_URL`/`MESSOR_URL` in `.env.example`); RabbitMQ creds **reuse the
     existing `services.curator.rabbitmq.*`** (same as `CuratorCommandService`)
     and stay **server-side only** — the Inertia props carry just
     statuses/metrics/queue depths, never creds or the mgmt URL. React page
     (`Pages/Health/Index.jsx`): one status card per service (green up / red
     down / grey unknown) with its key metric + latency, plus a queue-depth
     table. **68 Laravel tests pass** (4 new `HealthDashboardTest` via
     `Http::fake()` — all-up, a Curator-down graceful-degradation case, a
     no-creds-in-props assertion, and an auth gate); `npm run build` green.
     Live payload verified via tinker (all four up: pg 309/309/220/29/29, curator
     309/220/29, messor up, rabbit queues 2024/1/0); degradation verified by
     pointing `CURATOR_URL` at a dead port → `unreachable` in 9ms, total request
     82ms, Messor still up; `public` counts unchanged (articles=309, events=220,
     pages=29, published=29).
   - **B5 cost dashboard upgrades DONE** (branch `backend/b5-cost-upgrades`): the
     read-only **Cost & Usage** screen gained four computable upgrades over
     `backoffice.model_usage`. (1) **Date-range filter** — `from`/`to` query
     params scope **every** aggregate (summary cards, by-model, by-skill, by-day,
     by-event); default is the **last 30 days**; per-1k-articles / per-page
     denominators still come from live `public.articles`/`public.pages`. (2)
     **CSV export** — `GET /model-usage/export` (`model-usage.export`, all
     authenticated roles, same as the page) streams the **filtered** rows via
     `streamDownload`+`chunk` (cols: created_at, call_label, model, input_tokens,
     output_tokens, cost_usd, event_id). (3) **Budget threshold + alert** — a new
     **nullable `monthly_budget_usd`** column on `backoffice.curator_settings`
     (admin-only edit via the existing B1-audited Settings form; **Curator does
     not read it** — Backoffice-only display knob, no ADR-0004 contract change);
     the page shows **month-to-date spend vs budget** with a progress bar and an
     **over-budget alert banner** when MTD > budget; widget **hidden when unset**.
     (4) **By-event drill-down** — synth rows (event_id NOT NULL) grouped by event
     with cost/token totals, joined **defensively** to `public.pages` for the
     headline (ADR-0003 read-only cross-schema; degrades to null headline);
     enrich rows (event_id NULL) aggregated separately as "Unattributed".
     **DEFERRED — by-outlet & per-API-key cost:** `model_usage` carries neither
     `outlet_id` nor `api_key_id`, so those breakdowns can't be computed without
     Curator first writing those columns (noted in code + gap-analysis B5).
     **72 Laravel tests pass** (6 new in `ModelUsageTest`: date-range scoping,
     CSV export, budget over/under/unset, budget-change audit); `npm run build`
     green. Live payload **tinker-verified on Postgres**: wide range $0.006951/1
     call, narrow (Jan) $0/0; by-event headline "Six killed in Iowa family
     shooting…" joined for `01KT5E6AYJW4014BEYM5V0Z6B7`; budget $0.001 → over,
     $100 → within, null → hidden. **`public` counts unchanged** (articles=309,
     events=220, pages=29, published=29); **`model_usage` row count unchanged (1)**
     — read-only.
   - **B9 settings safety DONE** (branch `backend/b9-settings-safety`): guards a
     bad Curator config from reaching the live pipeline (Curator polls
     `backoffice.curator_settings`, ADR-0004). (1) **Model allowlist** — new
     `config/curator.php` holds `allowed_models.{enrich,synthesize}`
     (`claude-haiku-4-5`, `claude-sonnet-4-5`, `claude-opus-4-5`);
     `CuratorSettingController@update` validates both model fields with
     `Rule::in()` (422 + clear allowlist message), and the Settings page now
     renders them as **MUI Select dropdowns** (no free-text typos). (2)
     **Numeric ranges** tightened (temperature 0–1, similarity 0–1, tokens
     1–32000, entity_overlap ≥0, min_sources ≥1, recent_window ≥1, budget
     nullable ≥0). (3) **Reset to defaults** — `POST /settings/reset`
     (admin-only, B2) restores `config('curator.defaults')` behind a confirm
     dialog, audited as `settings.reset` (B1). **Single source of truth:** the
     create-table migration now seeds from the same `config('curator.defaults')`,
     so seed + reset can't drift. **82 Laravel tests pass** (5 new in
     `CuratorSettingsTest`: allowlist reject/accept, temperature>1 reject,
     min_sources<1 reject, reset-restores-defaults+audited); `npm run build`
     green. Live row tinker-verified at canonical defaults; **`public` counts
     unchanged** (articles=309, events=220, pages=29, outlets=31).
   - **B10 outlet import/export DONE** (branch `backend/b10-outlet-import-export`):
     bridges the Messor seed file and the live catalogue. (1) **Export** —
     `GET /outlets/export` (any authenticated role) streams `application/json` of
     all `public.outlets` rows in the **exact `outlets.json` seed shape** (`id,
     name, display_name, url, region, language, vertical, active, priority` — no
     timestamps), pretty-printed + unescaped slashes, so the file **round-trips**
     and can replace the seed. We never write the seed file on disk — pure
     download. (2) **Import** — two steps, operator+ (B2): `POST
     /outlets/import/preview` parses the upload, rejects a malformed/non-list file
     wholesale, validates each entry against the **same enums/ranges as the CRUD**,
     and returns a **create/update/error diff WITHOUT writing**; `POST
     /outlets/import/apply` re-validates, aborts if any row is invalid, then
     **upserts by `id`** (known columns only, `updated_at` stamped, **no DDL**) in a
     transaction. Audited (B1): per-row `outlet.created`/`outlet.updated` + an
     `outlet.imported` summary. A shared `buildPreview()` keeps preview and apply in
     lockstep. (3) **UI** — Outlets page gains **Export JSON** (download) + **Import
     JSON** (file picker → preview-diff dialog → **Apply**, blocked while any row is
     invalid), import gated to operator+. **89 Laravel tests pass** (7 new in
     `OutletImportExportTest`; the Curator-owned `public.outlets` is reproduced via
     `ATTACH DATABASE … AS public`, no shipped DDL); `npm run build` green. Verified:
     export = 31 rows, field set matches `outlets.json`; live apply exercised on
     Postgres (create→32 + update) then **restored to 31**. **`public` counts
     unchanged** (articles=309, events=220, pages=29, outlets=31).
   - **B4 scraping run history DONE** (branch `backend/b4-run-history`): read-only
     **Run History** screen (`/run-history`, `run-history.index`, **all
     authenticated roles** — no role gate; observability only). Live-reads Messor
     `GET /api/scrapesessions?page=1&limit=50` **defensively** (reuses B6's pattern:
     `Http::timeout(3)` + try/catch reading `config('services.messor.url')`); if
     Messor is unreachable or non-2xx the page renders an **empty state** + an
     "unreachable" notice and returns fast (no 500, no hang — verified 13ms against
     a dead port). The controller maps each session to the fields Messor actually
     exposes — articles total/successful/failed, **run-level success rate** (the
     rate B3 deferred at the outlet level), outlets (count + names + per-outlet
     article counts), duration — **no fabricated dedup ratio**. The page shows
     **summary cards** (runs in window, total articles, avg success rate, last run),
     a **recent-runs table** (relative + full-on-hover timestamps), and a
     **dependency-free inline-SVG** chart (articles-per-run bars coloured by
     success rate + a success-rate trend polyline) — **no charting library added**;
     handles 1 row and many. **77 Laravel tests pass** (5 new in `RunHistoryTest`:
     `Http::fake` happy-path mapping + summary rollup, single-session render,
     unreachable degradation, non-200 degradation, auth required); `npm run build`
     green. **Live-verified against Messor :8050** (1 session, 1801 articles, 100%
     success, 24 outlets). **`public` counts unchanged** (309/220/29/29); **no new
     tables** (`backoffice` table list unchanged — live-read, no `scrape_runs`
     table). **DEFERRED — dedup ratio** (not in Messor's payload; future
     Messor-side enhancement) and **durable long-range history** (this is
     recent/staging-bounded live data; persistence is future).
   - ~~**Data note:** 2.3 re-synthesize overwrote page `01KT5E6AYJW4014BEYM5V0Z6B7` with
     stub text.~~ **Resolved** — regenerated with real content (`is_stub=false`). *Lesson
     retained: verify re-synthesize against a throwaway event, never live data.*
1. **Deploy (D6):** nothing on DigitalOcean yet. Needs `.do/app.yaml` / prod compose.
2. **Pages from a real scheduled cycle:** the 29 pages came from manual 3-outlet runs +
   a one-off recluster. Wire `--schedule` for continuous operation.
3. **Outlet coverage:** EN (CNN/NPR/AP) plus LATAM/ES (Infobae, Milenio, El Universal MX,
   Listín Diario, El Espectador, clarín, animalpolítico…) now exercised via the Messor
   admin client. Broaden + schedule for full coverage.
4. ~~**Messor REPL:** `--scrape` spins on EOF with no TTY.~~ **Resolved** — non-TTY exits
   cleanly (one-shot) or holds the API up (serve mode). See Messor ADR-0007 follow-up.

## Known risks / cleanup debt

- **`Trashx/`** (local only, untracked): holds 34 moved legacy items. Several are repos
  with **unpushed/uncommitted work** (Entopics, Unitas, hermes, mefisto, walkway,
  DocTrainer, Inkbytes-PowerDesktop). Review repo-by-repo before deleting.
- ~~**Nested GitLab/local repos** inside the tree.~~ **Resolved** — severed; GitHub is the
  single source of truth. See [root ADR-0002](./adr/0002-github-monorepo-single-source.md).
- ~~**Shared-kernel symlinks** (`apps/scraper/inkbytes` → `src/inkbytes`, in-package links).~~
  **Resolved** — kernel is now self-contained real source. See
  [Messor ADR-0007](../Messor/docs/adr/0007-self-contained-shared-kernel.md).
- **Curator config**: `env.local.yaml` (gitignored) carries the live keys/values; the
  committed `config.py` defaults match it, but the secrets live only on this machine.
- **`Trashx/` legacy repos** (see above) still need repo-by-repo review before deletion.
- **Deploy image**: build `--platform linux/amd64` for the DO droplet (local builds are
  arm64); supply service hostnames via env-var overlay (committed `env.yaml` uses localhost).
