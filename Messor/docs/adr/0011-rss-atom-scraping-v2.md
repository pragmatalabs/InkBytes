# ADR-0011 — RSS/Atom-first scraping architecture (v2, deferred)

> *Status: proposed · Owner: Julian · Date: 2026-06-07 · Target: post-v0*

## Context

newspaper3k homepage crawling (current v1) has fundamental problems at production scale:
- 50–150 HTTP requests per outlet (homepage + categories + articles)
- Hangs on `download_categories()` — no timeout, blocks threads indefinitely
- Returns 500–1,500 URLs including navigation, ads, and archive content
- ~70–90% duplicates per cycle; genuine new articles are a small fraction
- Fails on JS-rendered sites (Al Jazeera, Wired) and paywalls (BBC, Bloomberg)
- Unmaintained since 2020; doesn't handle modern HTML structures

## Decision

Defer to post-v0. **Design is approved; implementation blocked on v0 stability.**

### v2 architecture

```
outlet.feed_url (from DB or auto-discovered)
  → feedparser.parse(feed_url)          # 1 HTTP req, ~200ms, pure XML
  → entries[:200]                        # already newest-first by outlet
  → filter: published within last 48h   # skip stale
  → dedup against history (content hash)
  → trafilatura.fetch_url(url) ×N       # parallel, 30s timeout
  → trafilatura.extract(html)           # main content extraction
```

### Feed discovery algorithm

```python
FEED_PATHS = ['/feed', '/feed.xml', '/rss', '/rss.xml', '/atom.xml',
              '/atom', '/news/rss', '/rss/news.xml', '/feed/rss2']

def discover_feed(outlet_url):
    for path in FEED_PATHS:
        r = requests.head(outlet_url + path, timeout=5)
        if r.ok and 'xml' in r.headers.get('content-type', ''):
            return outlet_url + path
    # fallback: parse homepage for <link rel="alternate" type="rss+xml">
    html = requests.get(outlet_url, timeout=15).text
    soup = BeautifulSoup(html)
    for link in soup.find_all('link', rel='alternate'):
        if 'rss' in link.get('type','') or 'atom' in link.get('type',''):
            return urljoin(outlet_url, link['href'])
    return None  # fall back to newspaper3k
```

### Known feed URLs for current outlets

| Outlet | Feed URL |
|---|---|
| CNN | https://rss.cnn.com/rss/edition.rss |
| AP News | https://apnews.com/rss |
| The Guardian | https://www.theguardian.com/world/rss |
| LA Times | https://www.latimes.com/world-nation/rss2.0.xml |
| NPR | https://feeds.npr.org/1001/rss.xml |
| TechCrunch | https://techcrunch.com/feed/ |
| CNBC | https://feeds.feedburner.com/cnbc/technology |
| Infobae | https://www.infobae.com/feeds/rss/ |
| Clarin | https://www.clarin.com/rss/lo-ultimo/ |
| El Tiempo CO | https://www.eltiempo.com/rss/portada.xml |
| Semana | https://www.semana.com/rss/ |
| Al Jazeera | https://www.aljazeera.com/xml/rss/all.xml |

### DB schema change required

```sql
ALTER TABLE public.outlets ADD COLUMN feed_url text;
```

Backoffice: editable `feed_url` field per outlet. If set, use directly.
If null, auto-discover on first scrape and cache to DB.

## Expected improvements

| Metric | v1 (now) | v2 (RSS) |
|---|---|---|
| HTTP requests / outlet | 50–150 | 1 + N articles |
| Time / outlet | 30–90s | 5–15s |
| Full cycle (22 outlets) | 6–15 min | 1–3 min |
| Duplicates / cycle | 70–90% | 5–20% |
| Thread hangs | Yes | No (pure XML parse) |
| Memory / cycle | ~2.2 GB peak | ~300 MB peak |

## Implementation plan (3 phases)

1. **Phase 1** — Add `feed_url` column to `public.outlets`; Backoffice edit field.
   Auto-discover and cache on first scrape (one-time per outlet). No scraper change yet.

2. **Phase 2** — `FeedScraper` class: `feedparser.parse()` → filter → `trafilatura.fetch_url()`.
   Run alongside existing `NewsScraper` with a feature flag per outlet.

3. **Phase 3** — Make FeedScraper the default; NewsScraper as fallback for outlets
   without discoverable feeds. Remove newspaper3k dependency.

## Dependencies

```
feedparser>=6.0.11      # RSS/Atom parsing
trafilatura>=1.9.0      # content extraction (replaces newspaper3k article.parse())
```

Both are in active maintenance and have no transitive conflicts with current deps.
