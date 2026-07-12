# ADR-R-0006 — Media drawer shows videos only

> *Status: accepted · Owner: Julian · Date: 2026-06-08*
>
> **Update 2026-07-12 — video coverflow (committed, NOT deployed):** the drawer's
> flat chip row is now a 3D coverflow (`components/video-coverflow.tsx`, same
> zero-dependency CSS `perspective`/`rotateY` technique as the ADR-R-0010 topic
> carousel): dark stage, glowing center card, 16:9 thumbs + play overlay +
> quality badge (derived from `width`/`height` — no durations in the rail),
> title·source·date caption, swipe/chevrons/dots/arrow keys; tap center = open,
> tap side = focus; cards beyond ±3 culled; reduced-motion safe. The center card
> is a top-level `<a>` (the drawer is not inside a card `<Link>` — respects the
> ADR-R-0010 no-nested-anchors rule). Verified on dev against prod data
> (6-video events) at 375px + 1280px.

## Context

`MediaRailDrawer` previously rendered two sections:

1. A horizontal scroll strip of **images** (clickable `<img>` tiles)
2. A chip list of **videos** with YouTube thumbnails + "Watch" label

A production event surfaced a truck-parts photo from an Australian trucking
trade magazine as an "image" in the drawer — unrelated to the news story but
large enough to score well.

Curator ADR-0014 removes image fetching at the source.  This ADR covers the
corresponding Reader change.

## Decision

`MediaRailDrawer` filters `rail` to `type === "video"` before rendering.
The image strip section is removed entirely.

- The button counter now shows the **video count** (not total rail length).
- Existing pages with stored image items silently show zero images (no
  migration needed — they were already displayed in a separate strip that
  no longer exists).
- `aria-label` updated to "Show videos" / "Hide videos".

## Consequences

- **Positive:** drawer always shows relevant, playable YouTube videos.
- **Positive:** no broken `<img>` tiles from sites that eventually 404 or
  rotate their CDN URLs.
- **Neutral:** pages without YouTube coverage show no drawer button — this
  is the correct signal (nothing to show).
