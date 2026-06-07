# ADR-R-0002 — InkBytes Icon System

> *Status: accepted · Owner: julian · Last updated: 2026-06-07*

## Context

The Reader needed a consistent visual icon system for:
1. **Bottom navigation** (4 tabs: News, Search, Entities, About) — previously hand-drawn 24×24 SVGs
2. **Category filter tabs** (9 categories in the feed header) — previously plain emoji
3. **CategoryChip labels** on event cards — previously plain text pills

The project ships with a licensed professional icon set (`/Users/.../Downloads/InkBytes Media/Iconset/`) comprising ~14 packs and ~324 SVGs across multiple styles (Line, Solid, Gradient, Duotone, AI-rendered).

## Decision

Extract 15 curated SVGs from the icon set, convert to React components with `stroke="currentColor"`, and serve them as a typed component library at `Reader/apps/web/components/icons.tsx`.

### Icon selection

| Component | Source set | Source file | Used for |
|---|---|---|---|
| `NewspaperIcon` | breaking-news-icon-set | `9. News paper.svg` | Nav → News tab |
| `SearchIcon` | computer-technology-icon-set | `21 magnifying glass.svg` | Nav → Search tab |
| `NetworkIcon` | artificial-intelligent-icon-set | `24 network.svg` | Nav → Entities tab |
| `InfoIcon` | help-center-icon-set | `7 info.svg` | Nav → About tab |
| `GlobalNewsIcon` | breaking-news-icon-set | `3. Global news.svg` | Category: world |
| `FinancialDataIcon` | money-icon-set | `15. Financial data.svg` | Category: business |
| `AIIcon` | artificial-intelligent-icon-set | `1 ai.svg` | Category: technology |
| `FootballIcon` | sport-icon-set | `15. Football.svg` | Category: sports |
| `HelpIcon` | help-center-icon-set | `5 help.svg` | Category: health |
| `ChargingIcon` | electrical-vehicle-icon-set | `Charging.svg` | Category: environment |
| `ImageMediaIcon` | breaking-news-icon-set | `25. Image media.svg` | Category: culture |
| `OfficialAnnouncementIcon` | breaking-news-icon-set | `12. Official announcement.svg` | Category: politics |
| `TrendingNewsIcon` | breaking-news-icon-set | `13. Trending news.svg` | Feed badge |
| `LiveReportIcon` | breaking-news-icon-set | `6. Live report.svg` | Feed badge |
| `HotNewsIcon` | breaking-news-icon-set | `4. Hot news.svg` | Feed badge |

### Color strategy

All source SVGs use hardcoded stroke colors (`stroke: #010101` or `stroke: #001d3d`). These are replaced with `stroke="currentColor"` on the `<svg>` element so icons inherit the surrounding CSS `color` property — enabling active/inactive states, theme colors, and dark mode without additional code.

The green-energy-solid icon set was **excluded**: its icons use multi-color `fill` attributes (`#169fdb`, `#213a74`) and cannot be trivially made monochrome. The EV `Charging.svg` from the electrical-vehicle set was used for the environment/climate category instead (stroke-based, fits the clean energy theme).

### Why React SVG components (not `<img>` or CSS sprites)

- **`<img>` tags**: Cannot be recolored via CSS `color` — nav active state and hover tints would require duplicate icons or CSS filter hacks.
- **CSS sprites / icon fonts**: Added toolchain complexity; harder to update individual icons.
- **Inline JSX SVG components**: Zero extra requests, CSS-colorable via `currentColor`, tree-shakeable, fully typed.

### Convenience export

`CategoryIcon` accepts a `category` string and renders the correct icon — or `null` for unknown categories. This keeps category rendering logic in one place.

## Consequences

- All 9 category types now have a visual SVG identity in the filter bar and card chips.
- Nav icons are from the licensed icon set, visually consistent with category icons.
- `TrendingNewsIcon`, `LiveReportIcon`, `HotNewsIcon` are available for future feed-badge use (Developing strip, hot-stories ribbon).
- Adding new icons requires reading the source SVG, stripping the `<defs><style>` block, and adding a new export — no external tooling needed.
- The source SVG files live at `~/Downloads/InkBytes Media/Iconset/` (not committed). To re-extract, follow the selection table above.

## Status

- [x] `components/icons.tsx` created with 15 icons + `CategoryIcon` helper
- [x] `bottom-nav.tsx` updated — 4 nav icons from icon set
- [x] `feed-client.tsx` updated — category filter tabs + `CategoryChip` use icons
- [ ] Feed badges (`TrendingNewsIcon`, `LiveReportIcon`, `HotNewsIcon`) wired to the breaking/hot/live strips
- [ ] PWA icon.svg — replace placeholder with a proper InkBytes logotype SVG
