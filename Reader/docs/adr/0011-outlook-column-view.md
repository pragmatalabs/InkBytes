# ADR-R-0011 — The Column view: Outlook pages as editorial objects (masthead, glyphs, functional citations)

> *Status: v1 · **DEPLOYED + verified live 2026-07-12** · Owner: Julian · Date: 2026-07-12*

## Context

The first Outlook surface (ADR-0008 / Outlook v1.1) shipped feature-complete but
dressed the column as a *tool*: five rows of chrome before the first sentence, a
four-pill toolbar (Share/Copy/Export/Print) between headline and prose, the
persona — the actual product — in 11px gray, ISO dates ("2026-07-11"), plain-text
`[n]` citations the reader had to eye-match against a flat footnote list, the
archive as raw ISO links at the page bottom, and a dead end after reading (back →
index → choose again). Julian asked for a UI/UX pass "Bauhaus/Apple mindset".

Principles applied: the persona is structural, not metadata; one loud element per
screen (the headline); utilities after reading; typography as the material;
geometric reduction; the theme-color system doing identity work.

## Decision

1. **Masthead** (`/outlook/[topic]`): persona glyph disc in the theme accent +
   persona name in small caps + "Technology · 11 de julio de 2026 · 2 min"
   (localized long dates, computed read time) + a 2px theme rule — the page's
   only ornament. `lib/theme-colors.ts` is the single accent source (15 themes).
2. **Persona glyph system** (`components/persona-icons.tsx`): 15 hand-authored
   monochrome SVG icons + El Editor fallback — one physical metaphor per persona
   name (La Mesa = round table top-down, El Balance = two-pan scale, El Pulso =
   EKG, La Alerta = beacon…). 24px grid, 2px round stroke, primitives only,
   `currentColor` tint. No image assets; used in the masthead, the
   "more outlooks" cards, and the index cards.
3. **Functional citations**: the editorial's `[n]` markers arrive as plain text;
   the page resolves each against the timeline (same-order contract) and renders
   a real superscript link in the theme accent to the cited event
   (`.outlook-body a[href^="/event/"]` CSS). Citations became navigation, not
   decoration.
4. **Edition strip**: weekday/day chips beside the masthead (context selection
   lives with context), active chip in theme color — replaces footer ISO links.
5. **Utilities demoted**: the actions row renders after the article. ES/EN is a
   segmented pill.
6. **Timeline as a rail**: circled theme-colored numbers matching the in-text
   citations, headline + recency/sources per item.
7. **No dead ends**: "More outlooks today" — a snap-row of the other personas'
   columns; the 15 verticals read as one continuous morning paper.
8. **Index**: persona-glyph cards with theme accents; latest day 2-col on ≥sm.
9. Article measure capped at 65ch; headline up to 2.5rem; the drop cap and 1.8
   leading (the v1 strengths) kept.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Generated/asset icons for personas | 16 metaphors this simple are better as hand-authored inline SVG — crisp at any size, tinted for free, zero pipeline. |
| Keep actions under the headline | Utilities at the most valuable screen position; export-before-reading is not a real intent. |
| Initials monograms (interim) | Shipped briefly; glyphs carry the metaphor and differentiate personas at a glance. |
| Linkify citations in Curator | Presentation concern; the Reader owns it (timeline order is already the API contract). |

## Consequences

- The persona system is now visual identity: recognizable, collectible columns.
- Citations are tappable evidence — strengthens the "synthesis you can verify"
  product claim on the most editorial surface.
- Dev gotcha recorded while verifying: Next's on-disk fetch cache
  (`.next/cache/fetch-cache`) survives dev-server restarts and served a
  nine-day-old edition; same fetch-cache class as the /entities lesson
  (docs/lessons-learned.md 2026-07-12).
