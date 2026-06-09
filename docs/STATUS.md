# InkBytes — Overall Status

> *Status: v0 live on DigitalOcean · Owner: Julian · Last updated: 2026-06-08*
> *Pipeline proven end-to-end. 413+ published pages. 22 active outlets. Continuous 12×/day harvest cycle.*
> *2026-06-08: ADR-0015 (synthesis cost cap + dedup fast-path) + Messor ADR-0012 (persistent staging volume) deployed — restart-driven queue flood eliminated.*
> *2026-06-08: ADR-0018 — `content_hash` made stable (normalized lede prefix); fixes the ADR-0015 fast-path that never fired. Tested locally, pending deploy.*
> *2026-06-09: 105 143-msg backlog purged. Root cause = ADR-0016 migration teardown wiped the dedup volume + per-DAY staging files re-published in full every cycle. Fixed by Messor ADR-0014 (per-RUN staging files). Tested locally, pending deploy.*
> *2026-06-09: Messor ADR-0015 — 48h harvest freshness gate (strict on undated) + dropped the archive tail-crawl. Stops month-old (back to 2012) articles entering as "fresh". History preserved (no prune). Tested locally, pending deploy.*
> *2026-06-09: Reader ADR-0007 — mobile daily splash ("Morning Briefing"), once per 24h over the home feed. Real Reader design system (Inter, LogoMark, --accent/--accent-dot); real local streak + live 24h category counts. Tested locally.*
> *2026-06-08: Curator ADR-0019 — lead-image hotlink guard. Outlet og:images embedded as a cross-origin `<img>` get hotlink-redirected by some CDNs (brightspot/LA Times) to a 1×1 `placeholder-1x1.png` (HTTP 200) → blank hero with no `onError`. `MediaValidator` probes each og:image at ingest with the browser `Sec-Fetch-*` fingerprint and NULLs blocked ones so the `/events` rollup falls back to another source. **Deployed + backfilled** (293 rows / 217 blocked URLs across 4,683 distinct). Verified live: the reported event now renders The Guardian's real photo. Two follow-up fixes: skip non-http(s) URLs (`data:` URIs were crashing the probe + would crash live ingest); don't false-positive images served without a Content-Type.*
> *2026-06-08: Messor — removed dead `process_found_articles` (no callers; pre-ADR-0011 thread-pool + ADR-0015-removed head+tail slicing). On branch `chore/remove-dead-process-found-articles`, **not yet pushed**.*

---

## TL;DR

The full v0 pipeline runs end-to-end on real infrastructure:
**Messor (harvest) → RabbitMQ → Curator (enrich + cluster + synthesize) → Reader (pages)**.

- **Reader:** https://inkbytes.org
- **Backoffice:** https://admin.inkbytes.org
- **Server:** DigitalOcean Droplet `67.205.136.61` · Docker + Traefik

---

## Live pipeline numbers (2026-06-07)

| Metric | Value |
|---|---|
| Total articles | 7,591 |
| Enriched | 7,078 (93%) |
| Events | 413 |
| Published pages | 413 |
| Active outlets | 22 of 34 |
| LLM — enrich | DeepSeek `deepseek-chat` |
| LLM — synthesize | DeepSeek `deepseek-reasoner` |
| Embeddings | Ollama `bge-m3` (1024-dim) |
| Cost projection | ~$5–10 / 1000 articles |
| Scraping schedule | 12×/day (~120 min interval) |

---

## Service state (production — DigitalOcean `67.205.136.61`)

| Service | Container | URL / Port | State |
|---|---|---|---|
| Reader (Next.js) | `inkbytes-reader` | `:18050` → `inkbytes.org` | ✅ healthy |
| Backoffice (nginx+php-fpm) | `inkbytes-backoffice` | `:18051` → `admin.inkbytes.org` | ✅ up |
| Curator API | `inkbytes-curator-api` | `:8060` (internal) | ✅ healthy |
| Curator Worker | `inkbytes-curator-worker` | internal | ✅ healthy |
| Messor harvester | `inkbytes-messor` | `:8050` (internal) | ✅ running |
| Postgres + pgvector | `inkbytes-postgres` | `:5432` (internal) | ✅ healthy |
| RabbitMQ | `inkbytes-rabbitmq` | `:5672` / mgmt `:15683` | ✅ healthy |
| MinIO (S3 stand-in) | `inkbytes-minio` | `:9000` / console `:9030` | ✅ healthy |
| Ollama (shared host) | `ollama` | `:11434` (host-network) | ✅ bge-m3 loaded |
| Traefik | host-network | `:80/:443` | ✅ TLS via Let's Encrypt |

### Memory limits (infra/docker-compose.prod.yml)

| Container | Limit | Typical usage |
|---|---|---|
| `inkbytes-messor` | 6 GB | 2–3 GB mid-scrape, ~150 MB idle |
| `inkbytes-curator-worker` | **1.5 GB** | ~200 MB idle / ~400 MB peak (IllustrateSkill — 1× Chromium for YouTube only, serialised via Semaphore(1); Bing image fetcher parked ADR-0014); `shm_size:'256m'` + `seccomp:unconfined` required to prevent Chromium SIGTRAP on Docker |
| `inkbytes-reader` | 512 MB | ~65 MB |
| `inkbytes-backoffice` | 512 MB | ~115 MB |
| `inkbytes-curator-api` | 512 MB | ~110 MB |
| `ollama` | 3 GB | ~1.6 GB (bge-m3) |

---

## Active outlets (22)

`apnews · clarin · cnbc · cnn · diariolibree · elcaribedr · elespectador · elfinancierolatam · eltiempoco · eluniversalmx · gizmodo · ground-news · infobae · lanacionar · latimes · listindiario · mileniomx · npr · semana · techcrunch · theguardian · acentodr`

### Disabled outlets (12) — reason

| Outlet | Reason |
|---|---|
| bbc | Geo-blocked on Hostinger IP; redirect loop (`Exceeded 30 redirects`) |
| aljazeera | Rate-limited; parse success dropped to 1.4% on back-to-back runs |
| bloomberg | Hard paywall — 0 articles harvested |
| wsj | Hard paywall — 0 articles harvested |
| reuters | Geo-blocked — 0 articles harvested |
| theeconomist | Hard paywall — 0 articles harvested |
| financialtimes | Soft paywall — 0 articles saved |
| wired | JS-rendered / soft paywall — 0 articles saved |
| foxbusiness | Broken newspaper3k parsing — 0.7% parse success |
| polifact | Broken parsing — 0% parse success |
| animalpolitico | Broken parsing — 0% parse success |
| eldinerodr | Broken parsing — 3.4% parse success |

---

## v0 Definition of Done

- [x] Curator runs end-to-end on real LLM
- [x] At least one outlet returned ≥ 5 articles via Messor
- [x] First event pages in `pages` table (413 multi-source pages)
- [x] Reader renders events at production URL
- [x] Server running docker-compose.prod.yaml at `inkbytes.org`
- [x] Continuous 12×/day scheduled cycles with per-outlet session tracking
- [x] Synthesis cost cap (ADR-0015) — max 15 articles / 2 per outlet; 9× token reduction deployed 2026-06-08
- [x] Duplicate enrichment fast-path (ADR-0015) — unchanged articles skip LLM; queue drains in ~2h not ~21d, deployed 2026-06-08
- [x] Stable `content_hash` (ADR-0018) — fixes the ADR-0015 fast-path that never fired (raw hash churned on newspaper3k noise → 0 SKIP / 176 ENRICH, ~$780 / 13-day drain); now hashes a normalized lede prefix. Tested locally, pending deploy.
- [x] Persistent Messor staging volume (ADR-0012) — `inkbytes_inkbytes-messor-scrapes` pre-seeded; no more restart floods, deployed 2026-06-08
- [x] Per-RUN staging files (Messor ADR-0014) — fixes the per-day file that re-published in full every cycle; ADR-0016 migration teardown had wiped the dedup volume → 105 143-msg backlog (purged 2026-06-09). Volume mount intact (survives restart); per-run files make any future wipe survivable. Tested locally, pending deploy.
- [ ] 24h of green scheduled cycles + first paying user invited
- [ ] Switch to `inkbytes.news` domain (DNS A records → `67.205.136.61`)
- [ ] GitHub Actions CI/CD (secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`)

---

## Monitoring commands (from repo root)

```bash
make status           # snapshot: all containers + memory table
make watch            # live stats every 5s
make logs             # follow ALL service logs
make logs-messor      # follow Messor (scraping progress)
make logs-curator     # follow Curator worker (enrich/cluster/synth)
make logs-backoffice  # follow Backoffice (Laravel)
make health           # HTTP status of reader + admin
make shell            # SSH into server
make shell-db         # psql on production Postgres
make shell-curator    # bash in curator-api container
```

---

## Open items / next steps

### P0 — Blocking on first paying user

1. **`inkbytes.news` domain** — add A records → `67.205.136.61`; update `READER_DOMAIN`/`ADMIN_DOMAIN` in `infra/.env` on DO Droplet; update Traefik config.
2. **Ollama reconnect on reboot** — `docker network connect inkbytes_inkbytes-internal infra-ollama` is currently manual after server reboot. Add a systemd unit or cron.
3. **Phase 3 / Stripe** — subscriber gating blocked on pricing decisions. See `docs/product.md`.
4. **24h green soak** — let 4 scheduled cycles complete; verify Scrape Results shows outlets at >80% parse success.

### P1 — Scraping quality

5. **RSS/Atom-first harvesting** — designed in `docs/roadmap.md`, not yet implemented. feedparser + trafilatura replaces newspaper3k homepage crawl. Expected: cycle time 28 min → 4-6 min.
6. **Per-outlet `feed_url` in DB** — `ALTER TABLE public.outlets ADD COLUMN feed_url text;` — prerequisite for RSS-first.
7. **trafilatura fallback parser** — when newspaper3k fails, try trafilatura. Better for modern JS sites.
8. **Per-outlet config** — custom headers (Referer, Accept-Language) and rate-limit delays per outlet.

### P2 — Reader

9. **Reader R4** — global perf/SEO pass. Lighthouse score, sitemap.xml.
10. **Language filter on feed** — Spanish content stays in Spanish; Reader shows language badge.
11. **Media Tier 1** ✅ 2026-06-07 — Messor passively extracts `og:image`/`top_image` and YouTube embeds; stored in `articles.lead_image`/`video_url`; rolled up to event level in API; Reader LeadCard, SecondaryCard, and event detail hero show cover image (ADR-0010).
    - ✅ 2026-06-08 — **Lead-image hotlink guard** (Curator ADR-0019): `MediaValidator` probes each og:image at ingest with the browser `Sec-Fetch-Dest:image`+`Sec-Fetch-Site:cross-site` fingerprint and NULLs URLs that hotlink-redirect to a placeholder pixel / 404 / serve an error page / a <512B pixel, so the `/events` rollup falls back to another source. Deployed + one-time backfill applied (`scripts/backfill_lead_images.py`). Toggle `application.validate_lead_images` (default true).
12. **Media Tier 2** ✅ 2026-06-07 — `IllustrateSkill` output (`pages.media_rail`) surfaced end-to-end. Curator API exposes `media_rail`; `MediaRailItem` typed in Reader. Event page: collapsed drawer in the action bar (streaming icon + pulse rings alongside Share button) — expands to **video chips only** on click. `MediaRailDrawer` client component owns toggle state (ADR-R-0003, ADR-R-0004).
    - ✅ 2026-06-08 — **Media rail video-only** (ADR-0014 / ADR-R-0006): Bing image fetcher parked; `media_rail` stores YouTube videos only. Eliminates off-topic editorial/product photos. Existing image items silently skipped at render time — no migration needed.
15. **Entities graph on mobile** ✅ 2026-06-07 — Force-directed SVG graph now renders on all screen sizes (was replaced by a pill list on mobile). Single responsive grid (`grid-cols-1 md:grid-cols-[1fr_320px]`); `touchAction:none` on SVG so finger-drag moves nodes without triggering page scroll (ADR-R-0004).
13. **PWA + bottom nav + share** ✅ 2026-06-07 — Web App Manifest, bottom nav (News/Search/Entities/About), Web Share API share button on event pages (ADR-R-0001). TODO: generate 192/512px PNG icons for Android install banner.
14. **Brand logo mark** ✅ 2026-06-07 — Real brand SVG (`InkBytes-Logo-White-cropped.svg`) wired into header (`<LogoMark>` component, `currentColor`) and favicon (`icon.svg` dark bg) replacing placeholder (ADR-R-0003).
14. **PNG app icons** — generate `/public/icon-192.png` and `/public/icon-512.png` from `icon.svg` for full Android PWA install prompt (`inkscape --export-type=png --export-width=192`).

### P2 — Event lifecycle (Sprint 2)

14. **Story arc archive (Curator ADR-0013)** — When a published event's `last_updated_at` is older than 7 days, mark it `concluded` and write a `story_arcs` record with `arc_article_ids TEXT[]` (ordered pointers into `articles.embedding`). Enables future "concluded story" UI badge, arc-similarity recommendation, and RAG context injection. Migration 010 + `--conclude-stories` command + `conclude_after_days` config.
15. **Stale article filter (Curator ADR-0012)** — Gate in Curator's `_handle_event()`: if `article.published_at > max_article_age_days (default 7)` AND no active cluster matches, drop without ENRICH/EMBED. Prevents orphan events from old re-featured homepage content. Depends on `find_nearest_active_event()` probe query + `max_article_age_days` config. *(Note: Messor ADR-0012 is the separate staging-volume fix — different service, same number is fine.)*

### P2 — Infrastructure (Sprint 2)

11. **Object store consolidation + embedding durability (Curator ADR-0016)** — Two separate objects stores in prod (MinIO internal + DO Spaces for Messor) is an accident of history. Sprint 2: remove `inkbytes-minio` from prod stack; point all services (Curator, Backoffice) at DO Spaces. Add daily `pg_dump` to DO Spaces (`backups/postgres/YYYY-MM-DD.sql.gz`, 28-day retention) — reduces embedding recovery from ~18h re-embed to ~10 min restore. pgvector stays; re-evaluate at 100k articles (~2 months out).

### P3 — Infrastructure

12. **GitHub Actions CI/CD** — auto-build and deploy on `git push master`. Set secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`.
13. **Curator config default** — change `embeddings_base_url` default to `http://ollama:11434/v1` (currently `localhost:11434` breaks after `migrate:fresh`).
14. **Approach B entity embeddings** — event-level pgvector for related-events at >1000 events scale.

---

## Repository

- **Canonical remote:** https://github.com/pragmatalabs/InkBytes (`master`)
- **Registry:** GitHub Container Registry `ghcr.io/pragmatalabs` (free; replaced DO registry)
- **Secrets:** never committed — set via `infra/.env` on server (see `docs/deployment-secrets.md`)
