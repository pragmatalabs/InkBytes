# ADR-0012 — Stale Article Filter: 7-day freshness gate in Curator

> *Status: accepted · Sprint: 2 (not started) · Owner: Julian · Last updated: 2026-06-08*
>
> 🟡 **Design only — not started.** Decision is final; implementation deferred to Sprint 2.
> See checklist at the bottom of this file. Gate ships disabled (`max_article_age_days: 0`) and
> must be validated against the live corpus before enabling.

## Context

Messor harvests outlet homepages on a 4×/day schedule. Homepage content is not
strictly chronological: outlets re-feature older articles, syndicate wire copy
with original publication dates, or republish evergreen content. This means
Curator occasionally receives articles whose `published_at` is days or weeks in
the past. Processing them costs LLM budget and creates stub events that never
accumulate enough sources to be published — they simply sit in `events` as
permanent `draft` noise.

Two failure modes:

1. **New orphan event from old article**: The article doesn't match any active
   cluster (nothing in the 48h `scraped_at` window overlaps), so it seeds a new
   event that will never receive a second source, burning ENRICH + EMBED costs.

2. **False cluster extension**: The article matches a cluster that concluded
   months ago, re-triggering synthesis and potentially updating a published page
   with stale context.

The existing `scraper.timestamp: 2880` config in Messor (`env.yaml`) was
designed to address this but was **never implemented** (noted in contracts.md §4).

## Decision

Implement a **7-day freshness gate in Curator's `_handle_event()` ingestion
path**, not in Messor.

### Placement: Curator, not Messor

The boundary is defined by ADR-0005: Messor's job is faithful harvesting.
Content-quality rules — including whether an article is too old to add value —
are Curator's responsibility.

More importantly, the gate cannot be a simple age check without context:
an article with `published_at = 10 days ago` is noise if it has no matching
cluster, but it is **valid signal** if it extends an existing active event
(e.g., a follow-up on a story first reported 9 days ago that is still
generating coverage). Curator has the cluster knowledge to make this
distinction; Messor does not.

### Gate logic (pseudocode)

```python
# In application.py _handle_event(), after upsert_article_raw()

if article.published_at is not None and config.max_article_age_days > 0:
    age_days = (now_utc - article.published_at).total_seconds() / 86400
    if age_days > config.max_article_age_days:          # default: 7
        # Cheap cluster probe: does an active event exist for this article?
        # Active = has scraped_at candidates within the 48h clustering window.
        # If the probe finds a candidate → allow through.
        # If no candidate → this would seed a new stale event → drop.
        candidate = await self.db.find_nearest_active_event(
            embedding=None,          # embed first, then check — or use title match
            language=article.language,
            window_hours=48,
        )
        if candidate is None:
            logger.info(
                "DROP stale article %s outlet=%s age=%.1fd (no active cluster)",
                article.id, article.outlet_id, age_days,
            )
            return   # ack RabbitMQ message, no ENRICH / EMBED / CLUSTER
```

**Note on the probe**: For v1, running EMBED before the probe is acceptable
(embedding is cheap vs. ENRICH). A faster v2 could use a title-only TF-IDF
check against recent event headlines. The exact probe implementation is left to
the implementation sprint.

### New configuration keys

`core/config.py` (Pydantic model, with DB hot-reload via `curator_settings`):
```python
max_article_age_days: int = 7    # 0 = gate disabled
```

The gate is disabled by default until the implementation sprint validates it
against the live article corpus.

## Consequences

- ENRICH + EMBED costs drop for outlets that re-feature old content
  (e.g., infobae syndication, wire copy re-runs)
- Risk: if `published_at` extraction by newspaper3k is wrong (e.g., returns
  a page-modification date rather than original publish date), valid fresh
  articles could be incorrectly dropped. Mitigation: gate is disabled by
  default; enable via Backoffice settings once validated.
- Messor `scraper.timestamp: 2880` should be removed when this ADR is
  implemented to avoid documentation confusion.
- `Messor/docs/contracts.md` §4 "Freshness Window Filter" note should be
  updated to point here.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Filter in Messor by `published_at` age before publishing to RabbitMQ | Messor can't distinguish "old orphan" from "old article, live story" |
| Filter in Messor with a Curator API call to check active clusters | Creates tight coupling across the Messor/Curator boundary (ADR-0005) |
| Hard cap: never process article if `published_at` is missing | `published_at` is nullable; many valid fresh wire articles omit it; dropping them degrades coverage |
| Use `scraped_at` instead of `published_at` for the age check | `scraped_at` is always fresh (Messor stamps it now); this would let old articles through as long as Messor scraped them recently — the wrong invariant |

## Implementation checklist (Sprint 2)

- [ ] `core/config.py`: add `max_article_age_days: int = 0` (disabled by default)
- [ ] `core/application.py`: add gate after `upsert_article_raw()`
- [ ] `services/database_service.py`: add `find_nearest_active_event()` probe
- [ ] `Messor/apps/scraper/env.yaml`: remove deprecated `scraper.timestamp`
- [ ] `Messor/docs/contracts.md`: update §4 to reference this ADR
- [ ] Validation: run `--reenrich-missing` on a snapshot where gate is enabled;
      compare drop rate vs. false-drop rate against ground truth
