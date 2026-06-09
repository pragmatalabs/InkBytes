# ADR-0019 — Lead-image hotlink guard: drop CDN-blocked og:images at ingest

> *Status: accepted / implemented · Owner: Julián · Last updated: 2026-06-08*
>
> Fixes blank hero/cover images on event pages and feed cards for some outlets.

## Context

Each event's cover image (`lead_image` on the `/events` and `/events/{id}`
responses) is rolled up at query time as the *first non-null* `articles.lead_image`
of the event's articles, ordered by `scraped_at DESC` (see
[`core/api_server.py`](../../apps/curator/core/api_server.py)). `articles.lead_image`
is the source outlet's **og:image** URL, extracted by Messor and stored verbatim.

For some outlets the cover rendered as a **blank box** in the Reader, with no
`onError` fallback. Reported example: event `01KTMRBYT1Q86Q1Z1TTDENH32Q`, whose
`lead_image` was an LA Times brightspot URL.

### Root cause — cross-origin hotlink protection serving a 1×1 placeholder

The Reader embeds `lead_image` as a **cross-origin** `<img>`. A real browser
sends two request headers on that load that server-side fetchers do not:

```
Sec-Fetch-Dest: image
Sec-Fetch-Site: cross-site
```

LA Times' brightspot CDN treats that exact fingerprint as hotlinking and
**302-redirects to `…/placeholder-1x1.png`** — a 69-byte transparent pixel served
with HTTP 200. Verified by isolating the trigger:

```
Sec-Fetch-Dest:image + Sec-Fetch-Site:cross-site  → HTTP 302 → placeholder-1x1.png
either header alone / no Sec-Fetch headers          → HTTP 200 → real JPEG
```

Two consequences explain everything observed:

- **It's invisible, not broken.** The redirect lands on a *valid* 1×1 PNG (200),
  so `<img onError>` never fires. `object-cover` stretches a transparent pixel →
  blank box, no fallback.
- **It passes every server-side check.** Messor's harvest, link-preview bots, and
  `curl` don't send `Sec-Fetch-*`, so they all see a real 200 JPEG. The dead URL
  sails through extraction and only fails inside a real browser embedding it
  cross-origin — which is why it's hard to spot and affects only *some* outlets
  (those with hotlink protection; brightspot and similar).

## Decision

Validate `lead_image` **at ingest**, reproducing the browser fingerprint, and
store hotlink-blocked URLs as `NULL` so the existing `/events` rollup naturally
falls back to another source's image (or none).

A new `MediaValidator` ([`services/media_validation.py`](../../apps/curator/services/media_validation.py))
probes each og:image URL with `Sec-Fetch-Dest: image` + `Sec-Fetch-Site:
cross-site` (+ a Chrome UA and an inkbytes Referer), follows redirects, and
classifies the URL **not displayable** when the final response is:

- non-200, or
- a non-`image/*` content-type (CDN error page), or
- a URL containing `placeholder` (followed a hotlink redirect to a pixel), or
- an image smaller than 512 bytes (1×1 tracking/placeholder pixel).

It **fails open** (keeps the URL) on timeout / network error — a transient outlet
hiccup must not permanently drop a good image.

The probe runs in `Application._handle_event` just before `upsert_article_raw`;
a blocked URL is nulled on the article dict before storage. Results are cached
in-process per URL (LRU, 5000 entries) so a URL is probed over the network at
most once per worker lifetime — re-scrapes and CDN-templated images hit the
cache. The pipeline is already gated by `max_concurrent_articles` (4), so at most
4 probes run concurrently; each has a 4 s timeout.

A toggle `application.validate_lead_images` (default `true`) and
`application.lead_image_probe_timeout_s` (default `4.0`) are in `AppCfg`.

## Consequences

- Events whose freshest source has a hotlink-blocked image now show the next
  source's image instead of a blank hero. Events where *every* source is blocked
  show no cover (the Reader already renders text-only when `lead_image` is null).
- One extra outbound GET (headers only, body not downloaded) per newly-seen
  og:image URL. Negligible at current volume; cached thereafter.
- This is an **ingest-time** guard: URLs already stored before this change are
  only re-evaluated when their article is next re-scraped with changed content.
  A one-time backfill could re-probe existing rows if blank covers persist.

## Alternatives considered

- **`referrerPolicy="no-referrer"` on the `<img>`.** Rejected — the Referer is
  not the trigger; `Sec-Fetch-Site: cross-site` is, and the browser always sends
  it for cross-origin image loads. Stripping the Referer doesn't help.
- **Client-side placeholder guard** (hide on `naturalWidth ≈ 1`). Useful as a
  defensive net but shows *no* image and doesn't fix the stored data. Deferred;
  ingest validation was chosen as the primary fix.
- **Re-host images on DO Spaces (image proxy).** The durable fix — serve covers
  from our own origin, immune to hotlinking, and gives relevance control. Bigger
  infra change (storage + worker), and in tension with the images-parked stance
  ([ADR-0014](./0014-media-rail-video-only.md)). Deferred.
