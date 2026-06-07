# ADR-0009 — Per-outlet session emit (immediate, not combined)

> *Status: Accepted · Owner: Julian · Date: 2026-06-07*

## Context

Messor scrapes multiple outlets concurrently (4 threads) and previously emitted a
**single combined `scrape.session.completed` RabbitMQ event** only after ALL outlets
finished. With 22 active outlets this meant:

- Backoffice Scrape Results showed nothing for 25–30 minutes, then a wall of data
- Curator couldn't start enriching fast outlets (apnews, latimes ~30–90s) while
  slow outlets (clarin, mileniomx, theguardian ~2–5 min) were still running
- If the cycle crashed mid-way, all completed-outlet data was lost from the Backoffice
  (though articles were already published to RabbitMQ per-article)

## Decision

Emit one `scrape.session.completed` RabbitMQ event **immediately when each outlet's
scrape finishes**, before moving to the next outlet in the thread pool queue.

**Session ID format:** `session-{outlet_start_unix_ts}-{outlet_slug}`
e.g. `session-1780799245-apnews`

Each session has `total_outlets=1` and a single-element `outlets[]` array.

## Implementation

`ScraperService.execute_scraping_process()` iterates `generate_outlets_scraping_sessions()`
as a generator (not accumulated into a list). For each yielded `ScrapingSession`:

1. Extract outlet-level start/end times from `session.to_json()['data']`
2. Build `outlet_session_id = f"session-{int(outlet_start.timestamp())}-{slug}"`
3. Call `_emit_session_completed(outlet_session_id, outlet_start, outlet_end, duration, [outlet_stats])`
4. Log: `"Session emitted for {slug}: {N} new articles"`

Curator's `run_session_consumer` handles these identically to the old combined events —
the `ON CONFLICT (session_id) DO UPDATE` upsert on `public.scrape_sessions` is idempotent.

## Consequences

**Good:**
- Backoffice Scrape Results updates outlet-by-outlet in real time (~30–90s per outlet)
- Curator begins enriching fast-outlet articles while slower outlets are still scraping
- Mid-cycle crashes don't lose already-completed outlet sessions

**Watch out:**
- A mid-cycle deploy (force-recreate) can cause the same outlet to appear twice: the old
  container may have already emitted a session; the new container rescapes the same outlet.
  Timestamps differ → two session rows in DB. This is a one-time artifact, not a bug.
- Session IDs per outlet can collide if two outlets start at the exact same second AND
  have the same slug — impossible in practice (slugs are unique; concurrent outlets start
  within milliseconds of each other but slug disambiguates).

## Alternatives considered

**Keep combined emit at end of cycle** — rejected: 28-minute delay before any visibility.

**Emit combined + per-outlet** — rejected: double rows in `scrape_sessions`, confusing UI.

**Emit per-outlet via a new RabbitMQ exchange** — over-engineered; the existing
`scrape.session.completed` routing key and Curator consumer already handle it correctly.
