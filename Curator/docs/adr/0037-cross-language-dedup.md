# Curator ADR-0037 — Cross-language event dedup (collapse, not merge)

> *Status: **accepted** — implemented 2026-06-28 (committed, not deployed) · Owner: Julian · Date: 2026-06-28*

## Context

Clustering is per-language by design (`cluster.py` filters candidate neighbours +
the centroid query by `language`), so synthesis is single-language — an ES reader
gets a Spanish-written page, an EN reader an English one. The side effect: the same
real-world story produces a separate EN event and ES event, and the **"All" feed
shows both** (the "3 Venezuela earthquake entries" the user reported).

bge-m3 is multilingual, so the two are trivially detectable: measured on prod, EN/ES
versions of the same story sit at centroid distance **0.03–0.06**; distinct stories
are far above. (`events.centroid`, ADR-0031.)

## Decision — collapse + link (keep per-language pages)

Rejected **merging** (drop the language filter → one bilingual event): it would lose
the clean per-language synthesis (which is a feature) and re-architect clustering +
synthesis. Instead, keep the per-language events and:

1. **Tag, in the `/events` feed:** one self-join over the windowed published set
   (pgvector `<=>` in C — no centroid parsing in Python) tags each event:
   - `primary` = `false` when a richer same-story sibling in another language exists
     (richer = higher `source_count`, id tiebreak);
   - `also_languages` = `{ "<lang>": "<page_id>" }` for each other-language sibling
     (the richest per language).
   Gated on the lifecycle window so the self-join stays bounded. Threshold
   `_CROSSLANG_DUP_DIST = 0.12`. Only different-language events are grouped (same-
   language near-duplicates are a separate clustering-recall concern, untouched).

2. **Collapse in the Reader "All" view:** show only `primary` events → one card per
   story (the richer-language version), with "also EN/ES" chips linking to the
   sibling page. The **EN/ES tabs are unchanged** — they filter by language and show
   every event of that language, so switching tabs never loses a story.

## Consequences

- "All" feed de-duplicated; per-language pages preserved; a one-tap path to the
  other language. No clustering/synthesis change, low risk.
- Cost: one extra bounded self-join per uncached feed request (feed is `max-age=30`).
  If it ever gets hot, precompute a `dup_group` at cluster time.
- Does **not** fix same-language fragmentation (two ES events for one story) — that's
  a clustering-recall item. The "All" view still collapses such an ES event if it has
  a richer cross-language sibling.
- Reader event page does not yet show the cross-language link (feed-card only); a
  later enhancement could add it via a sibling lookup in `/events/{id}`.
