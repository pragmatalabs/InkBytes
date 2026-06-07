# ADR-0010 — Scraping reliability: cap, shuffle, timeout, startup delay

> *Status: Accepted · Owner: Julian · Date: 2026-06-07*

## Context

After deploying to Hostinger VPS, the Messor container exhibited several reliability
problems observed over 2026-06-06/07:

1. **Crash-restart loop** — container OOM-killed every ~2 minutes when BBC + Al Jazeera
   + AP News ran concurrently. Docker auto-restarted, each restart immediately fired
   a new full 22-outlet sweep → cascading resource exhaustion.

2. **Thread freeze** — newspaper3k's `download_categories()` (called in `generate_paper()`)
   hangs indefinitely on slow/blocked outlets (e.g. BBC redirect loop). With 4 outlet
   threads × 4 article threads = 16 concurrent downloads, 4 hung connections = complete
   thread pool exhaustion → cycle runs for 4+ hours.

3. **Alphabetical bias** — outlets loaded alphabetically: `acentodr, aljazeera, apnews, clarin`
   always ran in the same concurrent batch. Al Jazeera + Acento hammered together every
   cycle, triggering rate-limits (parse success dropped from 60% to 1.4% on back-to-back runs).

4. **Article volume** — newspaper3k returned 500–1,500 article URLs per outlet (entire
   homepage + all category pages). clarin: 1,184 · mileniomx: 554 · cnbc: 1,397.
   Most were duplicates or archive content. Per-cycle RAM peak: 4 GB for Messor alone.

5. **Only `ValueError` caught** — network errors (`Timeout`, `ConnectionError`,
   `TooManyRedirects`) in `pre_process_article` propagated silently as unlogged failures.

6. **`meta_lang` guard dropped valid articles** — `pre_process_article` returned `None` when
   `article.meta_lang` was empty or wrong. Common on Spanish outlets where newspaper3k
   misdetects language. `langdetect` already runs downstream in `ArticleBuilder`.

## Decisions

### D1 — 200-article cap per outlet (`MAX_ARTICLES_PER_OUTLET = 200`)

`process_found_articles()` slices `paper.articles[:200]` before submitting to the thread
pool. newspaper3k returns articles in homepage order (newest/most-prominent first), so
the top 200 = the freshest editorial picks. Logs "capped at 200/1184" when active.

**Effect:** Per-cycle RAM peak: 4 GB → ~2 GB · Cycle time: 28 min → 10–15 min.

### D2 — Random shuffle of outlet order each cycle

`random.shuffle(outlets)` in `execute_scraping_process()` before starting the thread pool.
Prevents the same 4 outlets always sharing a concurrent batch → avoids rate-limit pileups.

### D3 — 5-minute per-outlet hard timeout

`OUTLET_TIMEOUT_SECONDS = 300` in `ScraperService`. `future.result(timeout=300)` in
`generate_outlets_scraping_sessions()`. If newspaper3k hangs on an outlet's homepage crawl,
the wait is abandoned after 5 min (thread continues in background, but the slot is freed
for the next outlet). The overall pool has `as_completed(timeout=300 × n_outlets)` as a
backstop.

**Note:** `future.result(timeout=N)` stops WAITING; it does not kill the thread. Lingering
threads eventually die when the thread pool is garbage-collected at end of cycle. This is
acceptable — the pool is short-lived.

### D4 — 5-minute startup delay (`MESSOR_STARTUP_DELAY_MINUTES=5`)

Set via env var (compose) and read in `Application._run_scheduled_mode()`. The FastAPI
server (trigger endpoint) comes up immediately; only the first scheduled scrape is held
5 minutes. Prevents burst scraping when Docker auto-restarts Messor (crash-restart loop
= 4 restarts × full 22-outlet sweep starting immediately).

### D5 — 4×/day schedule (`MESSOR_SCHEDULE_INTERVAL_MINUTES=360`)

Reduced from every 60 min (24 cycles/day) to every 360 min (4 cycles/day). News outlets
update their homepages 4–6 times/day; hourly scraping mostly collected duplicates and
stressed the server unnecessarily. Manual trigger from Backoffice available anytime.

### D6 — Request timeout + catch all exceptions in newspaper3k layer

- `request_timeout: 30` and `MAX_REDIRECTS: 10` added to `NewsPaper.build()` config dict.
- `pre_process_article()` now catches `Exception` (not just `ValueError`) and logs
  `WARNING: Download/parse failed for {url}: {type}: {msg}`.
- `scrape_outlet_article()` same: catches `Exception`, logs `WARNING`.
- `NewsPaper.generate_paper()` same: catches `Exception` (was `ValueError`).
- **Removed `meta_lang` guard** from `pre_process_article()` — language detection
  is handled by `langdetect` in `ArticleBuilder.buildFromNewspaper3K()`.

### D7 — Split outlet-level vs article-level thread pools

`ScraperService.article_workers_per_outlet = 2` (fixed). `create_outlet_scraping_session()`
passes `num_workers=self.article_workers_per_outlet` (not `max_threads`).

**Before:** `max_threads=4` outlets × `max_threads=4` article workers = 16 concurrent downloads.
**After:** `max_threads=4` outlets × `2` article workers = 8 max concurrent downloads.

## Memory budget (Hostinger VPS, 15 GB total)

| Component | Reserved | Notes |
|---|---|---|
| Messor `mem_limit` | 6 GB | Was 1.5→3→6 GB; 4 GB peak during heavy scrape |
| Ollama `mem_limit` | 3 GB | Was 10 GB; bge-m3 peaks at 1.6 GB |
| Curator worker | 1 GB | Stable ~130 MB |
| Reader + Backoffice + Curator API | 1.5 GB total | Each 512 MB limit |
| OS + other services | ~3 GB | RabbitMQ ~150 MB, Postgres ~35 MB |

## Disabled outlets

The following outlets were disabled (`public.outlets.active = false`) based on 48h
parse success rate analysis:

| Outlet | 48h parse rate | Reason disabled |
|---|---|---|
| bbc | 14% (geo-blocked) | Redirect loop; Hostinger IP blocked |
| aljazeera | 18.8% → 1.4% | Rate-limited on back-to-back runs |
| bloomberg | 0% | Hard paywall |
| wsj | 0% | Hard paywall |
| reuters | 0% | Geo-blocked |
| theeconomist | 0% | Hard paywall |
| financialtimes | 44% → 0% | Soft paywall, archive content only |
| wired | 17% | JS-rendered, 0% on new articles |
| foxbusiness | 44% | Broken newspaper3k parsing |
| polifact | 0% on new | All new URLs fail to parse |
| animalpolitico | 0% | Broken |
| eldinerodr | 3.4% | Broken |

**Parse rate methodology:** `successful / (total - duplicates)` = parse success on
genuinely new articles (excluding duplicates which are correctly classified as "seen",
not "failed"). The Backoffice Scrape Results display was fixed to show this real rate.

## Future evolution

See `docs/roadmap.md §RSS/Atom-first harvesting` for the planned v2 architecture
using `feedparser` + `trafilatura` that eliminates most of these issues at the root.
