# ADR-0043 — `pages.freshness_at` must be maintained on material attach, not only at synthesis

> *Status: v1 · Owner: Curator · Last updated: 2026-08-01*

## Context

The Reader feed cards display each event's age from `pages.freshness_at`, whose
documented definition is **`max(article.scraped_at)` over the event's articles**
(see the `freshness-at-use-scraped-at` rule and [ADR-0033]). Under ADR-0033 the
production feed (`GET /events`, `lifecycle_feed` ON) is **ordered by the material
clock** `events.last_material_update_at` and **displays** `pages.freshness_at`.

`pages.freshness_at` was written in exactly **one** place: `SynthesizeSkill`
(`skills/synthesize.py`), which computes
`freshness = max(scraped_at for the event's articles)` and upserts it into
`pages`. But re-synthesis of an already-published event is **throttled** (the
ADR-0035 re-synthesis watermark) — a fresh article can attach to a published
event, bump the material clock (`ClusterSkill` sets
`last_material_update_at = NOW()` on a material attach), and yet **never trigger
a page rewrite**. When that happens `pages.freshness_at` stays frozen at the last
synthesis time.

### Symptom (2026-08-01)

Julian reported "it's been 2 hours since the last news update." The pipeline was
healthy (0 × 402, publishing continuously, feed-lag by `freshness_at` order = 0.0 h).
But the **live feed order** (`last_material_update_at` DESC) surfaced evolving
events whose displayed `freshness_at` was hours—days stale:

| headline | `last_material_update_at` | stored `freshness_at` | **actual** `max(scraped_at)` |
|---|---|---|---|
| UN Security Council straw poll | 3 min ago | **45 h ago** | **7 min ago** |
| River Plate loses 1-0 | 5 min ago | **65 h ago** | **8 min ago** |
| UEFA/FIFA World Cup (20 src) | 3 min ago | **4.6 h ago** | **8 min ago** |

Of the top 50 events by material clock, **31 (62%)** displayed a `freshness_at`
older than 2 h while their newest article had been scraped **minutes** earlier.
The ranking was correct — these events genuinely gained fresh coverage — but the
**displayed age was frozen**, so the entire feed looked 1 h–days stale.

A `--reenrich-missing` backfill run earlier that day (re-clustering the morning's
articles after the DeepSeek-balance outage, see the `deepseek-cost-spike` note)
re-touched many old events and made the pre-existing drift vivid across the whole
top of the feed. But the bug bites **every** evolving event, backfill or not.

## Decision

`pages.freshness_at` is a **derived column** and must track its definition
continuously, independent of whether re-synthesis fires.

1. **Immediate data correction (no deploy):** recompute
   `pages.freshness_at = max(scraped_at)` for all published pages — realigns the
   column to its own definition. Display-only under `lifecycle_feed` (ordering is
   by the material clock, untouched). 5,371 rows corrected; top-of-feed display
   went from 45 h/65 h/23 h → 5–9 min.

2. **Durable fix (code):** on a **material** attach, `ClusterSkill` now calls
   `_touch_page_freshness(conn, event_id)`, which runs
   `UPDATE pages SET freshness_at = (SELECT MAX(scraped_at) FROM articles WHERE event_id=$1) WHERE event_id=$1 AND published_at IS NOT NULL`.
   Mirrors `synthesize.py`'s definition exactly; no-op for unpublished events.
   Wired into **both** attach paths (legacy single-linkage and the ADR-0031
   precision path).

### Why gate on `material` (not every attach)

A **tangential** re-mention joins the event but, per ADR-0033, must *not*
re-float it "as if it happened today" — it deliberately leaves the material clock
unchanged. Refreshing the displayed age off a tangential mention would resurrect
a dead story's timestamp. So `freshness_at` maintenance is gated on the same
`material` predicate that gates the material clock: a material attach refreshes
**both** ranking and display; a tangential attach refreshes **neither**.

## Consequences

- Evolving published events now show the age of their newest article as coverage
  arrives, between throttled re-syntheses — the lifecycle feed reads as fresh.
- One extra cheap `UPDATE` (indexed by `event_id`) per material attach to a
  published event. Negligible.
- `freshness_at` and `last_material_update_at` now move together on material
  attaches, as ADR-0033 always intended.

## Alternatives considered

- **Reader displays `last_material_update_at` instead of `freshness_at`.** Rejected:
  the material clock is a *ranking* signal (a tangential-free "re-float" time), not
  "when we last saw news" — and it would still need the ordering fix. `freshness_at`
  is the right display field; it was simply not being maintained.
- **Always re-synthesize on attach (drop the ADR-0035 watermark).** Rejected: that
  reintroduces the LLM cost/churn the watermark exists to prevent; freshness is a
  cheap SQL recompute that needs no model call.

## Rollback

Revert the two `_touch_page_freshness` call sites + the helper in
`skills/cluster.py`. The one-time data recompute needs no rollback (it only moved
`freshness_at` toward its definition). Behaviour is otherwise unchanged.
