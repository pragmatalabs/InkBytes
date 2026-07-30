# ADR-R-0013 — Adopt the InkBytes Reader Prototype mobile design

> *Status: accepted · Owner: Julian · Last updated: 2026-07-29*

## Context

Two claude.ai/design prototypes were produced for the Reader:

- **InkBytes Mobile.dc.html** (`8ee76f77…`) — a fuller product flow (onboarding,
  paywall, finite briefing, Browse, Saved, You).
- **InkBytes Reader.dc.html** (`1a76853a…`) — the reading-surface visual system:
  a finite mono-typographic briefing, per-screen navy chrome, a bottom nav of
  **Brief · Outlook · Browse · Entities** + a ☰ hamburger, and rich event/entity
  screens. Its `_ds/inkb-7695b19e…` design system documents the same tokens the
  Reader already ships (Inter, six core vars, procedural covers).

Julian asked to adopt the prototype look **mobile-first**, and — hard
constraints — **not** to use the Banreservas design system (the employer's, from
`InkBytes Mobile.dc.html`'s `_ds`), to **defer the paywall + onboarding**, and to
**keep DailySplash**. The redesign was built + verified stage-by-stage against
prod data (via an SSH tunnel to the prod Curator API).

## Decision

Re-skin the prototype into InkBytes' own tokens (Inter / `--accent #1a1a2e` /
`--accent-dot #e05c5c` / warm `--bg #fafaf9`), never Banreservas (Open Sans /
cyan). Concretely:

**Event page.** Serif synthesis (Source Serif 4) + category-accent drop cap; a
"This story" grid whose tiles open bottom-sheet **drawers** (Watch / Evidence /
Entities / Related) instead of inline sections; tappable `Source:` citation chips
that open the Evidence drawer focused on the source; an event chrome with a
`‹ BRIEFING n/m` position (from the frozen briefing set), EN/ES, Save, Share; a
`● DEVELOPING / CATEGORY` eyebrow; and a provenance row with
`N sources · N quotes`, a corroboration line (STRONG/MODERATE/LIMITED by source
count), and a `STARTED · UPDATED` mono clock.

**Home = a finite briefing** ("a briefing, not a feed"). A per-day **snapshot**
(`lib/briefing-set`, localStorage, day-keyed) freezes the top-N ranked events so
the set stops reshuffling and "you're caught up" holds; the home fetches ~60 (not
500) — enough for the top-N + the developing rail. The isBrief look: mono
dateline, a heavy weekday title, `N stories · ≈min · N read`, a **segmented**
progress strip, and two mono-ruled sections — `DEVELOPING NOW · N` (capped) and
`THE BRIEFING · N left` — over rail-cards with "READ" tags.

**Browse (`/browse`).** The full searchable/filterable feed (search, theme +
language filters, trending, the complete stream) — everything the finite home
leaves out. One `FeedClient` with a `mode` prop drives both.

**Navigation.** Bottom nav → **Brief · Outlook · Browse · Entities**; a ☰
**hamburger drawer** (`nav-menu.tsx`) holds Saved / Settings (`/you`) / About +
an EN/ES toggle; the header shows the current screen label + a boxed EN/ES
(hidden on `/event/*`, which has its own).

**Saved + You (localStorage; a profile later).** `/saved` (followed stories +
saved events + saved outlooks + followed entities) and `/you` = "Settings"
(reading language via `lib/prefs`, notification toggles, data counts + clear).
Save/Follow live in `lib/saved-events` / `lib/followed` / `lib/followed-entities`.

**Entities.** The `/entities` detail sheet + the event "Entities in this story"
drawer both match the prototype (colored avatars; 3-up `STORIES · LINKS · TODAY`;
Recent events; Connections). The **inside-news detail is its own component**
(`entity-detail-sheet.tsx`) opening as a stacked sub-sheet over the drawer,
fed by a new Curator endpoint (Curator ADR-0042) via `/api/entity/[id]`; it
degrades to a light sheet on 404.

## Consequences

- The home is now finite + typographic; discovery moved to `/browse`. The
  briefing snapshot means a story stays in the set for the day even as fresher
  ones arrive (they flow to Browse).
- Outlook + Entities become primary tabs; Saved + settings move into the ☰ menu.
- The event page keeps its own in-content `EventActionBar` below the global
  navy header (two bars on `/event/*`). Unifying them into the prototype's single
  morphing top-bar (chromeEvent) is deferred.
- All localStorage stores are per-origin; a signed-in profile later supersedes.
- Hydration safety preserved throughout: read-state, the briefing snapshot, the
  dateline, and per-screen labels render their server/first-paint value and fill
  after mount (the ADR-0004/Stage-6 pattern), so no React #418.

## Alternatives considered

- **The Mobile.dc.html nav (Briefing/Browse/Saved/You)** — shipped first (Slice
  C-B) then reversed to the Reader-prototype nav after a side-by-side compare;
  the two design files disagree on navigation and Julian chose this one.
- **Banreservas DS** — rejected by constraint (employer's system; InkBytes keeps
  its own identity).
- **Loading the full entity graph on the event page** to power the in-place
  entity sheet — rejected: the `/graph` query is ~20 s and heavy; a dedicated
  light endpoint (ADR-0042) is the right shape.
