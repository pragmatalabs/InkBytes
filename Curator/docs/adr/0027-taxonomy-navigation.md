# Curator ADR-0027 — Taxonomy navigation (theme filter + topic trending + category)

> *Status: accepted · Owner: Julian · Date: 2026-06-12*

## Context

`articles.theme` (8 canonical values), `articles.topic` (free-text LLM story
labels), and `articles.article_category` (raw outlet sections) are all
~99% populated and the event rollup already *displays* the dominant theme/topic
per event. But nothing let a reader or operator *filter/navigate* by them — the
single-column indexes sat at 0–2 scans. Julian (2026-06-11): "category and
topic must be used." Decision: make all three navigable across three surfaces
(API → Reader → Backoffice).

## Decision — API foundation (6a, this ADR)

The shared dependency for the Reader (6b) and Backoffice (6c). In
`core/api_server.py`:

1. **`GET /events?theme=`** — filters to events whose majority-vote theme
   matches. The dominant-theme subquery was lifted into a `th` LATERAL join so
   it can be referenced in `WHERE`. Validated against the 8 canonical themes
   (`_VALID_THEMES`); an unknown value is **ignored** (returns the unfiltered
   feed) rather than returning `[]`, so a stale Reader chip never blanks the
   page.
2. **`GET /events?category=`** — matches events with ≥1 article carrying that
   raw outlet section (`article_category`). Ops/Backoffice oriented.
3. **`GET /events?topic=`** — matches events with ≥1 article carrying that
   topic label. Powers the trending drill-down.
4. **`GET /topics/trending?window_hours=48&limit=20`** — top topics by distinct
   published-event count then article volume, over a clamped 1h–7d window. Junk
   enrichment artifacts (error pages, generic outlet boilerplate) excluded via
   `_JUNK_TOPIC_PATTERNS` (`browser error`, `cnn breaking news%`, …).

All filters AND-combine; defaults (all None) preserve the exact prior behavior.

### Why theme is the filter facet but topic is not

`theme` is a clean 8-value enum → ideal filter. `topic` is free-text and
high-cardinality (e.g. "Pope Leo XIV Visit to Barcelona" vs "…to Madrid" vs
"…to Spain" are three labels for one story) with some junk → used for *labels*
and a *trending list*, not a filter facet. `article_category` is outlet-specific
vocabulary (inconsistent across outlets: "News", "Partidos de hoy", date
strings) → ops filter only, not reader-facing navigation.

## Verification (local, 1,099 published events, all 8 themes)

- `?theme=sports` → 116 events, 100% theme=sports; `?theme=bogus` → unfiltered.
- `?topic=Iran Missile Attack on Israel` → 8 on-topic events.
- `?category=News` → 180 events.
- `/topics/trending` → real stories ranked by coverage breadth, junk excluded.

## Surfaces (6b/6c, separate tasks)

- **6b Reader**: theme filter chips on the feed (`?theme=`, URL-reflected) +
  a "Trending" section from `/topics/trending`, each topic linking to
  `?topic=`.
- **6c Backoffice**: theme/category/topic filters on the events admin view.

## Consequences

- The idle taxonomy indexes (`idx_articles_theme`/`topic`/`category`) now back
  real query paths — they earn their keep (answers Julian's "don't drop them").
- Filtered `/events` adds a LATERAL theme join + up to two `EXISTS` subqueries;
  all index-backed, negligible at the 500-row cap.
- A future light cleanup of junk `topic` values during ENRICH would tighten
  trending further (deferred).
