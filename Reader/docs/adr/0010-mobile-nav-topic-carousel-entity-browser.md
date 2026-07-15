# ADR-R-0010 — Mobile-first navigation: 3D topic-folder carousel + entity browser (CSS 3D, no WebAssembly)

> *Status: v1 · **DEPLOYED + verified live 2026-07-12** · Owner: Julian · Date: 2026-07-12*

> **Update 2026-07-15 — mobile home v2 (Rams pass, iterated live with Julian — PROPOSAL, not yet deployed):**
> A second "less but better" pass over the mobile home, above the feed:
>
> - **One nav, one search.** The top text-nav (`layout.tsx`) is now `hidden sm:flex`
>   — on mobile the bottom tab bar *is* the nav, so the second copy was pure
>   redundancy. The header search *pill* was removed too; there is now a single
>   search, moved to the **top of the content** (`find beats browse`).
> - **Outlook = signal, not banner.** The old Outlook promo banner is gone;
>   Today's Outlook is now a small **pulsing icon** (`outlook-pulse`,
>   reduced-motion-safe) sitting on the title row where the eye already is.
> - **Header no-wrap.** The title column is `flex-1 min-w-0` and the `All/EN/ES`
>   language toggle moved *out* of the title row and *into* the search row (a
>   filter, beside the other filters). Together these keep the date +
>   "Today's events" on single lines at 375 px — before, the squeezed column
>   wrapped the date to two lines.
> - **LATEST → coverflow.** The flat scroll-snap strip became `BreakingCoverflow`
>   — the *same* CSS-3D pattern as the topic carousel / video coverflow (no libs):
>   a **circular** ring where the **newest** story is centered, the **next-newest**
>   sits right, and the **oldest wraps around to the left**, so it is always
>   balanced with a neighbor on each side; swipe / chevrons / arrow-keys loop
>   (no dead ends). The centered card is a smaller **13 px semibold** headline in
>   a **uniform rounded border tinted to the category accent** (`themeAccent`), with
>   a deep two-layer shadow so it lifts off the page; side cards flatten and dim.
> - **"Today's events" heading kept** (Julian: it is needed). Subtitle trimmed to
>   `{n} stories · updated {time}` (the daily tagline was dropped for returning
>   readers).
>
> Process note: the in-app browser pane's **screenshot context can desync from
> its JS/scroll context** (screenshot rendered at 375 CSS px @2× DPR while
> `innerWidth` scripts saw a 559 px layout, and `scrollTo(0,0)` moved only the
> script context). Trust DOM measurements (`getBoundingClientRect`, computed
> style) for layout assertions; use the screenshot for the final look, taken
> from a fresh load rather than a scripted scroll.

> **Update 2026-07-12 — folder carousel v2 (Nexora layout, iterated live with Julian):**
> The topic carousel's card art went through several rounds and settled on
> Julian's `folder-definitive.svg` rendered as a **live tile** (`components/
> folder-glyph.tsx`): a **white folder with a category-coloured border**
> (source greys → white fills, strokes → `currentColor` accent), a soft accent
> **sheen dimming in from the top-right** of the front face, and the Nexora
> content layout — accent **icon tile** top-left, **count** top-right,
> **left-aligned** category name + small grey "N stories" bottom-left. The
> front/selected folder carries an **accent glow**. A staggered **entrance
> animation** (`tc-enter`, delay `i*45ms`, reduced-motion-safe) makes it read
> as a true carousel on load. Landscape geometry (158×124, aspect 512:400) to
> keep vertical spend low. Colour lives in the border + icon + count, not the
> folder body. All still driven by the existing client-side category filter;
> desktop (≥ sm) unchanged.
>
> Process notes worth keeping: Turbopack served stale global CSS through dev
> restarts several times — `rm -rf .next` was required each visual iteration
> (compile-cache cousin of the fetch-cache lessons). SVG gradient ids must be
> unique per instance (`useId`) or every folder binds the first one's accent.

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
- **Entity avatars 2026-07-12 (DEPLOYED):** country entities show a **flag**
  (`lib/country-flags.ts`, offline). **Person photos + Wikidata descriptions**
  shipped too: Curator migration 023 `entity_media`, `services/entity_photo.py`
  (Commons P18, human-filtered via P31=Q5 + context re-rank), `/graph` LEFT JOIN,
  `scripts/backfill_entity_photos.py`. EntityAvatar precedence photo>flag>icon;
  the sheet shows portrait + description + CC credit (PD → no credit). 89 people
  cached on first backfill (87 photos). Descriptions ARE Entity Phase 2 (done).
- Entity Phase 3 (inline entity highlights in article text, ~3–5h) parked.
- Known data follow-up: *United States* and *Estados Unidos* are separate
  entities — cross-language **entity** merging is the graph cousin of the
  ADR-0037 event dedup.
