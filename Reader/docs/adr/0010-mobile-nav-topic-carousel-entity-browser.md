# ADR-R-0010 — Mobile-first navigation: 3D topic-folder carousel + entity browser (CSS 3D, no WebAssembly)

> *Status: v1 · Owner: Julian · Date: 2026-07-12*

## Context

Julian flagged the mobile home as "not looking good, confusing" and asked whether
**WebAssembly** would make it faster with better navigation — referencing a
Nexora-style landing with a 3D rotating carousel of folder cards, and later an
"Entity Navigation" app mockup (type tabs → entity cards → details bottom sheet)
for `/entities`.

Diagnosis of the actual mobile problems:

1. **Home**: five stacked control rows before any news — header + language
   toggle → a 16-chip category scroll row (tiny targets, blind horizontal
   scroll) → trending pill strip → Outlook promo → search row.
2. **Entities**: the force graph (ADR-R-0004) is a desktop interaction — on a
   phone its nodes are tiny touch targets and drag/pan fights page scroll.
3. **A latent DOM bug**: every feed card is a `<Link>` (an `<a>`), and two child
   components also rendered anchors inside it — `AlsoIn` ("also es/en" chips,
   ADR-0037) and `EventCover`'s CC BY/BY-SA attribution overlay (ADR-0034).
   Nested `<a>` is invalid HTML: the parser DOM-corrects it (closing the outer
   anchor early) and React logs a hydration error → the whole feed tree is
   regenerated client-side on every load. Live on prod.

## Decision

1. **No WebAssembly.** WASM cannot touch the DOM (every UI update round-trips
   through JS), adds a binary download + instantiation before first paint, and
   solves *compute* problems, not *layout* problems. The desired effect is
   ~40 lines of CSS: `perspective` on a stage + `rotateY(iθ) translateZ(r)` per
   card — GPU-composited, 60 fps on mid-range phones, zero dependencies.

2. **Home (< `sm`): topic-folder carousel** (`components/topic-carousel.tsx`)
   replaces the category chip row. Each live theme is a gradient folder card
   (tab, count badge, icon, "N stories") on a 3D ring. Swipe/drag rotates
   (transform written directly via rAF during the gesture — React re-renders
   only on settle); the folder that settles front-center applies the existing
   client-side category filter (zero server cost). Chevrons + arrow keys for
   a11y; `prefers-reduced-motion` disables the transition; `overflow: hidden`
   on the stage keeps transformed cards out of the document scroll area
   (transforms contribute to scrollable overflow — this caused a sideways-
   scrolled page in the first build). Trending collapses to a slim accordion
   row on mobile. Desktop (≥ `sm`) keeps the chip row and pill strip unchanged.

3. **Entities (< `sm`): entity browser** (`app/entities/entity-browser.tsx` +
   `entities-view.tsx` shell) over the **same `/graph` payload** — zero backend
   changes (nodes already carry `label/type/event_count/pages`, edges carry
   co-occurrence weights, ADR-0036): type tabs with counts → top-10 horizontal
   snap cards + vertical list + cross-type search → details bottom sheet
   (stories/connections stats, a **static radial relationship preview** of the
   top-6 weighted neighbors — no physics — coverage list, re-centering
   connection chips). The force graph stays one tap away ("Full graph" + back
   bar) and is unchanged on desktop. `TYPE_META`/`TYPE_ORDER` extracted to
   `entities/type-meta.ts`, shared by both views.

4. **Rule: never render an `<a>`/`<Link>` inside a card `<Link>`.** Interactive
   children of link-cards must be `<button>`s that `router.push` (internal) or
   `window.open` (external) with `preventDefault` + `stopPropagation`. Both
   existing violations fixed (`AlsoIn`, `EventCover` credit). Verified:
   `document.querySelectorAll("a a").length === 0`.

## Alternatives considered

| Option | Rejected because |
|---|---|
| WebAssembly UI layer | No DOM access; payload + startup cost on a page that lives on first paint; the effect is plain CSS. Wrong tool. |
| Animation library (framer-motion etc.) | New dependency for one component; CSS transforms + rAF cover it. |
| Flat scroll-snap card row (no 3D) | Works, but loses the "one thing front-and-center" affordance that makes the folder metaphor navigational rather than decorative. Kept as the mental fallback if real-device testing shows jank. |
| Physics mini-graph in the entity sheet | The force sim is exactly what fails on phones; a static radial layout communicates the same top-neighbors information deterministically. |
| Backend `/entities/{id}` endpoint for the browser | Not needed for Phase 1 — `/graph` already ships pages + edges. Phase 2 (Wikidata descriptions) is when Curator gets involved. |

## Consequences

- Mobile home hierarchy: carousel hero → one slim trending row → Outlook →
  search → feed. Category navigation went from 16 blind chips to a spatial,
  swipeable object with live counts.
- Feed hydration is clean for every visitor (the nested-anchor regeneration
  penalty is gone) — this was a real, ongoing prod cost, not cosmetic.
- The carousel auto-applies filters on settle; browsing topics = swiping.
  All filtering stays client-side, so it's free.
- Entity Phase 2 (Wikidata descriptions + official links, ~6–10h, reuses the
  cover agent's `wbsearchentities` + context re-ranking) and Phase 3 (inline
  entity highlights in article text, ~3–5h) are parked with estimates.
- Known data follow-up: *United States* and *Estados Unidos* are separate
  entities — cross-language **entity** merging is the graph cousin of the
  ADR-0037 event dedup.
