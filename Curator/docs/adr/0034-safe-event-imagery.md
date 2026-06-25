# Curator ADR-0034 — Safe event imagery: owned procedural covers over hotlinked source photos

> *Status: **proposed** · Owner: Julian De La Rosa · Date: 2026-06-25*
> *Implements legal-risk mitigation **M1** (`docs/legal-risk.md`): stop displaying source `og:image`s. "Variation, not a copy" — owned/generic imagery instead of branded source photos.*

## Context

Every event card + hero wants a visual. Today the hero is the **source outlet's
`og:image`** (`articles.lead_image`, hotlinked cross-origin). That is risk **L3**
in `docs/legal-risk.md`: those are AP / Getty / Reuters / wire photos with **no
license** — the easiest infringement to prove (one photo = one clean claim).

Two traps to avoid in the replacement:
1. **Copyright** — must not be the source's photo (or any unlicensed photo).
2. **Authenticity / misinformation** — a *photoreal* AI image of a real event or
   person is itself dangerous for a **news** product: it fabricates "evidence,"
   misleads readers, and erodes trust. A generated photo of a real disaster or a
   real politician is not acceptable, however original it is legally.

So the safe sweet spot is **owned, non-photographic, clearly-illustrative**
imagery that is a *variation/representation* of the story, not a copy of it.

## Decision

A tiered, generics-first strategy — every event always has a safe visual:

### Tier 1 (default, every event) — owned **procedural brand cover**
Deterministically render an on-brand cover from data we already have, **no stored
asset, no external call, zero licensing**:
- **seed** = hash(`event_id`) → a unique ink/gradient field (reuse the InkBytes
  ink-shader aesthetic, Reader ADR-0008) so every event looks distinct.
- **palette** = the event's `theme` colour (the 15-theme palette from ADR-0032 —
  science=cyan, crime=slate, …).
- **glyph** = the theme/category icon (existing `components/icons.tsx`).
- **typography** = the headline set in the brand fonts.

Rendered Reader-side (SVG/canvas, cacheable). Unique per event ("variation"),
on-brand, free, never misleading, always available. This is the baseline.

### Tier 2 (variety, optional) — **license-clean generic library**
A curated set of **CC0 / public-domain / commissioned** generic images, mapped by
`theme` + top `LOC` entity: e.g. a generic trading-floor for business, a generic
courtroom for crime, a country **flag/map** (largely free) or CC0 landmark for the
primary location. Clearly *generic representations*, never the source's photo.
Selected deterministically so the same story keeps the same image.

### Tier 3 (top stories only, gated) — **stylized AI editorial illustration**
For `importance ≥ major` only (gate on the ADR-0033 importance score, so cost is
bounded): generate an **original, deliberately non-photoreal** editorial
illustration from the headline + theme. Always **labelled "Illustration."**
**Never photoreal**, never a depiction presented as a real photograph of a real
event or person.

### Hard rules
- The hero **never** uses the source outlet's `og:image`.
- **No photoreal** AI imagery of real events/people; AI/illustration is always labelled.
- The **video rail** (YouTube embeds, ADR-0011/0014) is unchanged — embedding via
  YouTube's own player is a different, much lower-risk legal model than copying a photo.
- `articles.lead_image` may still be *extracted/stored* for internal reference, but
  is **not rendered** as the public hero.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Keep hotlinking source `og:image` | The L3 infringement we're removing. |
| Photoreal AI image per event | Misinformation/authenticity — fabricates "evidence" of real news; erodes trust; the worst fit for a news product even if legally original. |
| Wikipedia / Wikimedia Commons entity photos | Mixed licenses (many CC-BY-SA require attribution; some non-free) → needs a per-image license check; fragile to automate safely. Viable later with a license filter. |
| Paid stock API (Getty/Shutterstock) per event | Cost at scale + still photographic; revisit if a licensing deal happens. |

## Consequences

- **Removes L3** — the highest-certainty copyright exposure — with Tier 1 alone.
- Distinctive, consistent **on-brand** look; reinforces the InkBytes identity instead of borrowing outlets' photography.
- Reuses what exists: the 15-theme palette (ADR-0032), the ink-shader (ADR-0008),
  category glyphs, and the ADR-0033 importance score (to gate Tier 3 cost).
- Tier 1 is free + always available; Tier 3 cost is bounded to top stories.
- Trade-off: less "photographic" — accepted, and arguably a feature (brand identity
  + no fake-photo risk).

## Rollout

1. **P0 — Tier 1 procedural covers** (Reader-side, no migration, no external dep):
   replace the source-`og:image` hero with the generated cover. Immediately kills L3.
2. **P1 — Tier 2 CC0 generic library** keyed to theme + LOC for variety.
3. **P2 — Tier 3 stylized AI illustration**, gated on ADR-0033 `importance ≥ major`.
