# Curator ADR-0034 — Safe event imagery: owned procedural covers over hotlinked source photos

> *Status: **P0 + P1a + P1b + Unsplash implemented** (2026-06-28, committed) · Owner: Julian De La Rosa · Date: 2026-06-25*
>
> **Unsplash source (2026-06-28):** added `unsplash_cover()` — high-quality generic photos via the official **Unsplash API** (`api.unsplash.com`, NOT the search-page URL — scraping it violates their ToS). Unsplash License = commercial-OK. `pick_cover` order is now **Wikimedia entity-canonical → Unsplash (theme/entity generic) → Openverse CC0 → procedural**. Gated on `UNSPLASH_ACCESS_KEY` (blank → skipped, chain unchanged). ToS honored: photographer + Unsplash credit (rendered via the `event-cover.tsx` overlay: `Photo by {name}` · `Unsplash`, linked with utm) and the `download_location` trigger on use. Kept strictly generic (theme/entity keyword), never event footage (misinformation guardrail). **To activate:** register an app at unsplash.com/developers → set `UNSPLASH_ACCESS_KEY` in `infra/.env` (compose passthrough added).
>
> **P1b (Tier 2, Wikimedia/Wikidata entity path) + cover agent:** `cover_image.py` adds `wikimedia_entity_cover()` (resolve entity → Wikidata Q-id → **P18** image → Commons `imageinfo`/`extmetadata`; license gate accepts CC0/PD/BY/BY-SA, **rejects** NC/ND, `NonFree`, any `Restrictions`; stores Artist attribution for BY/BY-SA) and a `pick_cover()` orchestrator: **Wikimedia entity-canonical (prefer LOC, then ORG) → Openverse CC0 keyword → None (procedural)**. The canonical images are far more relevant (Argentina→Fitz Roy PD, Madrid→cityscape, Binance→its photo). **The "agent" = `Application._cover_safe`** — a fire-and-forget step spawned after every synthesis (beside IllustrateSkill): if the event has no cover, pick + store one. New events auto-covered; `scripts/backfill_covers.py` (now `pick_cover`-based) covers the backlog. Reader `event-cover.tsx` renders a BY/BY-SA credit overlay (CC0/PD → none). Pending: Tier 3 (gated AI).
>
> **P1a (Tier 2, Openverse):** `services/cover_image.py` queries Openverse with `license_type=commercial` + `license=cc0,pdm` (CC0/PD only → zero attribution burden), keyed to the event's top **LOC** entity (a place → its landmark; "prefer places over people") or its theme; deterministic pick (seed = event id) so the same story keeps the same image; fail-open → procedural cover. Migration `021_event_cover_image.sql` (`events.cover_image` JSONB provenance: url/thumb/license/source_url/provider). `scripts/backfill_covers.py` (rate-limited, dry-run default) populates recent events; `/events` + `/events/{id}` return `cover_image`; Reader `components/event-cover.tsx` renders it over the procedural fallback (img onError → procedural shows through). Validated live against Openverse (CC0 landmarks/courthouses/stadiums). Still pending: the **Wikimedia/Wikidata P18 entity path** (canonical flag/map per entity), `by`/`by-sa` + attribution rendering, and Tier 3 (gated AI).
> *Implements legal-risk mitigation **M1** (`docs/legal-risk.md`): stop displaying source `og:image`s. "Variation, not a copy" — owned/generic imagery instead of branded source photos.*
>
> **Implemented (P0, Tier 1):** `Reader/components/procedural-cover.tsx` — a deterministic owned cover (seed=event id → theme-color gradient + seeded blobs + category glyph). Replaces the source og:image as the hero (event page) AND on the feed Lead/Secondary cards; the source `og:image` (an outlet LOGO triggered this — infobae's brand card) is no longer rendered. Also dropped the source photo from the event page's OpenGraph/Twitter share metadata (same M1 exposure). `lead_image` still stored, not rendered. `/events/{id}` now returns the majority `theme` → cover color. P1 (Tier 2 CC0/Openverse + Wikidata generic photos for variety) and P2 (gated AI illustration) still pending.

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

### Tier 2 (variety, optional) — **license-clean generic library via Openverse**
Generic images mapped by `theme` + top `LOC` entity (generic trading-floor for
business, courtroom for crime, country flag/map, CC0 landmark), selected
deterministically so the same story keeps the same image. Clearly *generic
representations*, never the source's photo.

Source: the **Openverse API** (`api.openverse.org`) — the successor to "CC Search"
(NOT `api.creativecommons.org`, which is a 2011 license-*generation* service, not
image search). It aggregates ~700M openly-licensed images.

**Commercial-use guardrails (InkBytes is paid — non-negotiable):**
- Query with **`license_type=commercial`** (excludes all **NonCommercial/NC** —
  using NC in a paid product is a violation) `+ modification` (excludes **ND** if
  we crop/recolor).
- **Default to `license=cc0,pdm`** (CC0 + Public Domain Mark) → no attribution
  obligation, simplest for automated covers. If `by`/`by-sa` are allowed, **render
  the attribution string** Openverse returns (author + license + `license_url`);
  avoid heavy edits of `by-sa` (share-alike on adaptations).
- ⚠️ Openverse **does not verify** license accuracy ("independently verify before
  reusing") → **store license + attribution + source URL per chosen image** for
  provenance; metadata-trust risk is why this stays Tier 2, not the foundation.
- These are photos → strictly **generic representation**, never implying it depicts
  the actual event.

**Entity-keyed path — MediaWiki / Wikimedia Commons API** (`www.mediawiki.org/wiki/API`).
Complements Openverse's keyword search: it returns a **canonical image per entity**
— `prop=pageimages` (article lead image) or Wikidata **P18** for the event's top
`LOC`/`ORG` (a country flag/map, the Sagrada Família, a stadium). This dovetails
with entity resolution (ADR-0032 item 3): resolve an entity → Wikidata ID → its
image, nearly free. Guardrails:
- Pull license metadata with `prop=imageinfo&iiprop=extmetadata` → `License` /
  `LicenseShortName`, `UsageTerms`, `Artist`, `AttributionRequired`, `LicenseUrl`,
  `Restrictions`, `NonFree`. Accept only commercial-OK (CC0/PD/BY/BY-SA); **reject
  `NonFree=true` or any `Restrictions`** (trademark/personality/currency), and NC/ND.
- Query **commons.wikimedia.org** (free-content only) rather than en.wikipedia
  page-images, which can point to **locally-hosted non-free/fair-use** files.
- Render attribution for BY/BY-SA (`Artist` + license + `LicenseUrl`); prefer
  CC0/PD to skip it. `extmetadata` is **expensive** → request few + cache per
  entity. Wikimedia requires a **descriptive `User-Agent`** (policy) or you're blocked.
- **Prefer places/things over people** — a real person's photo adds
  personality/publicity-rights + recency/context concerns beyond the photo's copyright.

### Tier 3 (top stories only, gated) — **stylized AI editorial illustration**
> **DEFERRED by decision (2026-06-28).** Considered adding OpenAI image generation
> (gpt-image-1) as a Tier-3 source. Declined for now: the license-clean chain
> (Wikimedia → Unsplash → Openverse → procedural) already gives every event a clean,
> relevant cover, and Tier 3 adds (a) recurring per-image cost, (b) re-hosting infra
> (boto3 + a public Spaces bucket — AI images expire and are owned), and (c) the
> "AI imagery on news" trust question. Marginal value (a bespoke illustration for the
> few biggest stories) didn't justify those. Revisit if a clear need emerges; the
> hard rules below still bind any future build.

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
| ~~Wikipedia / Commons entity photos — rejected~~ | **Promoted into Tier 2** as the *entity-keyed* path (Wikidata P18 / pageimages + `imageinfo/extmetadata` license filter). Mixed licenses + non-free locals are handled by the guardrails above (query Commons, reject `NonFree`/`Restrictions`, attribute BY/BY-SA, prefer places over people). |
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
