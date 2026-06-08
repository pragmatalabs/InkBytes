# ADR-0014 — Media rail is video-only; Bing image fetcher parked

> *Status: accepted · Owner: Julian · Date: 2026-06-08*

## Context

IllustrateSkill originally ran two concurrent fetchers:

1. **Bing Images** (Patchright headless) — returns `type="image"` items
2. **YouTube** (Playwright headless) — returns `type="video"` items

A production event page (`/event/01KTCZPG6XA22GBZBGDP1T2HE0`) surfaced an
off-topic industrial parts photo from `primemovermag.com.au` in the media
drawer.  This is a symptom of the deeper problem: image search returns any
image that's visually prominent for the query, including unrelated product
photos, catalog shots, and magazine covers from tangentially-related
industrial sites.

Domain blocklists and title relevance gates (ADR-0013, introduced in the
previous session) help, but are fundamentally a whack-a-mole approach for
arbitrary image sources.

## Decision

**The `pages.media_rail` column stores only video items going forward.**

- `_fetch_bing_images` is parked (kept in source for reference, not called).
- `IllustrateSkill.run()` only calls `_fetch_youtube_videos`.
- The Reader's `MediaRailDrawer` filters to `type === "video"` client-side
  so that existing pages with stored image items are silently excluded.

The rule: **YouTube links and, in the future, direct outlet-embedded videos.**
Anything `type="image"` is excluded.

## Rationale

| Approach | Verdict |
|---|---|
| Keep Bing + add smarter filters | Rejected — no stable signal distinguishes "relevant news photo" from "random editorial image" without per-domain curation at scale. |
| Use Google Image Search instead | Rejected — same fundamental problem; API requires paid quota. |
| Videos only | **Chosen** — YouTube results for a news query reliably map to actual news coverage; thumbnails are always relevant; no false positives from catalog/stock images. |

## Future extension

If a direct outlet video fetcher is added (e.g. Bing Video API, or
scraping video embeds from scraped article pages), it produces
`type="video"` items and slots in naturally — no Reader change needed.

## Consequences

- **Positive:** no more off-topic images in the media drawer; each item
  is a playable YouTube video directly relevant to the event headline.
- **Positive:** removes one Chromium browser instance per synthesis cycle
  (~200 MB RAM, ~3–5 s wall-clock saved per event).
- **Negative:** events without strong YouTube coverage get an empty rail
  (drawer button hidden). Acceptable — empty drawer > misleading images.
- **Existing pages:** `media_rail` columns already written will contain
  image items.  The Reader filters them out at display time; no migration
  needed.
