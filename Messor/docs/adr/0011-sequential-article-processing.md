# ADR-0011 — Sequential article processing: drop inner thread pool

> *Status: Accepted · Owner: Julian · Date: 2026-06-07*

## Context

Messor OOM-killed twice (exit code 137) while processing listindiario, consuming
6.27 GB (hitting the 6 GB `mem_limit`). Root-cause analysis via `dmesg` and code
inspection identified three compounding problems:

### Problem 1 — nested ThreadPoolExecutor holds all Article objects alive

The inner `ThreadPoolExecutor(max_workers=2)` receives ALL 150 article futures at once
via a list comprehension:

```python
results = [executor.submit(scrape_outlet_article, article, name) for article in articles]
```

Python's `concurrent.futures._WorkItem` stores `fn`, `args`, `kwargs`. While it clears
these after running in some Python versions, the `results` list itself keeps all 150
`Future` objects alive until the `as_completed()` loop finishes. Combined with lxml
retaining the HTML tree on each `newspaper.Article` after parse, this accumulates
hundreds of MB per outlet.

### Problem 2 — lxml cyclic garbage accumulates faster than Python's GC runs

`article.parse()` via lxml creates ~50,000+ Python objects per article with
parent-child circular references. Python's generational GC only runs when the
generation-0 threshold (700 objects) is exceeded — it cannot keep up with
50,000 new lxml nodes per article × 150 articles. The result: lxml trees pile up in
the Python heap, and the memory allocator does not return pages to the OS even after
GC (fragmentation).

Measured accumulation: ~2 GB of lxml garbage per outlet before the OS reclaims it.

### Problem 3 — `paper` object stays alive for the entire outlet's processing

`paper = self.newspaper.build(outlet)` holds all category-page HTMLs in memory
(10–50 category pages × 300 KB = 15 MB per outlet). The `paper` object is not freed
until `scrape_news_outlet()` returns — i.e., after all 150 articles are processed.

### Combined peak RAM at worst case (2 outlets, late cycle)

```
2 × paper objects (category HTMLs)           =   30 MB
2 × 150 futures × lxml HTML (if _WorkItem
      doesn't clear args promptly)           =  600 MB
2 × 150 parses × lxml fragmentation         = ~2 GB
Python heap fragmentation multiplier         = ~3 GB
────────────────────────────────────────────────────
                                              ~6 GB → OOM ✓
```

The article **cap** (200 → 150) delayed the OOM but did not fix it. At 150 articles
the peak is ~5.5 GB — still above 6 GB at late cycle when Python's heap is fragmented
from prior outlets.

## Decision

Replace the nested `ThreadPoolExecutor` + futures pattern with three coordinated changes:

### Layer 1 — Sequential article processing (drop inner pool)

Process articles one at a time within each outlet thread. The outer pool
(`max_threads=2` outlet threads) already provides meaningful concurrency — two outlets
run simultaneously. Within each outlet, processing articles sequentially:

- Keeps at most **1 article's HTML in memory at a time** per outlet thread
- Eliminates the "150 futures in results list" reference problem
- Eliminates the nested-pool complexity entirely

Throughput impact: minimal. Each article download is 200ms–2s (network I/O-bound).
Sequential throughput ≈ parallel throughput at `max_workers=2` because the server
rate-limits concurrent requests from the same IP anyway.

### Layer 2 — Explicit HTML cleanup + forced GC every 20 articles

After `create_article_record()` extracts the data we need, explicitly nullify the
newspaper.Article's heavy fields:

```python
np_article.html = None
np_article.clean_doc = None
np_article.clean_top_node = None
```

Call `gc.collect()` every 20 articles to force CPython to collect lxml circular refs
before they accumulate.

### Layer 3 — URL-based pre-dedup (skip download for known articles)

Article IDs are `uuid3(NAMESPACE_URL, article.url)` — deterministic from URL alone.
Before the scraping loop starts, load all article URLs from prior staging files into
a `Set[str]`. Then for each `newspaper.Article` (which has `.url` available before
any download):

```python
if np_article.url in known_urls:
    # duplicate — skip entirely, no HTTP request
    continue
```

In mature cycles, 70–90% of articles are duplicates. Pre-filtering by URL eliminates
their downloads entirely, reducing both memory and bandwidth by 5–7×.

Replaces: `check_article_exists_in_all_scrapes()` (which read entire staging JSON files
for every article). The URL set is loaded once (O(N_files) reads) instead of once per
article (O(N_articles × N_files) reads).

**Trade-off:** Content-updated articles (same URL, changed text) are no longer
re-published. Acceptable for news: articles are rarely substantially updated after
initial publication. Can be restored by a periodic "re-check known URLs" pass.

## Implementation

### `staging_store.py` — new function

```python
def load_known_article_urls(scrapes_dir: str, outlet_name: str) -> set[str]:
    """Load all article URLs from prior staging files for this outlet.
    Called once per outlet at cycle start; replaces per-article file reads."""
```

### `scraper.py` — changes

- `scrape_outlet()`: remove `num_workers` / inner `ThreadPoolExecutor`
- `NewsScraper.scrape_news_outlet()`: load `known_urls` set; call `del paper` after
  extracting article list to free category HTMLs ASAP; call new sequential loop
- `NewsScraper.process_outlet_articles()`: replace `as_completed(futures)` with
  sequential loop; URL pre-dedup; explicit cleanup; `gc.collect()` every 20
- `scrape_outlet_article()`: add explicit HTML cleanup after `create_article_record()`

### `scraper_service.py`

Remove `article_workers_per_outlet` — no longer relevant.
`scrape_outlet()` no longer accepts `num_workers`.

## Memory model after this change

| Source | Before | After |
|---|---|---|
| Article HTML in memory | 150 futures × 2 MB = **300 MB/outlet** | 1 × 2 MB = **2 MB/outlet** |
| lxml garbage | ~2 GB (150 parses, no forced GC) | ~20 MB (gc every 20) |
| Staging file dedup reads | 750 KB × N_files × 150 articles | **Set lookup O(1)**, loaded once |
| Peak RAM (2 outlets, late cycle) | **6+ GB → OOM** | **~250 MB** |

## Article cap status

With this change, `MAX_ARTICLES_PER_OUTLET` is a throughput/freshness control, not a
memory safety control. It can be raised back to 300–500 articles without OOM risk.
For now, 150 is kept pending one full cycle observation.

## Alternatives considered

**Increase `mem_limit` beyond 6 GB** — rejected: the Hostinger VPS has 15 GB shared
with Ollama and other services. There is no safe headroom. Treating memory as elastic
invites future regressions.

**Reduce `max_threads` further (1 outlet at a time)** — rejected: halves throughput
unnecessarily. Layer 1 fixes the root cause; `max_threads=2` is fine.

**`memoize_articles=True`** — rejected: this caches parsed articles in newspaper3k's
module-level dict indefinitely; it would make memory worse, not better.

**Switch to async I/O (httpx + trafilatura) now** — the correct long-term fix
(roadmap Sprint 2), but requires replacing newspaper3k entirely. Layers 1-3 are
surgical changes with low risk; they buy time for the async migration.
