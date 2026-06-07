# ADR-0009 — Per-outlet scraping sessions emitted immediately on completion

> *Status: accepted · Owner: Julian · Date: 2026-06-07*

## Context

Messor scraped outlets concurrently (up to 4 at once) and emitted a **single combined
session** only after ALL outlets finished.  With 22 active outlets this meant:

- Backoffice showed nothing for 20–30 minutes then received a wall of data at once.
- Curator's enrichment pipeline sat idle during the entire scrape, then got flooded.
- If Messor crashed mid-cycle, all completed outlet results were lost — nothing persisted.

## Decision

Emit **one `scrape.session.completed` message per outlet** immediately when that outlet
finishes, instead of one combined message at the end.

Session ID format: `session-{outlet_start_unix_ts}-{outlet_slug}`
(e.g. `session-1780800545-latimes`)

Each session message contains a single-element `outlets[]` array matching the existing
Curator schema — no schema change required.

The combined end-of-run summary was removed entirely.

## Consequences

**Positive:**
- Backoffice Scrape Results updates outlet-by-outlet in real time (visible progress).
- Curator begins enriching articles from fast outlets (apnews ~30s) while slow outlets
  (clarin, mileniomx) are still scraping — pipeline overlap.
- A Messor crash mid-cycle preserves all already-completed outlet sessions in the DB.
- Each outlet's success/failure is independently visible for monitoring.

**Negative:**
- Backoffice session list grows much faster (22 rows per cycle instead of 1).
- Session IDs are no longer a single stable run ID; correlation across outlets
  within a cycle requires matching the unix timestamp prefix.

## Implementation

`Messor/apps/scraper/services/scraper_service.py` — `execute_scraping_process()`:
replaces `list(generate_outlets_scraping_sessions())` + single emit with an inline
loop that emits per-outlet immediately on `yield`.

## Future

When RSS/Atom-first scraping is implemented (v2 Messor), the per-outlet model
remains valid — each feed parse is a discrete unit that can succeed or fail independently.
