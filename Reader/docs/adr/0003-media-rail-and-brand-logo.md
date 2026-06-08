# ADR-R-0003 — Media rail surfacing + brand logo mark

> *Status: accepted · Owner: Julian · Date: 2026-06-07*

## Context

Two Reader changes landed together in this session:

### 1. Media rail (IllustrateSkill output)

`IllustrateSkill` (Curator Skill 4) now writes a `media_rail` JSONB array to
`pages.media_rail` after synthesis. Each element carries:
`url · thumb_url · type ("image"|"video") · title · source_domain · published_at · width · height · score`.

The Reader had no way to surface this data — the API endpoint didn't expose
the column, the TypeScript type was absent, and no UI existed.

### 2. Brand logo mark

The header and favicon used a text-only `InkBytes.` wordmark and a placeholder
`I`-letter SVG favicon. The real vector brand asset
(`InkBytes-Logo-White-cropped.svg`) was available and unused.

---

## Decisions

### Media rail

**API (`/events/{id}`):** `SELECT p.*` already includes `pages.media_rail` since
it's on the `pages` table; the only missing step was decoding it.
`_decode_json_col()` (existing helper) normalises both `jsonb` (already decoded
by asyncpg) and raw JSON strings — so a one-liner alongside `timeline` handles
it.

**TypeScript type (`MediaRailItem`):** Added as a named interface to `lib/types.ts`
so every consumer is type-safe. Made optional on `EventPage` (`media_rail?`) for
backward compat with pages synthesised before IllustrateSkill shipped.

**UI layout — two-tier rendering inside the event page:**
- *Images*: horizontal scroll strip (`overflow-x-auto snap-x scrollbar-hide`)
  between the hero and the meta row. Each thumbnail is a `192×128` `<a>` card
  that links to the full image URL. Matches the `scrollbar-hide` class already
  used in `feed-client.tsx` (consistent with ADR-R-0002 utility discipline).
- *Videos*: inline "Watch" chips with the thumbnail image, a play-icon overlay,
  a coral "WATCH" label, the clip title, and `source_domain`. Sit below the
  image strip (or alone when no images exist).
- Both tiers are rendered via an IIFE guard: `(page.media_rail ?? []).filter(…)`;
  renders nothing when the array is empty (old pages unaffected, zero layout
  shift).

**Placement decision:** below the hero cover image, above the meta row (topic /
sources / timestamp). This keeps media contextually close to the hero without
interrupting the headline → synthesis reading flow.

### Brand logo

**Component (`components/logo.tsx`):** `LogoMark` is a standalone SVG component
using the exact 13 paths from the official `InkBytes-Logo-White-cropped.svg`.
`viewBox` is preserved verbatim (`274 206 481 477`) — no path transformation
needed. `fill="currentColor"` replaces the hardcoded `#FFFFFF` so the mark
inherits any parent text color (white on the dark header; adaptable to future
light-mode or marketing pages).

**Header:** The text-only `InkBytes.` link is replaced with
`<LogoMark h-6 text-white> + wordmark`. Gap is `2.5` (10px) — tight enough to
read as a unit, loose enough to breathe at small sizes.

**Favicon (`app/icon.svg`):** Rebuilt with the same 13 paths on the brand dark
(`#1a1a2e`) rounded-square background. `rx="105"` gives the same visual corner
radius as `rx="7"` at the 32px display size. Browsers (and Next.js) serve this
as the tab icon and iOS home-screen icon.

---

## Alternatives considered

| Option | Rejected because |
|---|---|
| Render media_rail below the evidence rail | Breaks reading flow — evidence is a citation section; media belongs near the hero |
| Video as inline embed (`<iframe>`) | GDPR / perf: embeds load Google scripts unconditionally; chips let the user opt in |
| Inline the logo SVG in layout.tsx | `components/logo.tsx` is reusable (future marketing, about page, email templates) |
| Keep the placeholder I-letter favicon | Brand inconsistency; the real asset was already available |

---

## Consequences

- `GET /events/{id}` now always returns `media_rail: []` for older pages
  (decoded from `null` by `_decode_json_col`). No breaking change.
- `MediaRailItem.thumb_url` is nullable; image strip gracefully falls back to
  `img.url` when null (full image as its own thumbnail).
- `LogoMark` uses `fill-rule="evenodd"` matching the source file; do not change
  to `nonzero` — the nib interior would fill incorrectly.
- The favicon `rx="105"` produces identical corner curvature to the previous
  `rx="7"` at 32px, so the tab icon is visually unchanged in shape; only the
  graphic changes.
