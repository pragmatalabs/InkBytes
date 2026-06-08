# ADR-R-0004 — Entities graph on mobile + media rail as action-bar drawer

> *Status: accepted · Owner: Julian · Date: 2026-06-07*

## Context

Two independent Reader UX issues surfaced during the 2026-06-07 session:

### 1. Entities page: mobile shows a pill list, desktop shows the force graph

`graph-client.tsx` used `hidden md:grid` / `md:hidden` to render two completely
different UIs: the interactive D3-style force graph on desktop and a flat
`MobileList` of entity pills on mobile. Mobile users could not explore the
graph, drag nodes, or see the visual cluster structure.

### 2. Media rail: always-visible inline strip (below hero)

`IllustrateSkill` fills `pages.media_rail` with 6 ranked images/videos after
synthesis. The initial Reader implementation rendered this as an always-visible
horizontal scroll strip below the hero image — interrupting the reading flow and
adding visual noise on every page load even before the user expressed interest.

Additionally, `media_rail` arriving as a raw JSON string from asyncpg (no JSONB
codec registered) caused a `TypeError: rail.filter is not a function` 500 error
when the client component tried to call `.filter` on a string.

---

## Decisions

### Entities graph: unified responsive grid

**Change:** Remove the duplicate `hidden md:grid` / `md:hidden` blocks. Replace
with a single `grid grid-cols-1 md:grid-cols-[1fr_320px]` container that renders
the SVG graph on all screen sizes.

- **Graph height:** `h-[min(55vh,440px)]` on mobile → `md:h-[min(72vh,700px)]`
  on desktop. Slightly shorter on mobile so the panel below is visible without
  scrolling.
- **Touch interaction:** `touchAction: "none"` on the SVG element. Without this,
  a finger-drag fires both PointerEvents (moving a node) AND a page scroll
  simultaneously — nodes become impossible to drag on touch screens.
  PointerEvents (`onPointerDown/Move/Up`) already work for touch; only the
  default scroll behaviour needs suppressing.
- **EntityPanel on mobile:** Stacks below the graph (no `max-h` cap on mobile;
  page scrolls naturally). On `md+` it is constrained to `max-h-[min(72vh,700px)]`
  and scrolls independently.
- **MobileList removed:** The pill-list component is deleted entirely — 67 lines
  gone, no longer needed.

### Media rail: collapsed drawer in the action bar

**Problem with inline strip:** Renders unconditionally above the fold, feels
like advertising noise. Users who want to watch video/see images are self-
selecting — the feature should be opt-in per page load.

**Decision:** Move the media trigger into the `← All events / Share` action bar
as a compact icon button. The expandable panel appears *below the action bar*
(inline, not a modal overlay) and pushes content down when open.

**`MediaRailDrawer` client component** (`app/event/[id]/media-rail-drawer.tsx`):
- Owns `open: boolean` state via `useState`.
- Accepts `rail`, `back` (ReactNode), and `share` (ReactNode) as props —
  server-rendered nodes can be passed as props to a client component, avoiding
  a full-page client boundary.
- Button: streaming SVG icon + item count (`6`). Rendered only when
  `rail.length > 0` — zero visual footprint when IllustrateSkill has not run.
- Icon pulse: two `animate-ping` rings (`#6A6493` purple / `#FC4442` red,
  staggered 1 s, 2 s cycle, 25%/15% opacity). Ambient, non-intrusive — conveys
  "live" origin of the media without demanding attention.

**JSONB string guard:** asyncpg returns plain `JSONB` columns as Python strings
when no codec is registered. The Curator API applies `_decode_json_col()` to
normalise, but the Reader additionally guards defensively:
```ts
Array.isArray(raw) ? raw : typeof raw === "string" ? JSON.parse(raw) : []
```
This makes the Reader resilient independent of the API version.

---

## Alternatives considered

| Option | Rejected because |
|---|---|
| Keep MobileList for mobile entities | Users can't see the graph structure or connections; defeats the purpose of a graph UI |
| Swipe-up modal for entities panel on mobile | Extra complexity; stacked panel below the graph is discoverable and works without JS tricks |
| Portal for media drawer (render outside action bar) | Unnecessary complexity; inline expansion is simpler and doesn't require a DOM ref |
| `<details>/<summary>` for media drawer | Works without JS but button can't be co-located with Share in the flex bar — the `<summary>` can only be the first child of `<details>` |
| Always-visible media strip | Tested; user feedback: "looks like ads", clutters reading flow |

---

## Consequences

- `graph-client.tsx` is 60 lines shorter (MobileList + duplicate graph block removed).
- The force simulation runs on mobile. With many nodes (200+) this costs more CPU
  per frame, but the `alpha` decay (`0.985×` per tick) means the sim settles in
  ~3 s and then stops consuming cycles.
- `MediaRailDrawer` is the only `"use client"` component on the event page besides
  `ShareButton`. Both are pure leaf nodes — no provider or context required.
- `media_rail?: MediaRailItem[]` stays optional on `EventPage` so pages
  synthesised before IllustrateSkill deployed render with no drawer at all.
