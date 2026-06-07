# ADR-0011 — IllustrateSkill: Scrapling-based media rail (Phase 2)

> *Status: accepted · Owner: julian · Last updated: 2026-06-07*

## Context

Published event pages currently display either the `lead_image` extracted
passively by Messor from the article's `og:image` tag, or nothing.
This gives incomplete visual coverage: events with many text-only sources
(wire services, financial outlets) show a grey placeholder.

Phase 2 adds an active media-search step that runs after synthesis and
populates a `pages.media_rail` JSONB array with up to 6 scored
image/video candidates.

## Decision

### Skill: `IllustrateSkill` (`skills/illustrate.py`)

Searches two sources concurrently after synthesis completes:

| Source | Fetcher | Rationale |
|--------|---------|-----------|
| YouTube | `DynamicFetcher` (Playwright) | Search results are JS-rendered; `httpx` gets an empty SPA shell |
| Bing Images | `StealthyFetcher` (Camoufox) | Bot-detection blocks plain requests; Camoufox spoofs a real browser fingerprint |

### Scoring function (0–1)

Each candidate is scored on three additive axes:

| Axis | Weight | Signal |
|------|--------|--------|
| Source credibility | 0–0.40 | Domain allowlist: Reuters/AP/BBC = 0.36-0.38, YouTube = 0.40, unknown = 0.10 |
| Image resolution | 0–0.35 | Pixel area normalised to 1920×1080; capped at 0.35 |
| Recency | 0–0.25 | Exponential decay, half-life = 48 h; `None` date → 0 |

Maximum possible score = 1.0. In practice a 1920×1080 image from Reuters
published 1 hour ago scores ≈ 0.38 + 0.35 + 0.25 = 0.98.

### Pipeline integration

IllustrateSkill runs as a **fire-and-forget `asyncio.create_task`** spawned
immediately after synthesis completes (only when synthesis actually wrote a
new page, i.e. `PageV1 is not None`).  This ensures:

1. The RabbitMQ message is ACKed without waiting for browser fetches (~5–25 s).
2. A failed illustration never rolls back or retries synthesis.
3. The media rail is asynchronously enriched while the Reader already shows
   the text brief.

### Storage: `pages.media_rail JSONB` (migration 009)

Each element shape:
```json
{
  "url":           "https://...",
  "thumb_url":     "https://...",
  "type":          "image|video",
  "title":         "...",
  "source_domain": "reuters.com",
  "published_at":  "2026-06-07T14:00:00+00:00",
  "width":         1920,
  "height":        1080,
  "score":         0.73
}
```

Defaults to `[]` so the Reader can iterate without null-checks.
Re-synthesis overwrites the rail (write_media_rail is idempotent).

## Alternatives considered

**Google Images** — ToS prohibits scraping; no reliable public API within
our budget tier. Bing Images is more permissive and Camoufox bypasses its
bot detection.

**YouTube Data API v3** — Quota is 10,000 units/day; each search costs 100
units → 100 searches/day cap. With 413 pages live and growing, this is
insufficient. Scrapling bypasses the quota entirely.

**httpx direct requests** — YouTube returns an SPA shell without JS
execution. Bing Images blocks non-browser user agents. Both require a
headless browser; scrapling abstracts this cleanly.

**LangGraph / CrewAI agent** — Rejected (ADR-0001): we don't need a
multi-agent framework for a single-step scrape + score operation.

## Consequences

- Docker image grows by ~300–400 MB (Chromium + Camoufox binaries).
- Each IllustrateSkill call adds 5–30 s of background work (never on
  the critical path — fire-and-forget).
- Events synthesized before this migration deploy will have `media_rail = []`
  until re-synthesized (or a future backfill script runs).
- `scrapling[fetchers]>=0.2.9` added to `requirements.txt`.
- Migration 009 runs on next Curator startup.

## Open items

- [ ] Backfill script: run IllustrateSkill on all existing published pages
      with `media_rail = '[]'`
- [ ] Reader UI: wire `media_rail` into event page hero / image carousel
- [ ] Credibility allowlist: expand LATAM-specific domains
      (eluniversal.com, clarin.com, etc.)
- [ ] Rate-limiting: cap concurrent IllustrateSkill tasks if queue depth > N
