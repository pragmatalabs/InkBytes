# ADR-0015 — 48-Hour Harvest Freshness Window

> *Status: accepted · Owner: Julián · Last updated: 2026-06-09*

## Context

The Reader was surfacing month-old (and older) stories as if they were fresh.
Investigation traced it to Messor's harvest, not the Reader:

1. **No freshness filter existed.** `scrape_outlet_article` extracts
   `publish_date`, but nothing ever gated on it — every article newspaper3k
   discovered was staged → published → enriched → clustered → paged.
2. **The head+tail slice actively harvested archives.** `_slice_outlet_articles`
   took the first 300 **and the last 300** discovered URLs. The "tail" was
   explicitly category-page depth — which is exactly where newspaper3k surfaces
   deep archive links.

Evidence from a single production harvest of **theguardian** (1 173 articles):

| Bucket | Count |
|---|---|
| 2026-06 (current) | 858 |
| 2026-05 | 172 |
| 2026-03 / 04 | 45 |
| 2012 – 2025 (long tail) | ~89 |
| null `publish_date` | 9 (0.8%) |

So ~27% of harvested articles were **not** from the current month, stretching
back to **2012**. Because Curator's `pages.freshness_at` was just changed to
`max(scraped_at)`, an April article scraped today gets `freshness_at = today`
and floats to the top of the feed — the visible bug.

Crucially, the same data shows `publish_date` is populated for **~99%** of
articles. A date filter is therefore an *exact* tool here, not a heuristic.

## Decision

### 1. Freshness gate — only articles published in the last 48 hours

`process_outlet_articles` now drops any parsed article that fails
`is_article_fresh(record, window_hours)`:

- Keep iff `publish_date >= now − window_hours` (default **48h**).
- **Strict** (decided 2026-06-09): a missing / unparseable `publish_date` is
  treated as stale and **dropped**. The null rate is ~1–3% and is uncorrelated
  with age, so the cost is small; the benefit is a hard guarantee that nothing
  undated slips through.
- A date beyond `now + 2 days` is dropped — newspaper3k sometimes lifts a date
  from the article *body* rather than the byline, which would otherwise sneak a
  stale piece past the lower bound.
- Comparison is naive-UTC; tz-aware dates are normalised first. A few hours of
  tz slop is irrelevant against a 48-hour window.

Window is configurable: `articles.freshness_window_hours` (defaults to 48 if
unset). Dropped count is logged per outlet as `stale-skip`.

### 2. Drop the archive tail — homepage-order head only

`_slice_outlet_articles` now returns `articles[:MAX_ARTICLES_PER_OUTLET]` (the
homepage-order head) and **drops the tail**. With the date gate doing the
precise freshness work, the cap is now just a per-outlet *download bound* on the
freshest-first head — it also stops us *downloading* ~300 mostly-stale tail
articles per outlet each cycle.

### 3. Scope — Messor only, history preserved

This changes **harvesting only**. Existing articles/events/pages in Curator are
left untouched (decided 2026-06-09: "history can remain"). No retention job, no
DB reset, no Curator change.

## Consequences

| | Before | After |
|---|---|---|
| theguardian articles staged/cycle | ~1 173 (back to 2012) | the ≤48h slice (low hundreds), 0 archive |
| Freshness rule | none | `publish_date ≥ now − 48h`, strict on undated |
| Per-outlet download | head 300 + tail 300 | head ≤300 only |
| Reader feed | month-old stories appear "fresh" | only genuinely recent stories enter |

### Risk — outlets with poor date extraction

Strict-on-undated assumes the ~99% date-population rate holds per outlet. An
outlet where newspaper3k fails to extract dates (more likely on some LATAM/ES
sites) would be over-filtered and under-harvest. **Mitigation:** the per-outlet
`stale-skip` log line makes this visible immediately after deploy — watch for
outlets whose `stale-skip` dwarfs `new`. If one shows up, options are: relax to
lenient-on-null for that outlet, widen the window, or improve date extraction.

### Interaction with dedup (ADR-0011/0012/0014)

The gate runs *after* URL pre-dedup and *after* download/parse (publish_date is
only known post-parse). Stale articles are dropped before staging, so they never
enter a staging file and are never published — and being absent from staging,
they are not added to the URL-dedup set, so a later cycle re-evaluates them
(cheap: they get URL-skipped only if a *fresh* sibling staged the same URL). No
conflict with the per-run staging files of ADR-0014.

## Alternatives considered

### "Top 200 by position" (the original proposal)

Cap each outlet at its first 200 discovered URLs. Rejected as the *primary*
rule: newspaper3k's order is discovery order, not date order, so position-200
can still include pinned/archive links, **and** it would cut genuinely-fresh
stories when an outlet has >200 in 48h. The date gate is semantically exact;
the head cap is kept only as a download bound.

### Filter by URL date pattern before download (e.g. `/2026/06/`)

Cheaper (no download for stale URLs), but outlet-specific and fragile — many
outlets use non-dated slugs. Deferred; the post-parse gate is universal and the
tail-drop already removes the bulk of stale downloads.

### Lenient on null dates

Keep undated articles (they're usually homepage-fresh). Rejected per the
2026-06-09 decision in favour of a hard freshness guarantee; revisit per-outlet
if `stale-skip` reveals a high-null outlet.
