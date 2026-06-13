# Reader ADR-0008 — Animated ink-shader splash background

> *Status: accepted · Owner: Julian · Date: 2026-06-12*

## Context

The daily "Morning Briefing" splash (ADR-0007) sat on a flat `--accent` navy
field. We had a design prototype ("Shader wallpapers") of a WebGL calligraphic
ink/smoke effect and wanted it as the splash backdrop — alive, on-brand, and
interactive — without disturbing the splash's content or gating logic.

## Decision

Vendor the prototype's `InkWall` WebGL1 engine and run it as an absolute
background layer behind the splash content.

- **Engine** (`lib/ink-shader.js`): curl-noise velocity field advecting a
  scalar ink-density field in ping-pong half-float textures; per-palette
  colour ramp + grain + vignette in the display pass. Adapted for React:
  per-instance `start()` / `destroy()` instead of the prototype's single
  global rAF loop. **`destroy()` must NOT call `WEBGL_lose_context.loseContext()`**
  — that permanently poisons the `<canvas>`, so a remount (React StrictMode
  double-invoke in dev, or any re-render) fails shader compilation. Deleting
  GPU resources + cancelling rAF is sufficient; the browser reclaims the
  context when the canvas leaves the DOM.

- **Brand palette (5)**: deep navy field + luminous **indigo** primary ink,
  tuned to `--accent #1a1a2e`. A second **coral** ink stream (`--accent-dot`
  family) drifts on an independent Lissajous path — a separate density channel
  (green) with its own emitter (`uEmit2`), blended over the indigo in the
  display pass. Two brand colours (navy/indigo + red/coral) moving
  independently.

- **Wrapper** (`components/ink-shader-bg.tsx`): owns the canvas lifecycle,
  wires drag/touch to stir the ink, cleans up on unmount.

- **Splash integration** (`components/daily-splash.tsx`): canvas behind the
  content + radial/linear legibility scrims; the content wrapper is
  `pointer-events-none` so drags reach the ink, while the close / Read-now /
  Don't-show-again controls opt back in with `pointer-events-auto`.

### Reduced motion

Earlier iteration skipped the shader entirely under
`prefers-reduced-motion` → a blank navy splash for the many users who enable
it ("I don't see the ink"). **Decision (Julian): everyone gets a gentle, slow
drift — no frozen frame.** It's a soft ambient flow (low advection `speed`),
not vestibular parallax/zoom; reduced-motion users get an even slower speed as
a courtesy. WebGL-unavailable still falls back to the solid `--accent` bg.

### Tuning

Density must stay **dark-dominant** so white foreground text is legible:
a strong drifting emitter keeps luminous ribbons on screen at all times while
the field's baseline stays low (steady-state ≈ `ambient/(1−dissip)`). The
coral blend strength + glow are capped so peak coral frames never wash out the
headline.

## Consequences

- Mobile-only (`md:hidden`), shown once/24h via the existing splash gate — the
  WebGL cost is bounded to that one view and the context is released on
  dismiss.
- Palette is a single prop (`palette={5}`); switching to cyber (2) / iridescent
  (3) / ink-blue (1) is one line.
- Verified in mobile preview: two colours drift independently, animation
  confirmed across frames, text legible, drag-to-stir works, Read-now
  dismisses; tsc + production build clean.
