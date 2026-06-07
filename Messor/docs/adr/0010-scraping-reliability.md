# ADR-0010 — Messor scraping reliability: cap, shuffle, timeout, delay

> *Status: accepted · Owner: Julian · Date: 2026-06-07*

## Context

After deploying to Hostinger VPS, Messor exhibited several stability problems:

1. **OOM crash every ~2 min** — 10 concurrent threads × newspaper3k peaked at 2.2 GB,
   exceeding the 1.5 GB container limit → Docker SIGKILL (exit 0, not OOMKilled).
2. **Crash-restart burst** — `restart: unless-stopped` + no startup delay → each restart
   immediately fired a full 22-outlet cycle → 4 restarts = 4 concurrent sweeps.
3. **Thread hangs** — `newspaper3k.build()` has no timeout; one stalled outlet held a
   thread indefinitely (confirmed: 4-hour hang, 2338% CPU, 4 GB RAM).
4. **Alphabetical batch bias** — with 4 concurrent outlet threads, outlets A–D always
   ran in batch 1 together. Al Jazeera + Acento + APNews scraped simultaneously every
   cycle, triggering rate limits (AJ dropped from 60% → 1.4% on back-to-back runs).
5. **Article volume** — newspaper3k returned 500–1,500 URLs per outlet including
   navigation links, old archives, and category pages. Most were duplicates.

## Decisions

### D1 — 200-article cap per outlet

`process_found_articles()` slices `paper.articles[:200]` before submitting to threads.
newspaper3k returns articles in homepage order (newest first), so the top 200 = the
freshest editorial headlines.

```python
MAX_ARTICLES_PER_OUTLET = 200
articles = paper.articles[:MAX_ARTICLES_PER_OUTLET]
```

**Effect:** clarin 1,113 → 200, mileniomx 554 → 200. Cycle time: 28 min → ~6 min.

### D2 — Shuffle outlet order each cycle

`random.shuffle(outlets)` before the concurrent pool starts. Prevents the same outlets
from always running in batch 1.

**Effect:** Al Jazeera no longer guaranteed to run concurrently with APNews and Acento.

### D3 — Startup delay (MESSOR_STARTUP_DELAY_MINUTES=5)

5-minute sleep before the first scheduled scrape cycle. FastAPI comes up immediately;
only the scraping holds. Crash-restart loop of N restarts → at most one cycle per 5
minutes instead of N simultaneous cycles.

### D4 — Per-outlet 5-minute hard timeout

`future.result(timeout=300)` in `generate_outlets_scraping_sessions()`. If any outlet's
`scrape_outlet()` call hangs beyond 5 minutes, it is skipped and logged. The overall
pool also has a `as_completed(timeout=outlets×300)` guard.

### D5 — Split outlet vs article thread counts

The outer ThreadPoolExecutor (outlet level) uses `max_threads` (4).
The inner ThreadPoolExecutor (article level within each outlet) is fixed at 2.
Max concurrent downloads: 4 × 2 = 8 (was 4 × 4 = 16 → OOM pressure).

### D6 — Exception handling broadened

`pre_process_article()` and `scrape_outlet_article()` previously only caught `ValueError`.
All exceptions are now caught and logged as WARNING, preventing silent thread death.

### D7 — request_timeout=30, MAX_REDIRECTS=10

Set in `NewsPaper.build()` config. Prevents stalled HTTP connections from blocking
article threads and limits BBC-style redirect loops from consuming slots.

### D8 — 4×/day schedule (360-minute interval)

Reduced from 60 min to 360 min (6-hour intervals). Manual trigger from Backoffice
remains available at any time. Rationale: news outlets refresh their top stories
every 4–6 hours; hourly scraping produces ~90% duplicates after the first cycle.

## Memory budget

| Container | Limit | Peak observed |
|---|---|---|
| inkbytes-messor | 6 GB | ~2.2 GB (BBC+large outlets) |
| ollama (bge-m3) | 3 GB | 1.6 GB |
| everything else | ~2 GB total | < 1 GB total |

Total reserved: ~8 GB of 16 GB available.

## Alternatives considered

- **Increase max_threads beyond 4** — rejected; multiplies peak memory linearly.
- **Per-outlet memory limit** — not enforceable within a single Python process.
- **Replace newspaper3k with trafilatura** — deferred to v2 RSS-first architecture (ADR-0011).
- **Kubernetes** — rejected; single VPS is sufficient for v0 scale.

## Open issues

- Messor healthcheck (`curl /api/outlets`) fails during the startup delay window
  (FastAPI up but Curator API may not yet respond). Not critical — `restart: unless-stopped`
  won't trigger because the process itself is healthy.
- Al Jazeera disabled in DB due to persistent rate-limiting. Re-evaluate with RSS feed.
