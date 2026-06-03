# InkBytes — Overall Status

> *Status: v0 pipeline proven end-to-end · Owner: Julian · Last updated: 2026-06-02*

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
     **Next: Phase 2.2** (model_usage + cost dashboard) and/or 2.3 (moderation).
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
