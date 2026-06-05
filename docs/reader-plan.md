# Reader — Desktop + Mobile Plan (from the design prototype)

> *Status: plan · Owner: Julián de la Rosa · Last updated: 2026-06-04*
>
> Plan to evolve the public **Reader** (`Reader/apps/web`, Next.js) toward the uploaded
> design prototype — **without losing the original product goals**. Design reference is
> vendored at [`docs/reader-prototype/`](./reader-prototype/) (the self-contained React
> prototype + screenshots). Product goals: [`product.md`](./product.md). Data source:
> Curator `:8060`.

## 1. What the prototype is
A self-contained React prototype (`docs/reader-prototype/`, CDN React + Babel) with **three
reader surfaces** + a dev tweaks panel:

- **Feed** (`feed.jsx`, screenshots `01-lower.png`/`02-lower.png`) — event cards with a
  source-avatar stack, **Factuality**, **Coverage** (article count + sparkline), a
  **DEVELOPING** badge, and entity chips.
- **Event page** (`event.jsx`, `uploads/pasted-…png`) — `DEVELOPING` badge · *N sources ·
  updated* · big headline · **entity chips** · **stat cards (Sources / Factuality /
  Coverage)** · drop-cap body with inline **`Source: X`** citations · **SOURCES** evidence rail.
- **Entity graph** (`graph.jsx`, `screenshots/graph*.png`) — interactive force graph,
  "Navigate the news by who & what": Place/Person/Org/Topic nodes linked when they share a
  story, click a node → its coverage, "Most connected" side panel, type filters, entity search
  (34 entities · 103 links · 8 events in the sample).

## 2. Current Reader vs prototype
Built today: `app/page.tsx` (feed), `app/event/[id]/page.tsx`, `app/about`, `app/login`,
`app/api/auth`. Server-rendered; reads Curator `/events`, `/events/{id}` (PageV1:
`synthesis_md`, `evidence_rail`, `entities`, `source_count`, `article_count`). Auth = demo
password.

| Surface | Built today | Prototype | Gap |
|---|---|---|---|
| **Event page** | headline · source_count · entity chips · synthesis **with inline citations** · evidence rail | + DEVELOPING badge · **stat cards** (sources/factuality/coverage + sparkline) · drop-cap | **medium** — core present, needs the polish layer |
| **Feed** | plain headline-only cards | rich cards (avatars, factuality, coverage, badge, chips) + search/topics | **large** |
| **Entity graph** | — none — | full interactive graph + panel | **new surface** |
| **Mobile** | basic Tailwind responsive, unverified | first-class | **deliberate pass needed** |

## 3. 🎯 Goals to preserve (guardrails — do NOT lose these)
From `product.md`: **one elegant synthesized page per event**, every claim **source-cited**,
**entity context** + **source diversity** visible, **ad-free**, fast, and **paid gating**
(free = headline + ~100 words; **$9/mo** unlocks full synthesis + evidence rail + entity
links). The new surfaces wrap *around* this promise — they must never bury the synthesized
event page or drop citations to chase graph eye-candy. On mobile the **synthesized event page
is first-class**; richer surfaces (esp. the graph) degrade gracefully, never block the core.

## 4. Desktop plan
1. **Event page → prototype parity** (it's the product): DEVELOPING badge (from `freshness_at`
   recency), the 3 stat cards, drop-cap; **keep** the inline `Source:` citations + evidence
   rail + entity chips (already built). Entity chips deep-link into the graph filtered to that
   entity.
2. **Feed upgrade**: event cards with source-avatar stack, factuality, coverage, badge, entity
   chips; top nav **Search / News / Topics / Entities / About**.
3. **Entity graph** (`/entities`): port the prototype's force sim + "Most connected" panel +
   type filters + entity search; click an entity → its events.

## 5. Mobile plan (where "without losing goals" bites)
- **Event page = first-class on mobile**: single column; stat cards → compact strip; drop-cap
  scales; citations stay tappable; evidence rail collapses under the body; entity chips wrap;
  gating prompt inline. Must be flawless — it's the core promise.
- **Feed**: single-column cards, condensed meta, sticky search.
- **Entity graph**: a force graph is clumsy on a phone — **degrade, don't drop the goal**.
  Mobile shows an **entity list grouped by type** (Place/Person/Org/Topic) with counts +
  "Most connected", tap → events. (Optional later: pannable/zoomable touch graph.) The
  "navigate by who & what" goal is preserved without a janky canvas.
- Nav collapses to a drawer; sticky search.

## 6. Data gaps the backend must close
1. **Entity graph needs a new Curator endpoint** — e.g. `GET /graph` returning entity
   **nodes** (name, type, count) + **co-occurrence links** (entities sharing an event).
   Curator has the `entities` table + per-page `entities`, but no graph endpoint. (Deriving it
   client-side from `/events` is heavy — a backend endpoint is the right call.)
2. **Event-level Factuality + Coverage sparkline** — `factuality` is *per-article* enrichment;
   the event aggregate + coverage-over-time series aren't in PageV1. Either Curator exposes
   them, or the Reader ships **Sources + Coverage count** (available) and treats Factuality +
   sparkline as a follow-on.
3. **Paid gating** — real subscriber gating is **Phase 3 (Stripe, paused)**. Design the
   free/paid **content boundary now** (free = headline + ~100 words + source count; paid =
   full synthesis + evidence rail + entity links + graph) so it's ready to wire; keep the demo
   gate meanwhile.

## 7. Phasing
| Phase | Scope | Backend dep |
|---|---|---|
| **R1** | **Event page → parity, desktop + mobile** (the core): DEVELOPING badge, stat cards (Sources + Coverage; Factuality deferred), drop-cap; keep citations + evidence rail + entity chips; mobile-first responsive | none (existing PageV1) |
| **R2** | Feed upgrade + nav/search (desktop + mobile) | none |
| **R3** | Entity graph: Curator `GET /graph` endpoint → desktop force graph + mobile entity-list | **Curator `/graph`** |
| **R4** | Global responsive / perf / SEO pass (keep SSR + OG tags) | none |
| **R5** | Gating boundary (free vs paid) wired to subscriber status | **Phase 3 / Stripe** |

**Start with R1** — highest value, no backend dependency, and it hardens the core promise on
both desktop and mobile.

## 8. Tech guardrails
- ⚠️ **Heed [`Reader/apps/web/AGENTS.md`](../Reader/apps/web/AGENTS.md)** — "this is NOT the
  Next.js you know; read `node_modules/next/dist/docs` before writing code." Respect the pinned
  Next 16 specifics.
- **Reuse the prototype's `graph.jsx` force sim** (dependency-free, ~449 LOC) rather than
  adding a heavy graph library — mirrors how Backoffice B4 did a no-lib inline-SVG chart.
- Keep **server-rendered + OG tags** (event pages are SEO/share targets) and the existing
  CSS-variable design system.
- Reader reads Curator `:8060`; it must run (`--api-only` is enough for reads) to serve pages.

## 9. Open decisions for the owner
- **Factuality/coverage-sparkline**: expose from Curator now (R1 backend touch) or defer
  (ship Sources+Coverage only in R1)? *Default: defer — keep R1 backend-free.*
- **Mobile graph**: entity-list fallback (recommended) vs a touch force-graph later?
- **Gating**: design the free/paid boundary in R1 (content split ready) even though Stripe
  (Phase 3) isn't wired? *Default: yes — structure it now, wire later.*
