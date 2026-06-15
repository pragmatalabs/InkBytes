# InkBytes — Overall Status

> *Status: v0 live on DigitalOcean · Owner: Julian · Last updated: 2026-06-14*
> *2026-06-14: **inkbytes.news marketing site (WordPress) — v2 multi-page theme.** Public marketing site live at `inkbytes.news` — WordPress on the Hostinger box (`82.112.250.139`, `/docker/wordpress-yybr`, behind Traefik + LE cert), NOT the droplet. (1) Security-hardened (additive `docker-compose.override.yml` + mu-plugin): proxy-aware HTTPS, `DISALLOW_FILE_EDIT`, XML-RPC blocked at proxy, REST/`?author=` user-enumeration killed, HSTS+security headers, `/wp-login.php` rate-limited. (2) The `inkbytes` theme is now a **full multi-page v2** built from the design-system static site `docs/marketing/site/`: home + how-it-works + why + features + pricing + methodology + about + contact + privacy + terms + The Desk (index + 1 post) + 404 — all verified live (HTTP 200, zero PHP errors). The site's `_ds/` design-system bundle isn't vendored, so the theme is **self-contained**: DS base tokens reconstructed in `style.css` (Archivo/Spectral/IBM Plex Mono), the DS React widgets rendered as **static HTML** (`parts/widget-*.php`), chrome server-rendered from `chrome.jsx`. No runtime React/Babel. Source of record: `docs/marketing/inkbytes-theme/` (`build-templates.py` regenerates page templates from `site/*.html`; `seed-pages.php` creates the Pages + pretty permalinks). Deployed **manually** to Hostinger via scp+docker cp (strip macOS quarantine xattr first). **Spanish `/es/` pages deferred** (needs Polylang). CTAs → reader at inkbytes.org. See memory `hostinger-wordpress-hardening`.*
> *2026-06-14: **Session batch (cost accuracy, taxonomy nav, pulse fix, entity coverage, bot icon).** (1) Cost-meter accuracy (Curator ADR-0028) — was overstating ~15× (reported ~$62/day; real DeepSeek invoice ~$3-4/day). Root cause: Claude-Haiku list prices ($1/$5 per Mtok) instead of deepseek-v4-flash ($0.14/$0.28) + ignoring the cache-hit discount ($0.0028/Mtok, ~half of input is cached). Now splits input cache-hit/miss; COST log shows `cache_hit=`; verified to the cent against the invoice. Live + confirmed. (2) Taxonomy navigation (Curator ADR-0027) — `/events?theme=&topic=&category=` filters + `/topics/trending`; Reader theme chips (pre-existing) + new Trending strip with server-side `?topic=` drill-down. Trending **recency-weighted** (hotness = coverage / (age+2)^1.2) so fresh topics lead the carousel instead of sinking to the end. (3) Pulse-lane tagging fix — `publish_scrape_session_completed` dropped `lane` from the payload, so every pulse session arrived untagged → Backoffice pulse filter was empty despite pulse running (8 outlets/5min). One-line forward fix. (4) Entity extraction — ENRICH prompt now defines all 5 types (PERSON/ORG/LOC/EVENT/OTHER) and requires typed coverage; EVENT was under-extracted (3.7% of entities) and mis-typed as OTHER (deals/negotiations) — verified fix on real samples. (5) Reader floating chat button → bot icon. (6) NewsScraper logs now under `Inkbytes.Messor` so per-stage breakdown (stale-skip/parse-fail/lang-skip) is visible — exposed that "0-success" outlets are German (lang-skip), paywalled (parse-fail), or undated (stale-skip), NOT lack of news. anthropic outlet disabled (no date, no feed). All deployed 2026-06-14.*
> *2026-06-13: **Pre-enrich triage gate** (Curator ADR-0030) — a small local model (`llama3.2:3b` on the Hostinger box) classifies each to-be-enriched article keep|junk from title+lede BEFORE the paid DeepSeek enrich, dropping filler (horoscopes/lottery/deals/dead pages). Runs after the dedup fast-path, before enrich; fail-OPEN (timeout/error → keep); bounded to 2 concurrent. Shipped in **shadow mode** (logs `TRIAGE shadow-DROP` without dropping) to measure drop-rate + precision before enforcing. First shadow batch caught `qwen2.5:3b` mislabeling real news → switched to `llama3.2:3b` + dropped the sports-betting/fixture categories (3B can't tell a match preview from a betting tip; betting is already gated at synthesis). Bigger models (mistral:7b 81s, gemma4:12b 500) too slow on the CPU box. **Now ENFORCING** (`shadow=false`) — shadow ran clean (50 verdicts, 2 drops, 0 false positives, 0 thrash errors), so junk is dropped before enrich as of 2026-06-13. Drop rate ~4% (lower than the 15-25% estimate after removing betting). Revert = set `TRIAGE_SHADOW=true` in droplet `infra/.env`. See ADR-0030 addendum. **⚠️ Known issue:** dropped articles have no terminal marker (`topic`/`enriched_at` stay NULL), so `--reenrich-missing` would re-enrich them and resurrect the junk — **do NOT run `--reenrich-missing` while triage is enforcing** (disable triage first). Also makes the dashboard "pending enrichment" counter drift upward. Fix flagged (add `triage_dropped_at` column), not yet built — ADR-0030 "Known limitation".*
> *2026-06-13: **Outlet redundancy analysis + "Decisive" column** — measured which outlets are near-duplicative (co-occurrence Jaccard + a "decisive %" = share of an outlet's events where it's load-bearing for the ≥2-source bar). Safe-cut signal now a live column on the Backoffice Outlets screen (red <25%). Findings: polifact (3%, never decisive) + mileniomx (subsumed by excelsiormx) are the clearest cuts; redundancy is within same region+language only. Full writeup: `docs/outlet-redundancy-analysis.md`.*
> *2026-06-13: **Rich markdown news body** (Reader ADR-0009) — event body now renders `synthesis_md` via react-markdown + remark-gfm (headings, bold, lists, blockquotes, links, tables) with brand-styled components + `[Source:]` → inline `cite` chips (rehype pass; raw HTML not rendered). synthesize.md prompt now asks for STRUCTURED markdown (bold lead → `##` sections → key-point bullets, 220–320w). Plus a feed hydration fix: relative timestamps routed through `<TimeAgo suppressHydrationWarning>` (Date.now() server/client drift was regenerating the tree). Existing plain pages still render; richer structure lands as they re-synthesize.*
> *2026-06-13: **On-Demand Breaking Desk shipped** (Curator ADR-0029, 3 services) — Backoffice screen: enter a title (Google News RSS search → batchexecute URL decode) or paste a URL → Messor scrapes on demand at AMQP priority 9, freshness gate bypassed → editor marks the resulting event breaking / clears / force-publishes (synthesize.run(force=True) past the ≥2-source + promo/noise gates). New Messor `core/gnews_search.py` + `POST /api/scrape/on-demand`; Curator `event.mark_breaking`/`clear_breaking`/`force_publish` commands; Backoffice "Breaking Desk" page + CuratorCommandService methods. Verified locally: search decoded 5/5 real URLs incl. the exact example; URL-mode scraped anthropic.com/news/fable-mythos-access (freshness bypass) and published @ priority 9; screen renders + Vite build compiles. Committed locally, NOT pushed/deployed.*
> *Also confirmed live (local): the ADR-0028 cache-aware cost meter — COST lines now show `cache_hit=` and project ~$0.27/1000 articles.*
> *2026-06-12: morning maintenance — REINDEX embedding index (recall + space); embed concurrency benchmarked → keep `_embed_sem=1` (Hostinger bge-m3 CPU-bound ~19/min, concurrency thrashes, ADR-0026 addendum); cost persistence confirmed healthy (was a query-schema mistake). Overnight: queue drained 3,700→~400, lag 10h→~30min.*
> *2026-06-12: **Ink-shader splash background** (Reader ADR-0008) — the daily "Morning Briefing" splash now renders over an animated WebGL ink/smoke field (vendored InkWall engine). Brand palette: deep navy + luminous indigo primary ink + a second coral (`--accent-dot`) ink stream drifting on an independent path. Everyone gets a gentle slow drift (reduced-motion → slower, never a frozen frame); WebGL-unavailable falls back to solid `--accent`. Drag-to-stir. Committed locally.*
> *2026-06-12: **Taxonomy navigation shipped** (Curator ADR-0027, all 3 surfaces) — 6a Curator API: `/events?theme=/?category=/?topic=` filters + `/topics/trending` (junk-excluded, page-aligned counts); 6b Reader: trending-topic strip + `?topic=` server-filtered drill-down (shareable URL, count==result); 6c Backoffice: theme/category/topic filters on the moderation view. Makes the previously-idle taxonomy indexes earn their keep. Committed locally, NOT yet pushed/deployed.*
> *Pipeline proven end-to-end. 413+ published pages. 22 active outlets. Continuous 12×/day harvest cycle.*
> *2026-06-08: ADR-0015 (synthesis cost cap + dedup fast-path) + Messor ADR-0012 (persistent staging volume) deployed — restart-driven queue flood eliminated.*
> *2026-06-08: ADR-0018 — `content_hash` made stable (normalized lede prefix); fixes the ADR-0015 fast-path that never fired. Tested locally, pending deploy.*
> *2026-06-09: 105 143-msg backlog purged. Root cause = ADR-0016 migration teardown wiped the dedup volume + per-DAY staging files re-published in full every cycle. Fixed by Messor ADR-0014 (per-RUN staging files). Tested locally, pending deploy.*
> *2026-06-09: Messor ADR-0015 — 48h harvest freshness gate (strict on undated) + dropped the archive tail-crawl. Stops month-old (back to 2012) articles entering as "fresh". History preserved (no prune). Tested locally, pending deploy.*
> *2026-06-09: Reader ADR-0007 — mobile daily splash ("Morning Briefing"), once per 24h over the home feed. Real Reader design system (Inter, LogoMark, --accent/--accent-dot); real local streak + live 24h category counts. Tested locally.*
> *2026-06-08: Curator ADR-0019 — lead-image hotlink guard. Outlet og:images embedded as a cross-origin `<img>` get hotlink-redirected by some CDNs (brightspot/LA Times) to a 1×1 `placeholder-1x1.png` (HTTP 200) → blank hero with no `onError`. `MediaValidator` probes each og:image at ingest with the browser `Sec-Fetch-*` fingerprint and NULLs blocked ones so the `/events` rollup falls back to another source. **Deployed + backfilled** (293 rows / 217 blocked URLs across 4,683 distinct). Verified live: the reported event now renders The Guardian's real photo. Two follow-up fixes: skip non-http(s) URLs (`data:` URIs were crashing the probe + would crash live ingest); don't false-positive images served without a Content-Type.*
> *2026-06-08: Messor — removed dead `process_found_articles` (no callers; pre-ADR-0011 thread-pool + ADR-0015-removed head+tail slicing). On branch `chore/remove-dead-process-found-articles`, **not yet pushed**.*
> *2026-06-09: Curator ADR-0021 — lead-image must come from a cluster CORE member. A marginal/mis-clustered article (e.g. a Stevie Nicks/Fleetwood Mac photo at distance 0.47 on the "Michael Tilson Thomas, conductor, dies" obituary) was hijacking the hero because it was the freshest article with an image. The `/events` rollup now gates `cluster_distance <= 0.45` (attach threshold is 0.50); events whose only image is an outlier go text-only. Query-time rollup — no migration. Impact: 281 events → 270 keep hero, 8 go text-only, 39 switch to a more-core image.*
> *2026-06-09: Curator ADR-0020 — promotional/commerce content filter. Affiliate clusters (e.g. The Guardian's shopping vertical → "Guardian Covers Top New Mom Gifts and Sonos Speaker Reviews") no longer publish: SynthesizeSkill skips a cluster whose article titles are a strict majority commercial, and refuses ad-style synthesized headlines. Deterministic `services/promo_filter.py`, tuned to 1/282 page headlines + 17/4000 article titles (zero false positives). Backfill un-publishes existing ad pages (`scripts/backfill_promo_pages.py`).*
> *2026-06-10: Messor ADR-0013 (RSS-first harvesting) **implemented** — `feed_url` per outlet in DB (Curator migration 012 + Laravel migration 000001); `FeedScraper` / `get_articles_from_feed()` with 48h freshness gate + newspaper3k fallback; BBC, Al Jazeera, Reuters + 4 LATAM outlets seeded. Messor ADR-0016 — per-outlet scraper config pattern (`min_word_count`, Curator migration 013). Logger level bug fixed (INFO was silently dropped — `LoggingService` never called `logger.setLevel()`). arm64 architecture fix for Backoffice-triggered scrapes confirmed working. Deployed 2026-06-10.*
> *2026-06-11: **prod `feed_url` backfill + stub bug found** — the 2026-06-10 RSS seeding only landed in `outlets.json` (local fallback); prod reads outlets from Curator API → DB where `feed_url` was NULL for all 65 outlets, so RSS-first was dormant. Every candidate feed probed from the droplet with a browser UA; 22 verified-working feeds + 9 `min_word_count` overrides backfilled via psql. Corrected 7 dead/wrong URLs (Arc Publishing `arc/outboundfeeds/rss/?outputType=xml` for infobae/lanacionar/eluniversalmx/semana; real CNBC feed; economist `/latest/rss.xml`; eltiempo `colombia.xml`). No working feed: apnews, cnn, reuters, elespectador, animalpolitico, mileniomx — stay on newspaper3k. First live BBC run then exposed TWO blockers, both fixed + deployed same day: (1) `_FeedArticleStub` lacked `.download()` — every feed article died on AttributeError and the newspaper3k fallback never fires when the feed fetch itself succeeds; fixed by returning real undownloaded `newspaper.Article` objects. (2) newspaper3k can't extract a byline date from BBC pages → `publish_date='None'` → the strict ADR-0015 freshness gate dropped all 29 as undated; fixed by stamping the feed entry's outlet-authoritative pubDate as `publish_date` fallback. **Verified live post-deploy: BBC session tot=28 ok=21 (was ~1 article/day), 21 events published to RabbitMQ, Curator consuming.** Backfill re-applied (22 outlets with feeds). Ollama-reconnect systemd unit confirmed already in place + working. New `make soak-report` target. Soak clock starts now — next scheduled cycle is the first with RSS active fleet-wide.*
> *2026-06-11: **ADR-0008 — Editorial service (design accepted)** — daily per-theme editorial persona, separate service outside Curator, provider-pluggable LLM. Live bake-off on real corpus data: gemma4 12B = Spanish quality floor; 4B-class fails. Dev local (Mac), prod DeepSeek until the 16 GB droplet upgrade, then local.*
> *2026-06-11: **Curator ADR-0026 — embeddings offloaded to Hostinger.** The ADR-0025 concurrency fix was capped by the real bottleneck: DO's CPU-only Ollama embedded bge-m3 in ~15s under scrape contention, serialized → ~4/min pipeline ceiling → permanent ~3,700-msg queue / ~10h Reader lag. Pointed prod embeddings at the Hostinger box (82.112.250.139:32768, idle 16GB, firewalled to the droplet) running the SAME bge-m3 → ~2.2s warm, ~27/min, **zero re-embed / zero clustering break** (same 1024-dim space). Backlog drains in ~2.3h then stays real-time. One env var in docker-compose.do.yml; no migration.*
> *2026-06-11: **Curator ADR-0025 — concurrent pipeline + intake age gate.** Root cause of "old headlines pinned / new articles not showing": `prefetch_count=1` serialized the whole pipeline behind the 8–17s enrich LLM call → ~4.3 articles/min vs ~4–6k/day inflow → permanent ~3.5k-message queue ≈ 9–13h Reader latency. Fix: prefetch 8 + concurrent enrich, with `_embed_sem(1)` protecting CPU Ollama and `_cluster_lock` preventing duplicate-event seeding. Plus a 48h `scraped_at` intake gate (`max_article_age_hours`) that acks-and-drops stale messages before any LLM spend. Verified locally on real articles: **~70/min (16×)**, zero Ollama timeouts, concurrent same-story articles attach to one event, 60h-old message dropped at intake. Committed, pending deploy.*
> *2026-06-11: **Breaking-news fast lane, Phases 1+2 implemented** (Messor ADR-0017 + Curator ADR-0024) — 5-min RSS-only pulse over 10 flagged outlets (`outlets.pulse`, Backoffice switch), per-article AMQP priority 9, Curator consume queue declared `x-max-priority=10` (graceful fallback until the existing prod queue is drained+deleted — see ADR-0024 §migration), cluster-velocity breaking detector (≥2 pulse outlets within 60 min → `events.breaking_at`, demotes after 2h). Tested locally: detector positive/negative/re-fire/TTL cases, real AMQP priority ordering, feed_only skip path. **Deployed 2026-06-11 ~20:30 UTC**: migration 014 applied, 10 pulse outlets seeded, pulse thread live ("⚡ Pulse lane active"). Queue migrated zero-loss via `infra/scripts/migrate_priority_queue.py` (worker stopped → 3,248 msgs shoveled to tmp → queue recreated `x-max-priority=10` + rebound → msgs shoveled back → worker restarted; the planned "wait for drain" was impossible — backlog drains ~1 msg/min ≈ 2 days). Note: an orphaned legacy `articles-scraped` queue (346 msgs, zero consumers, pre-ADR-0004) exists — delete when convenient. Phases 3+4 (breaking synthesis persona + Reader rail) agreed, not started.*

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

## Active outlets (65 — all active as of 2026-06-11)

All outlets in `public.outlets` are active. 22 have a droplet-verified `feed_url`
(RSS-first); the rest use newspaper3k homepage crawl. Check live health with
`make soak-report`.

### Outlets with verified RSS feeds (backfilled 2026-06-11)

`bbc · aljazeera · eldinerodr · npr · theguardian · latimes · gizmodo · clarin ·
cnbc · wired · foxbusiness · bloomberg · financialtimes · elfinancierolatam ·
eluniversalmx · infobae · lanacionar · theeconomist · semana · techcrunch · wsj ·
eltiempoco`

### No working feed found (probed 2026-06-11 — stay on newspaper3k)

| Outlet | Probe result |
|---|---|
| apnews | rsshub proxy 403; no official RSS |
| cnn | rss.cnn.com discontinued |
| reuters | feeds.reuters.com discontinued |
| elespectador | 404 on all known paths (incl. Arc outboundfeeds) |
| animalpolitico | 404 on /feed, /rss, /rss.xml |
| mileniomx | 403 (bot-blocked) on /rss |

Note: paywalled outlets (bloomberg/wsj/economist/FT) have working *feeds* but
article-page fetches may still hit the paywall — watch their parse_pct in the
soak report before judging.

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
2. ✅ **Ollama reconnect on reboot** (verified 2026-06-11) — `ollama-inkbytes-network.service` systemd unit on the droplet (enabled, oneshot, waits up to 60s for the `inkbytes_inkbytes-internal` network then connects `infra-ollama`). `deploy.sh` also reconnects at every deploy. Connectivity verified from inside `inkbytes-curator-worker` (HTTP 200 on `/api/tags`).
3. **Phase 3 / Stripe** — subscriber gating blocked on pricing decisions. See `docs/product.md`.
4. **24h green soak** — let 4 scheduled cycles complete; verify Scrape Results shows outlets at >80% parse success.

### P1 — Scraping quality

5. ✅ **RSS/Atom-first harvesting** (Messor ADR-0013, 2026-06-10) — `feed_url` per outlet; `FeedScraper` with 48h freshness gate; newspaper3k fallback when feed absent/fails. BBC, Al Jazeera, Reuters, wired, foxbusiness, animalpolitico, eldinerodr + 3 LATAM dailies seeded. **Re-enable disabled outlets in Backoffice.**
6. ✅ **Per-outlet `feed_url` in DB** — Curator migration 012 + Laravel migration 000001 (both deployed).
7. ✅ **Per-outlet `min_word_count`** (Messor ADR-0016, 2026-06-10) — overrides global 40-word floor per outlet (BBC/Reuters/LATAM dailies set to 25).
8. **trafilatura fallback parser** — when newspaper3k fails, try trafilatura. Better for modern JS sites.
9. **Per-outlet rate-limit / custom headers** — follow the ADR-0016 pattern: one DB column + SCRAPER_FIELDS entry + Pydantic field.

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

### P2 — Editorial service (Sprint 2)

16. **Editorial service (ADR-0008, design accepted 2026-06-11)** — daily per-theme
    editorial column by a named persona, **separate service outside Curator**.
    Provider-pluggable LLM (`ollama | deepseek | anthropic`, ADR-0003 pattern).
    Bake-off result: **gemma4 12B is the quality floor for Spanish** — 4B-class
    fails (gender errors, anglicisms, invented facts). Sequencing: dev = local
    gemma4 on the Mac; prod launch = DeepSeek (<$0.05/day — droplet can't host
    12B); prod local after the 8→16 GB droplet upgrade. Themes from
    `articles.theme` (8 verticals); `events.topic` is empty — don't use it.
    See [`docs/adr/0008-editorial-service-llm-selection.md`](./adr/0008-editorial-service-llm-selection.md).

### P2 — Infrastructure (Sprint 2)

11. **Object store consolidation + embedding durability (Curator ADR-0016)** — Two separate objects stores in prod (MinIO internal + DO Spaces for Messor) is an accident of history. Sprint 2: remove `inkbytes-minio` from prod stack; point all services (Curator, Backoffice) at DO Spaces. Add daily `pg_dump` to DO Spaces (`backups/postgres/YYYY-MM-DD.sql.gz`, 28-day retention) — reduces embedding recovery from ~18h re-embed to ~10 min restore. pgvector stays; re-evaluate at 100k articles (~2 months out).

### Marketing site (inkbytes.news)

- ✅ **`inkbytes` WordPress theme committed** to the monorepo at
  `docs/marketing/inkbytes-theme/` (2026-06-14) — it's the live homepage of
  `inkbytes.news`. Deployed **manually** to the Hostinger box (`docker cp` →
  activate via DB), not in CI; revert = stock `twentytwentyfive`. See memory
  `hostinger-wordpress-hardening` + the theme README for deploy/activate steps.
- **Phase-1 marketing site v2** (`docs/marketing/site/`) — a richer multi-page
  static site (about/methodology/pricing/contact) on the InkBytes Design System
  is in progress in a separate workstream; not yet committed or deployed (depends
  on a `_ds/` bundle not yet in the tree). Decision pending: keep under
  `docs/marketing/` or extract to its own repo.
- **Outstanding host-level exposures on the Hostinger box** (flagged, awaiting decision):
  open-webui world-exposed on `:8080` (host-network) + `:32769`; SSH `PermitRootLogin yes`
  + `PasswordAuthentication yes`. (Ollama `:32768` is correctly firewalled.)

### P3 — Infrastructure

12. **GitHub Actions CI/CD** — auto-build and deploy on `git push master`. Set secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`.
13. **Curator config default** — change `embeddings_base_url` default to `http://ollama:11434/v1` (currently `localhost:11434` breaks after `migrate:fresh`).
14. **Approach B entity embeddings** — event-level pgvector for related-events at >1000 events scale.
15. **Reader traffic analytics in Backoffice** ("Reader Hits") — surface per-request hits to the Reader (top events, by country, over time) in the Backoffice. Design note (incl. GDPR/PII handling — salted IP hash, GeoIP-then-discard): [`docs/reader-traffic-analytics.md`](./reader-traffic-analytics.md). Leading approach: Reader middleware → RabbitMQ `reader.hit.v1` → aggregate table. **Design only, not built.**

---

## Repository

- **Canonical remote:** https://github.com/pragmatalabs/InkBytes (`master`)
- **Registry:** GitHub Container Registry `ghcr.io/pragmatalabs` (free; replaced DO registry)
- **Secrets:** never committed — set via `infra/.env` on server (see `docs/deployment-secrets.md`)
