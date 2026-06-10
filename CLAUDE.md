# InkBytes — Repo Briefing (Claude Code handoff)

> *If you're a fresh Claude Code session, read this top-to-bottom before doing anything. ~3 min.*
> *Last updated: 2026-06-07*

## Single source of truth (read this first)

InkBytes docs split by layer. Don't duplicate across the boundary:

- **Engineering + current state → this repo's `docs/`.** Live status is
  [`docs/STATUS.md`](./docs/STATUS.md) (authoritative, dated). The week plan is
  [`docs/mvp-plan.md`](./docs/mvp-plan.md). Product/business framing is
  [`docs/product.md`](./docs/product.md).
- **Product / business / strategy → Notion hub**
  ([InkBytes](https://www.notion.so/373eca56ed94818da548f66ca288593a)). The Notion
  architecture/status sections *mirror* this repo — when they disagree, the repo wins.

If you only update one status, update `docs/STATUS.md`, then reconcile this file.

## What this repo is

InkBytes is a paid, ad-free news reader: one elegant page per *event*, synthesized from multiple sources. The reader pays to skip the noise.

Long-term pipeline: **Messor (harvester) → Entopics (NER+topics) → Synochi (synthesis) → Unitas (clustering+QA) → Reader**.

**v0 collapses Entopics+Synochi+Unitas into a single LLM-powered service called `Curator`.** As of 2026-06-07 the full v0 loop is **live in production on DigitalOcean** (`inkbytes.org`): 413 published pages, 22 active outlets, continuous 4×/day harvest cycle. Remaining: 24h green soak + first paying user (D7).

## Monorepo map

```
InkBytes/                              ← repo root
├── docs/                              ← system-wide docs
│   ├── README.md
│   └── mvp-plan.md                    ← THE plan for this week, read this first
│
├── orchestrator/                      ← parent-level dev/prod compose + scripts
│   ├── docker-compose.dev.yaml        ← Postgres + RabbitMQ + MinIO
│   └── scripts/up.sh, down.sh
│
├── Messor/                            ← STAGE 1, status: harvester live (publishes to RabbitMQ)
│   ├── apps/scraper/                  ← Python harvester (FastAPI, newspaper3k)
│   ├── packages/inkbytes/             ← shared kernel (pydantic v1)
│   ├── docs/                          ← incl. contracts.md, ADRs
│   └── CLAUDE.md                      ← Messor-specific briefing
│
├── Curator/                           ← STAGES 2+3+4 collapsed, status: end-to-end proven (29 pages)
│   ├── apps/curator/                  ← Python LLM service (pydantic v2)
│   ├── docs/                          ← incl. architecture.md, ADR-0001
│   └── CLAUDE.md                      ← Curator-specific briefing ← read this if working here
│
├── Reader/                            ← v0 frontend, status: Next.js scaffolded, runs at :3000
│   └── apps/web/                      ← Next.js public reader (reads Curator pages)
│
├── Entopics/  Synochi/  Unitas/       ← legacy folders, PARKED for v0
└── (other folders are legacy / pre-MVP — ignore unless asked)
```

## Locked decisions (updated 2026-06-08)

| Decision | Choice |
|---|---|
| LLM (enrich + synthesize) | **Anthropic Claude Haiku 4.5** |
| Embeddings | **Local Ollama `bge-m3` (1024-dim, multilingual)** — Curator ADR-0003; OpenAI `text-embedding-3-small` is the fallback provider |
| Local model runtime | **Ollama** — deployed service (dev `full` profile + prod compose); serves bge-m3 over an OpenAI-compatible `/v1` endpoint |
| Outlet vertical | LATAM bilingual (DR/MX/CO/AR/PE/CL/EC/PR/VE) + Europe (ES/FR/DE) + global EN business/tech |
| Outlet regions | Single source of truth: `Messor/apps/platform/config/regions.php`. Rule: `global` OR `{macro}-{cc}` (`{macro}` ∈ `latam`/`europe`/…, `{cc}` = ISO 3166-1 alpha-2 lowercase). Extend by adding the code under its macro in that config — the validator allowlist + Backoffice dropdown derive from it. Do NOT hardcode region lists in controllers (2026-06-09). |
| Deploy target | Single DigitalOcean Droplet |
| Database | Postgres + pgvector |
| Event bus | RabbitMQ |
| Object store (prod) | DigitalOcean Spaces (S3) |
| Object store (dev) | MinIO via docker-compose |
| Reader exchange name | renamed `hermes` → `messor.logs` (ADR-0004) |
| Pydantic | v1 in Messor (legacy), v2 in Curator (new) — boundary is RabbitMQ JSON |
| `pages.media_rail` content | **Videos only** (YouTube + future direct outlet video) — Bing image fetcher parked 2026-06-08 (ADR-0014). Images caused off-topic editorial/product photos to appear in the media drawer. |
| Corpus chat assistant | Curator `POST /ask` (`skills/assistant.py`, `prompts/assistant.md`) + Reader floating button/overlay (`components/chat-assistant.tsx` → `/api/ask` proxy). Grounded digests + RAG Q&A over **published events only**; cites `[n]` → `/event/{id}`; reuses the synthesis LLM engine. Curator ADR-0022. |
| Curator kill-switch | "Stop Curator" toggle on the Backoffice Settings page → `curator_settings.processing_enabled` (persistent). Curator polls it (~30s) and pauses the enrich→cluster→synthesize pipeline — articles requeue in RabbitMQ (no loss), API stays up. Curator ADR-0023. |

## State of the world right now

**Live status lives in [`docs/STATUS.md`](./docs/STATUS.md)** — keep the numbers there, not here. Summary as of 2026-06-02 evening:

✅ **Messor**: harvester live; publishes per-article `event.article.scraped` on the `messor` exchange. 3 outlets exercised (CNN/NPR/AP, ~319 articles). LATAM/ES outlets configured but not yet harvested. Not yet deployed.

✅ **Curator**: consumes from RabbitMQ; ENRICH → CLUSTER → SYNTHESIZE all live on real Haiku 4.5 + OpenAI embeddings + Postgres/pgvector. DB shows 309 enriched articles, 220 events, **29 published pages** (7 three-source, 22 two-source).

✅ **Reader (D4/D5)**: Next.js `apps/web` running in production at `inkbytes.org`. PWA manifest, bottom nav (4 tabs), share button on event pages. Lead images on cards and event hero.

✅ **Deploy (D6)**: DigitalOcean Droplet `67.205.136.61` running `docker-compose.prod.yml` at `inkbytes.org`. **Hostinger is retired — DO is the sole deploy target.**

🟡 **Soak (D7)**: 4×/day cycle is live; needs 24h of green cycles + first paying user invited.

## Where to point pwd depending on what you're doing

| Task | `cd` into | Then run `claude` |
|---|---|---|
| Anything spanning multiple services / system docs / orchestration | `/Volumes/Pragmata/Projects/InkBytes/` | reads this file (`CLAUDE.md`) |
| Curator dev | `/Volumes/Pragmata/Projects/InkBytes/Curator/apps/curator/` | reads `Curator/CLAUDE.md` |
| Messor dev | `/Volumes/Pragmata/Projects/InkBytes/Messor/apps/scraper/` | reads `Messor/CLAUDE.md` |
| Reader dev (D4, current focus) | `/Volumes/Pragmata/Projects/InkBytes/Reader/apps/web/` | reads `Reader/apps/web/CLAUDE.md` |

## Required env vars (host shell, never commit)

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
export OPENAI_API_KEY='sk-...'
# Postgres + RabbitMQ + MinIO defaults are already in env.local.yaml
```

If you're picking up cold and need to set these, add them to `~/.zshrc` (macOS default) or use 1Password CLI / Doppler.

## Bring everything up (one shot)

```bash
cd /Volumes/Pragmata/Projects/InkBytes
bash orchestrator/scripts/up.sh
# → Postgres :5432, RabbitMQ :5672 (UI :15672), MinIO :9000 (console :9001)
```

**Full local STACK as dev processes** (Messor harvest → RabbitMQ → Curator → Reader,
plus the Laravel Backoffice), running against `env.local.yaml` instead of Docker
(needs Ollama on :11434). All infra lives under one compose project, `inkbytes-dev`:

```bash
bash orchestrator/scripts/dev-pipeline.sh up      # infra + Curator(:8060) + Messor(--schedule) + Reader(:3000) + Backoffice(:8000)
bash orchestrator/scripts/dev-pipeline.sh status  # health + live pipeline counts
bash orchestrator/scripts/dev-pipeline.sh logs    # tail all app logs
bash orchestrator/scripts/dev-pipeline.sh down    # stop apps (infra stays)
```
Gotchas the script handles: (1) pins each Python app to **arm64** — the `.venv`
pythons are universal but their native wheels (`pydantic_core`) are arm64-only, so a
Rosetta/background launch crashes on import; it re-execs under arm64. (2) the macOS
framework python lacks `aio_pika`/`pika`/`newspaper` — it uses each app's `.venv`.
Backoffice runs `php artisan serve` (:8000) + vite and applies pending migrations on up.

Tear down:

```bash
bash orchestrator/scripts/down.sh         # keep volumes
bash orchestrator/scripts/down.sh --nuke  # delete volumes too
```

## Read order if you have 10 minutes

1. [`docs/STATUS.md`](./docs/STATUS.md) — live end-to-end state, the current truth
2. [`docs/mvp-plan.md`](./docs/mvp-plan.md) — week-of plan / roadmap
3. [`docs/product.md`](./docs/product.md) — mission, audience, differentiation (business layer)
4. [`Curator/docs/architecture.md`](./Curator/docs/architecture.md) — what we built
5. [`Curator/docs/adr/0001-curator-collapses-pipeline.md`](./Curator/docs/adr/0001-curator-collapses-pipeline.md) — why one service instead of three
6. [`Messor/docs/contracts.md`](./Messor/docs/contracts.md) — the event Curator consumes
7. [`Messor/docs/adr/0005-messor-curator-responsibility-split.md`](./Messor/docs/adr/0005-messor-curator-responsibility-split.md) — the boundary

## Open immediate todos

(see [`docs/STATUS.md`](./docs/STATUS.md) §"Open items" for the live list)

1. **Soak (D7):** let 4 scheduled cycles complete; verify outlets at >80% parse success; invite first paying user.
2. **`inkbytes.news` domain:** add A records → `67.205.136.61`; update `READER_DOMAIN`/`ADMIN_DOMAIN` on DO server.
3. **PNG app icons:** generate `/public/icon-192.png` and `/public/icon-512.png` from `icon.svg` for Android PWA install banner.
4. **Outlet coverage:** harvest the remaining LATAM/ES outlets; RSS/Atom-first harvesting in roadmap.
5. **Cleanup debt:** retire the legacy Messor GitLab remote; review `Trashx/` repos before deleting.

## ⚠️ Dev workflow — mandatory for ALL agents

> Full reference: [`docs/dev-workflow.md`](./docs/dev-workflow.md)

### Rule 1 — Test locally BEFORE deploying

**Never push to `origin/master` or trigger a production deploy without first verifying the change works in local dev.** Julian called this out explicitly (2026-06-08).

| Service | How to run locally |
|---|---|
| Infrastructure | `bash orchestrator/scripts/up.sh` → Postgres :5432, RabbitMQ :5672, MinIO :9000 |
| Curator (API + worker) | `cd Curator/apps/curator && python main.py` |
| Messor | `cd Messor/apps/scraper && python main.py` |
| Reader (Next.js) | `cd Reader/apps/web && npm run dev` → localhost:3000 |

Required checks: **Python changes** → boot service + exercise code path. **Reader changes** → `npm run dev`, open localhost:3000, verify visually. **Config changes** → confirm container picks up value. **Only then:** commit → push → `bash infra/deploy.sh [--build]`.

### Rule 2 — Commit locally, wait for push/deploy instruction

**Commit locally. Do NOT push or deploy without explicit instruction from Julian.**

- Always finish with: "N commits ahead of origin, ready to push when you say so."
- `git push`, `make deploy-build-do`, and any SSH-side deploys require an explicit "push" or "deploy" from Julian in chat.
- **Deploy target:** DigitalOcean only — `67.205.136.61` / `inkbytes.org`. Hostinger is retired.

---

## Conventions to keep using

- **Prompts as `.md` files** in `Curator/apps/curator/prompts/` — diffable, reviewable. See `Curator/docs/prompts.md` for the versioning policy.
- **Pydantic v2 in Curator** (don't downgrade). Pydantic v1 in Messor (don't upgrade until INK-Sprint-2).
- **ADRs** for any non-trivial decision. Sequential numbering per service.
- **Status banner** at the top of every doc: `> *Status: vN · Owner: ... · Last updated: YYYY-MM-DD*`.
- **`__SET_VIA_ENV__`** placeholders in committed YAML; real secrets come from env vars.
- **Never paste API keys in chat.** Set via shell. See `Messor/docs/security.md`.

## Anti-patterns to avoid

- Re-adding `topics_extracted` / `clusters_path` / `openai:` config to Messor — that's Curator's territory (ADR-0005).
- Calling `newspaper3k.Article.nlp()` in Messor — heuristic NLP belongs to Curator (ADR-0005).
- Mixing pydantic v1 imports into Curator code, or v2 imports into Messor code.
- Using a multi-agent framework (LangGraph / CrewAI / AutoGen) for Curator's three skills. ADR-0001 §"Alternatives considered" rejected it explicitly.
- Adding new schemas to the `inkbytes` shared package without a version bump.
- Writing prompts as inline Python strings instead of `.md` files in `prompts/`.
- **`export const revalidate = N` on Reader pages that call internal Docker services** (`inkbytes-curator-api` etc.). ISR pre-renders during `docker build` when the internal hostname doesn't exist → bakes the error state permanently. Use `export const dynamic = "force-dynamic"` instead (ADR-R-0005).
- **Accessing asyncpg JSONB columns without `_decode_json_col()`**. asyncpg returns plain `JSONB` columns as Python strings without explicit codec registration. Every JSONB column in the `/events/{id}` response must pass through `_decode_json_col()`. In the Reader, guard defensively: `Array.isArray(v) ? v : JSON.parse(v)` (ADR-R-0004).
- **`IllustrateSkill` without a concurrency gate**. Each run opens a Chromium instance (~200 MB). During batch synthesis N events fire N concurrent tasks → OOM. Always wrap the call in `_illustrate_sem` (`Semaphore(1)`) (ADR-0011).
- **Chromium in Docker without `seccomp:unconfined`**. Docker's default seccomp profile blocks the `clone()` flags Chromium needs → `SIGTRAP` crash on DO even with `--no-sandbox`. `inkbytes-curator-worker` in `infra/docker-compose.do.yml` must carry `shm_size: '256m'` and `security_opt: [seccomp:unconfined]` (ADR-0011).
- **Scrapling `StealthyFetcher`/`DynamicFetcher` in Docker containers**. Both wrappers inject `channel='chromium'` into Playwright's browser launch options. On Docker/Linux, `channel='chromium'` triggers a channel-based binary lookup that SIGTRAP-crashes even with `seccomp:unconfined`. Use `patchright.async_api.async_playwright` / `playwright.async_api.async_playwright` directly with no `channel` argument (ADR-0011).
- **Stateful service directories without a Docker volume**. If a service writes files that drive application behaviour (dedup caches, staging files, etc.) and those files have no named volume, every container restart silently wipes them. Messor's `data/scrapes/` had no volume for months — every deploy re-published all articles, flooding RabbitMQ with ~1 500 duplicate messages. Rule: if a Dockerfile comment says "mount this directory", there must be a matching entry in `docker-compose.prod.yml`. (Messor ADR-0012)
- **Pre-deploy volume seeding order**. When adding a volume mount to an existing service, Docker Compose names the volume `<project>_<volume-name>` (e.g. `inkbytes_inkbytes-messor-scrapes`). A bare `docker volume create <volume-name>` creates a *different* volume that the container will never see. Always seed using the full prefixed name, or seed after the first `compose up` using `docker run --rm -v <project>_<volume-name>:/dest …`. (Messor ADR-0012)
- **`docker compose down -v` / `docker volume prune` on the prod stack**. To remove ONE named volume during a migration, target it explicitly (`docker volume rm inkbytes_inkbytes-minio-data`). `down -v` / `volume prune` also destroy `inkbytes_inkbytes-messor-scrapes` (Messor's URL-dedup state) → the next cycle re-scrapes & re-publishes everything. This is what wiped dedup state during the ADR-0016 migration and drove the 105k-message backlog of 2026-06-09. (Messor ADR-0014) **Guardrail (2026-06-09):** `inkbytes-postgres-data` and `inkbytes-messor-scrapes` are now declared `external: true` (pinned via `name:` to the existing `inkbytes_*` volumes) in `infra/docker-compose.prod.yml`, so `docker compose down -v` can no longer delete them; `deploy.sh` creates them if absent. A blanket `volume prune` while the stack is *stopped* can still catch them, so the rule above still stands.
- **Per-DAY (vs per-RUN) staging filenames in Messor**. `process_outlet_articles` must name staging files with a per-run timestamp (`int(time.time())`), NOT `generate_today_timestamp()` (midnight). A per-day file accumulates every cycle's new articles, and `_publish_articles_from_staging_file` re-reads the WHOLE file each cycle → each article re-published ~4×/day, and after a dedup wipe the day-file balloons and replays in full (the 105k flood). Per-run files publish only-new. (Messor ADR-0014)
- **Harvesting without a freshness gate in Messor**. newspaper3k's `_slice_outlet_articles` tail-crawl surfaces deep archive links (theguardian back to 2012), and `pages.freshness_at = max(scraped_at)` makes any old article scraped today float to the top of the Reader feed. Messor must drop articles whose `publish_date` is outside `articles.freshness_window_hours` (48h) — strict: undated articles are dropped too — and take the homepage **head only** (no tail). Watch per-outlet `stale-skip` logs for outlets with poor date extraction. (Messor ADR-0015)
- **`pages.freshness_at` must use `max(scraped_at)`, never `max(published_at)`**. `published_at` is outlet-supplied and extracted by newspaper3k — it can be null, future-dated (newspaper3k picks up event dates from article body copy), or wrong. Using it as `freshness_at` pins future-dated stories permanently at the top of the Reader feed. `scraped_at` is stamped by Messor as `NOW()` at harvest time: always non-null, never in the future, semantically correct ("when did we last see news on this story").
- **Trusting a `curl` 200 as proof an outlet image will render in the Reader**. `lead_image` is the source outlet's og:image, embedded by the Reader as a *cross-origin* `<img>`. A real browser sends `Sec-Fetch-Dest: image` + `Sec-Fetch-Site: cross-site` on that load; some CDNs (LA Times' brightspot) read that fingerprint as hotlinking and 302-redirect to a 69-byte `placeholder-1x1.png` (HTTP 200) → blank hero, and `<img onError>` never fires (a successful pixel load isn't an error). Server-side fetchers (`curl`, Messor harvest, link-preview bots) omit `Sec-Fetch-*` and see the real image, so the dead URL passes extraction. Curator validates og:images at ingest with the browser fingerprint and NULLs blocked ones so the `/events` rollup falls back to another source (Curator ADR-0019). To verify an image renders, send `Sec-Fetch-Dest:image` + `Sec-Fetch-Site:cross-site`, not a bare `curl`.
- **Letting affiliate/commerce articles cluster into published "events"**. Outlets publish shopping content alongside news (The Guardian's vertical: gift guides, "best `<product>`" roundups, "I tested…", deals). These cluster by entity/embedding and synthesize into ad pages ("Guardian Covers Top New Mom Gifts and Sonos Speaker Reviews"). `SynthesizeSkill` gates publish via `services/promo_filter.py` (Curator ADR-0020): skip a cluster whose article titles are a *strict majority* commercial, and refuse ad-style synthesized headlines. The filter is precision-first — it targets purchase/affiliate/deal content, NOT news that mentions a brand, news *about* a shopping event (Black Friday fraud tips), or editorial best-of ("best shows to stream"). When adding patterns, re-run `scripts/test_promo_filter.py` and the corpus check (must stay ~0 false positives on the 282 page + 4000 article titles).
- **Letting horoscope / lottery / betting filler cluster into published "events"**. LATAM/ES + European dailies run *daily* horoscopes, lottery-result roundups, and sports-betting tips. They cluster strongly by recurrence and synthesize into junk pages. `SynthesizeSkill` gates publish via `services/content_filter.py` behind `application.filter_noise` (Curator ADR-0021), same shape as the promo gate: skip a strict-majority-filler cluster + refuse filler headlines. Precision-first — NEVER match bare sign names (`Cáncer` disease, Pope `León`, `Virgo`/`Virgin`), keep gambling-industry/regulation news and weather "pronóstico" and match previews. When adding patterns re-run `scripts/test_content_filter.py` (must stay 0 false positives) AND `scripts/test_promo_filter.py`.
- **`Schema::hasColumn()` in Backoffice migrations for `public.*` tables**. The Backoffice DB connection's `search_path` is `backoffice,public`. Laravel's `Schema::hasColumn('outlets', ...)` delegates to Doctrine DBAL, which introspects only the *first* schema in the path (`backoffice`) — `public.outlets` is invisible to it, so the guard always returns `false` and the `ALTER TABLE` fires even when the column already exists (e.g. added by a Curator migration that ran first). Use a raw query instead: `DB::selectOne("SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name=? AND column_name=?", [$table, $col])`. Pattern is in migrations `2026_06_10_000001` and `2026_06_10_000002`. (Messor ADR-0016, 2026-06-10)
- **Not calling `logger.setLevel()` on the logger itself in `LoggingService`**. `LoggerFactory.create_logger()` sets level on *handlers* (`handler.setLevel(log_level)`) but never on the logger object. A Python `logging.Logger` that has no level set inherits the root logger's `WARNING` default — all `INFO` records are silently dropped *before* reaching any handler, regardless of handler level. Always call `logger.setLevel(log_config.log_level)` after `LoggerFactory.create_logger()` in `LoggingService._configure_logger()`. (2026-06-10)

## What "done" looks like for v0 (Sunday 2026-06-07)

Six boxes from [`docs/mvp-plan.md`](./docs/mvp-plan.md) §7 (mirror of `docs/STATUS.md`):

- [x] Curator runs end-to-end on real LLM
- [x] At least one outlet returned ≥ 5 articles via Messor (22 outlets, 7,591 articles)
- [x] First event pages in `pages` table (413 published pages)
- [x] Reader renders events at `inkbytes.org` (production)
- [x] DO Droplet running docker-compose.prod.yaml at `inkbytes.org`
- [x] IllustrateSkill Phase 2 — media rail in production (Scrapling, Patchright, ADR-0011)
- [x] Reader v2 — force graph on mobile, media drawer in action bar, brand logo (ADR-R-0003/0004/0005)
- [ ] 24h of green scheduled cycles + first paying user invited
