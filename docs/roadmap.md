# InkBytes — Product & Engineering Roadmap

> *Status: living document · Owner: Julian · Last updated: 2026-06-07*

---

## Where we are

v0 is live on Hostinger VPS (`inkbytes.galvanic.cloud`). 413 published pages, 22 active
outlets, 4 scraping cycles/day. The pipeline is proven end-to-end; the remaining work
is quality, distribution, and monetisation.

---

## Scraping — RSS/Atom-first (P1, Sprint 2)

### Problem with current approach

`newspaper3k.build(outlet.url)` crawls the homepage, downloads all category pages
(10–20 HTTP requests), and generates 500–1,500 article URLs — most of which are old
archive content or navigation links. This:

- Takes 2–5 min per outlet (homepage crawl + category downloads)
- Returns 70–90% duplicates per cycle
- Hangs on JS-rendered or rate-limiting sites
- Runs `download_categories()` which has no timeout and can freeze threads for hours

### v2 architecture

```
feedparser.parse(feed_url)   # 1 HTTP req · ~200ms · pure XML
  → entries[:200]            # already sorted newest-first by outlet
  → dedup against history    # skip known URLs/hashes
  → trafilatura.extract(N)   # parallel content fetch · 30s timeout
```

**Expected improvements:**

| Metric | Now (newspaper3k) | v2 (feedparser + trafilatura) |
|---|---|---|
| HTTP reqs per outlet | 10–20 + N articles | 1 feed + N articles |
| Time per outlet | 2–5 min | 15–30 s |
| Full cycle (22 outlets) | 15–28 min | 3–6 min |
| Duplicate rate | 70–90% | 5–20% |
| Thread hangs | Yes | No (feedparser is pure XML) |

### Implementation plan

**Phase 1 — Feed URL storage**
```sql
ALTER TABLE public.outlets ADD COLUMN feed_url text;
```
Backoffice: editable `feed_url` field per outlet. Pre-populated for known outlets (see table below).

**Phase 2 — Feed discovery**
```python
FEED_PATHS = ['/feed', '/feed.xml', '/rss', '/rss.xml', '/atom.xml', ...]

def discover_feed(outlet_url) -> str | None:
    # 1. Try common paths (HEAD requests, 5s timeout)
    # 2. Parse homepage for <link rel="alternate" type="application/rss+xml">
    # 3. Return None → fallback to newspaper3k
```

**Phase 3 — FeedScraper class**
```python
class FeedScraper:
    MAX_ARTICLES = 200
    MAX_AGE_HOURS = 48

    def scrape(self, outlet, feed_url) -> list[Article]:
        feed    = feedparser.parse(feed_url)           # 1 req
        entries = feed.entries[:self.MAX_ARTICLES]     # top-N newest
        fresh   = [e for e in entries if age(e) < 48h]
        # parallel content fetch via ThreadPoolExecutor(max_workers=4)
        # trafilatura.fetch_url(url) + trafilatura.extract(html)
        # fallback to feed's own <content> or <summary> if fetch fails
```

**Phase 4 — Fallback strategy**
```
outlet.feed_url set?
  YES → FeedScraper (fast path)
  NO  → discover_feed(outlet.url)
          found → cache to DB → FeedScraper
          not found → existing NewsScraper (newspaper3k fallback)
```

### Known feed URLs for active outlets

| Outlet | Feed URL |
|---|---|
| CNN | `https://rss.cnn.com/rss/edition.rss` |
| AP News | `https://apnews.com/rss` |
| NPR | `https://feeds.npr.org/1001/rss.xml` |
| The Guardian | `https://www.theguardian.com/world/rss` |
| LA Times | `https://www.latimes.com/world-nation/rss2.0.xml` |
| CNBC | `https://feeds.feedburner.com/cnbc/technology` |
| TechCrunch | `https://techcrunch.com/feed/` |
| Gizmodo | `https://gizmodo.com/rss` |
| Infobae | `https://www.infobae.com/feeds/rss/` |
| Clarín | `https://www.clarin.com/rss/lo-ultimo/` |
| El Tiempo CO | `https://www.eltiempo.com/rss/portada.xml` |
| Semana | `https://www.semana.com/rss/` |
| Milenio MX | `https://www.milenio.com/rss` |
| El Universal MX | `https://www.eluniversal.com.mx/rss.xml` |
| El Espectador | `https://www.elespectador.com/arc/outboundfeeds/rss/` |

### Dependencies to add

```
feedparser>=6.0.11       # RSS 2.0 + Atom parsing, BSD-2-Clause, no deps
trafilatura>=1.8.0       # content extraction from HTML, Apache-2.0
```

---

## Scraping — per-outlet configuration (P1, Sprint 2)

Some outlets need specific treatment that can't be global:

| Need | Outlet(s) | Config field |
|---|---|---|
| Custom `Referer` header | theguardian, latimes | `headers_override` jsonb |
| `User-Agent` rotation | cnbc, clarin | `user_agent` text |
| Rate-limit delay (s between articles) | semana, eltiempoco | `rate_limit_ms` int |
| Language override | mixed outlets | `primary_language` text |
| Priority (which outlets run first) | apnews, cnn | `priority` int (already exists) |

Schema addition:
```sql
ALTER TABLE public.outlets ADD COLUMN scraper_config jsonb DEFAULT '{}'::jsonb;
```

Backoffice: expandable "Advanced" section per outlet for these fields.

---

## Language strategy (P1, Sprint 2)

**Current:** All articles go through the same pipeline regardless of language. Synthesis
prompt is in English; Spanish articles produce English synthesis. Reader shows all content
in one feed.

**Target:** Spanish content stays in Spanish through the full pipeline.

**Phase A (now):** Language filter on the Reader feed (toggle: EN / ES / All).

**Phase B (Sprint 2):**
- Separate synthesis prompts for `language='es'` and `language='en'`
- Curator: `prompts/synthesize_es.md` alongside `prompts/synthesize.md`
- Events gain a `language` column (derived from majority language of sources)
- Reader: language badge on feed cards; filter persists in localStorage

**Phase C (future):** Cross-language clustering (an AP English article and an Infobae
Spanish article about the same event → same event, bilingual synthesis).

---

## Curator embeddings — Approach B (P2, Sprint 3)

**Current:** Article-level embeddings in `public.articles.embedding` (1024-dim bge-m3).
Clustering uses cosine similarity between article embeddings. Works well at < 500 events.

**Problem at scale:** At > 1,000 events, cosine search over all article embeddings
becomes O(N) per new article. Related-events query is also O(N²).

**Approach B:** Event-level embeddings.
- After synthesis, embed the event headline + synthesis summary → store in `public.events.embedding`
- Related events: `SELECT ... ORDER BY embedding <=> $1 LIMIT 10` (pgvector index)
- Expected: related-events query from O(N) article scan → O(log N) HNSW index

**Migration:** `ALTER TABLE public.events ADD COLUMN embedding vector(1024);`
Backfill via `--reenrich-missing` equivalent for events.

---

## Reader — R4 global polish (P2)

- **Lighthouse score** — target 90+ performance. Largest Contentful Paint on event page.
- **og:image** — generate a dynamic OG image per event (outlet logos + headline).
- **Sitemap** — `sitemap.xml` with all published event pages.
- **robots.txt** — allow crawlers; block `/login`, `/api`.
- **404 / error pages** — branded, with "latest events" fallback.
- **Freshness indicator** — "Updated N hours ago" ribbon on event cards.

---

## Monetisation — Phase 3 (blocked on pricing decision)

**Scope:** Stripe test credentials + pricing decisions from Owner before starting.

Technical plan (when unblocked):
1. `composer require laravel/cashier` in Backoffice
2. New tables in `backoffice`: `customers`, `subscriptions`
3. Staff roles: `admin / operator / viewer / subscriber / guest`
4. Sanctum API tokens for Reader auth
5. Reader subscriber gating: `/event/[id]` requires valid token
6. Backoffice: subscription management UI

**Pricing options** (to decide):
- A. Freemium: 5 events/day free, unlimited paid (~$5–10/mo)
- B. All-access: flat monthly subscription (~$8/mo)
- C. Pay-per-use: credits model

---

## Infrastructure — CI/CD (P0)

**Current:** Manual deploy via `make deploy` (SSH + git pull + docker compose up).

**Target:** Auto-deploy on `git push master`.

```yaml
# .github/workflows/deploy.yml
on: push
  branches: [master]
jobs:
  build:
    - docker build + push to ghcr.io
  deploy:
    - SSH to server: git pull + docker compose up -d
```

GitHub secrets needed:
```
DEPLOY_HOST=82.112.250.139
DEPLOY_USER=root
DEPLOY_KEY=<private_key_contents>
GHCR_TOKEN=<github_pat_with_packages_write>
```

---

## Infrastructure — Ollama reliability (P0)

**Problem:** After server reboot, Ollama is not on the `inkbytes_inkbytes-internal`
Docker network. Manual fix: `docker network connect inkbytes_inkbytes-internal ollama`.

**Fix options:**
1. **systemd service** — `ExecStartPost=docker network connect inkbytes_inkbytes-internal ollama`
2. **compose post-hook** — not natively supported in standalone compose
3. **Move Ollama into inkbytes compose** — cleanest but ties Ollama lifecycle to InkBytes stack

Recommendation: option 1 (systemd unit override).

---

## Gaps identified (2026-06-06/07)

| Gap | Severity | Notes |
|---|---|---|
| BBC geo-blocked on Hostinger IP | Medium | Consider a news API (NewsAPI.org) or RSS-only approach for BBC |
| Al Jazeera rate-limited | Medium | RSS feed approach would fix this |
| MinIO bucket needed for S3 archival | Low | Scraping works without it (RabbitMQ path unaffected) |
| Backoffice `/api/scrapesessions` 404 | Low | Legacy endpoint Messor still calls; harmless (Curator session path is via RabbitMQ) |
| Curator `embeddings_base_url` default wrong | Low | Default is `localhost:11434`, breaks after `migrate:fresh`. Fix: change to `http://ollama:11434/v1` |
| `public.scrape_sessions` no outlet-level breakdown | Low | `outlets` column is jsonb; Backoffice parse rate calc correct; future: normalize per-outlet rows |
| Model usage has no outlet_id / api_key_id | Low | Deferred in B5 — needs Curator to write these columns |
