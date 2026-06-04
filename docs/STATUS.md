# InkBytes — Overall Status

> *Status: v0 pipeline proven end-to-end · Owner: Julian · Last updated: 2026-06-03*

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
     Next: gap-analysis P0s — ~~B1 audit log~~ (DONE), **B2 RBAC**.
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
