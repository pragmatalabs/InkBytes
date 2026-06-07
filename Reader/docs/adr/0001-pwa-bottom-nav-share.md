# ADR-R-0001 — PWA manifest, bottom navigation, and share button

> *Status: implemented · Owner: Julian de la Rosa · Last updated: 2026-06-07*

## Context

InkBytes is a news reader. As usage grows on mobile, users should be able to
add it to their home screen as a Progressive Web App (PWA) and get a
native-app feel: no browser chrome, bottom navigation, and a share button that
opens the native OS share sheet.

Three concerns in one change:

1. **Install prompt**: the browser only shows an "Add to Home Screen" prompt
   when a valid Web App Manifest is present.
2. **Navigation in standalone mode**: once the browser chrome (address bar)
   disappears, the header-only nav is invisible on small screens — a bottom
   tab bar is needed.
3. **Share**: a news reader's primary social action; should use the native OS
   share sheet on mobile for articles.

## Decision

### Manifest (`app/manifest.ts`)

Next.js 13+ app router generates `/manifest.webmanifest` automatically from a
`manifest.ts` file that exports a typed `MetadataRoute.Manifest` object. We
use:

- `display: "standalone"` — hides browser chrome when launched from home screen
- `theme_color: "#1a1a2e"` — matches `--accent` so the status bar blends in
- `background_color: "#fafaf9"` — matches `--bg` for the splash screen
- SVG icon (`/icon.svg`) as the primary icon; PNG 192/512 entries reference
  `/icon-192.png` / `/icon-512.png` which are **TODO** — placeholders for a
  future design pass. Their absence produces a 404 (non-fatal; browser falls
  back to SVG) but Android Chrome requires at least one PNG ≥ 192 px for the
  install prompt to fire reliably. Generate them with Inkscape/imagemagick from
  `icon.svg` and drop in `public/`.

### Bottom navigation (`app/bottom-nav.tsx`)

A `"use client"` component, fixed at the viewport bottom. Four tabs:

| Tab | Icon | Route | Notes |
|-----|------|-------|-------|
| News | house | `/` | active when `pathname === "/"` |
| Search | magnifier | `/?search=1` | tap focuses `<input>` if already on "/" |
| Entities | graph | `/entities` | |
| About | info circle | `/about` | |

Design choices:
- `md:hidden` — hidden on desktop; the sticky header nav handles that tier
- `h-[58px]` fixed height + `env(safe-area-inset-bottom)` padding via inline style — the CSS `env()` function requires `viewport-fit=cover` in the viewport tag to work on iOS
- A `.bottom-nav-spacer` div at the end of `<main>` (defined in `globals.css`) adds the same `calc(58px + env(safe-area-inset-bottom))` space so the last content line is never hidden under the bar
- **Smart search tap**: when the user is already on `/`, tapping Search focuses the `<input type="text">` on the page and smooth-scrolls to it instead of navigating away. Uses `document.querySelector` directly (safe — only called client-side on button click).

### Share button (`app/event/[id]/share-button.tsx`)

A `"use client"` component placed in the top action bar of every event page,
right-aligned opposite the ← back link.

Flow:
1. Try `navigator.share({ title, text, url })` — opens native OS share sheet
   (iOS Safari, Android Chrome, macOS Ventura+, Windows Edge)
2. If `navigator.share` is absent or the user cancels — fall through to
   `navigator.clipboard.writeText(url)`
3. Show ✓ **Shared!** / ✓ **Copied!** state for 2 s, then reset

The `text` parameter is pre-filled with the first sentence of the synthesis so
sharing produces a meaningful preview on messaging apps.

### Viewport (`layout.tsx`)

Next.js 16 separates `viewport` from `metadata`. We export:

```typescript
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",   // ← required for env(safe-area-inset-bottom) on iOS
  themeColor: "#1a1a2e",
};
```

`appleWebApp` metadata (`capable: true`, `statusBarStyle: "black-translucent"`)
makes the status bar overlay the app background rather than boxing it — needed
for the full-bleed hero images in event pages to look good.

## Consequences

+ Browser install prompt appears on Chrome/Edge/Android; Safari shows "Add to
  Home Screen" in the share sheet.
+ Home-screen-launched sessions get full-screen UI with native bottom tabs.
+ Every event page has a one-tap share action that degrades gracefully to
  clipboard copy on any platform.
+ `env(safe-area-inset-bottom)` CSS is only respected when `viewport-fit=cover`
  is set — both must be present or the bottom nav overlaps the home indicator.
- PNG icons (`/icon-192.png`, `/icon-512.png`) are missing — Android may not
  show the "Add to Home Screen" banner until they're added.
- The footer is hidden on mobile (redundant when the bottom nav is present).
  Desktop shows it normally.

## Future work

- Generate `/public/icon-192.png` and `/public/icon-512.png` from `icon.svg`
  (Inkscape CLI: `inkscape --export-type=png --export-width=192 icon.svg`).
- Add `apple-touch-icon` link tag (180 px PNG) for iOS home screen icons.
- Service worker + offline caching for the last-read event pages.
