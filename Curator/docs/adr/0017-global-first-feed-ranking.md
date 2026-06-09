> *Status: v1 · Owner: Curator · Last updated: 2026-06-09*

# ADR-0017 — Global-first feed ranking via `has_global_outlet` freshness bonus

## Status

Accepted

## Context

InkBytes' stated mission is global-first news. The reader should see AP/Reuters/CNN/BBC
stories at the top of the feed, with regional (LATAM, EU local) stories below — unless the
regional stories are genuinely more recent.

**The problem before this ADR:**

The `/events` API ordered by `p.freshness_at DESC NULLS LAST`, where `freshness_at =
max(scraped_at)` for the event. Messor's harvester scrapes outlets in a fixed sequence;
regional LATAM outlets (Heraldo, Listín Diario, La República) happen to be scraped toward
the end of each 120-minute cycle. Their events therefore have systematically *newer*
`freshness_at` values than CNN/AP/BBC events from the same cycle — even when the global
stories are more significant.

The existing client-side `importance()` sort in `feed-client.tsx` added
`source_count * 1000 ms` to freshness. With typical events having 2–5 sources, this added
2–5 seconds — swamped by millisecond differences between `freshness_at` values. It was
effectively a no-op.

**Result:** the InkBytes feed regularly displayed "latest news from Mexico / Dominican
Republic" rather than "top global events."

## Decision

Add a **6-hour freshness bonus** to events that have at least one article from a
`global`-region outlet (AP, Reuters, BBC, CNN, NPR, El País, Le Monde, Der Spiegel, etc.).

### Signal: `outlets.region = 'global'`

`outlets.region` is already managed in `Messor/apps/platform/config/regions.php` (the
single source of truth for region codes). Outlets configured with `region = 'global'` are
the authoritative international wire services and flagship broadcasters.

### Implementation: LATERAL join in `/events` query

A `LEFT JOIN LATERAL` subquery computes `has_global_outlet` once per event row using an
`EXISTS` check against `articles.event_id` (FK-indexed) and `outlets.region` (indexed).
The flag is exposed in the SELECT and used in ORDER BY without duplication:

```sql
LEFT JOIN LATERAL (
    SELECT EXISTS (
        SELECT 1
          FROM articles a_gf
          JOIN outlets o_gf ON o_gf.id = a_gf.outlet_id
         WHERE a_gf.event_id = e.id
           AND o_gf.region = 'global'
    ) AS has_global_outlet
) gflag ON true
```

ORDER BY expression:

```sql
ORDER BY (
    p.freshness_at
    + CASE WHEN gflag.has_global_outlet
          THEN INTERVAL '6 hours'
          ELSE INTERVAL '0'
      END
) DESC NULLS LAST
```

### Why 6 hours?

- InkBytes runs 4–12 harvest cycles per day; each cycle is ~120 minutes.
- A 6-hour bonus protects a global event across **3 full cycles** before a purely-regional
  story at identical `freshness_at` can overtake it.
- It is not a hard tier (all globals before all locals) — a regional story from 7+ hours
  ago still falls below a fresh regional story, and a global story from 20 hours ago
  eventually falls below a regional story from 10 hours ago. The feed remains time-bounded.
- The constant is easy to tune: raise to 8h if regional stories still break through too
  early; drop to 3h if global dominance becomes too aggressive. A future improvement: make
  it configurable via a `curator_settings` DB table.

### `has_global_outlet` exposed to Reader

The `has_global_outlet` boolean is included in the `/events` response so the Reader can:

1. Replicate the same sort order client-side (used for local re-sorting, e.g. after
   infinite-scroll appends).
2. Render a "Regional" section divider that makes the layout logic legible to users.

No DB migration required. `outlets.region` and `articles.outlet_id` already exist.

## Alternatives considered

**Hard two-tier ordering (all globals first, then all regionals)**
Would mean a 24-hour-old global story always ranks above a 30-minute-old regional story.
Too rigid — staleness still matters. Rejected.

**Client-side sort only**
The Reader is a thin presentation layer; it should not encode knowledge of which outlet
names are "global." Ranking is data-layer knowledge. Rejected. (The client-side
`importance()` is only kept as a mirror of the server sort for local append operations.)

**Score field on events table**
A static `score` column could be pre-computed and stored. But it would need re-computing
on every harvest cycle and would add a migration + backfill. The LATERAL join is
computed at query time and requires no schema change. Rejected (for now).

**Weighting by `source_count`**
The previous approach. `source_count * 1000 ms` is overwhelmed by millisecond differences
in `freshness_at`. No practical effect. Replaced by the 6h bonus.

## Consequences

- Global events consistently lead the feed during active cycles.
- Regional events still surface at the top when global stories are genuinely stale (>6h
  since last harvest contributing a global article).
- The Reader shows a "Regional" section divider that visually labels the tier boundary,
  improving user orientation without layout changes.
- `has_global_outlet` must be included in `/events` paginated responses — it is part of
  the public contract of `EventSummary`.

## Files changed

- `Curator/apps/curator/core/api_server.py` — LATERAL join + new ORDER BY
- `Reader/apps/web/lib/types.ts` — `has_global_outlet: boolean` on `EventSummary`
- `Reader/apps/web/app/feed-client.tsx` — `importance()` rewrite; "Regional" divider
- `Reader/docs/adr/0007-global-first-feed-ranking.md` — Reader-side record
