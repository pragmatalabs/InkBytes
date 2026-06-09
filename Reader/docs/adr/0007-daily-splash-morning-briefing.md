# ADR-0007 — Daily Splash ("Morning Briefing")

> *Status: accepted · Owner: Julián · Last updated: 2026-06-09*

## Context

Design handoff `InkBytes Media/design_handoff_daily_splash` (Variation A)
specified a **mobile-only daily splash**: a full-screen "welcome back" shown
once per 24h over the home feed — time-of-day greeting, reading streak, and
"what's new since yesterday" grouped by category, with a "Don't show again"
opt-out.

The handoff is a HTML/Babel prototype using its own tokens (`--m-navy`,
`--m-blue`, Poppins, IBM Plex Mono, a placeholder logo). The brief explicitly
says to **recreate it in the target codebase using the Reader's real
design-system**, not ship the prototype.

## Decision

Build the splash as a client overlay on the Reader's real primitives.

### Design-system binding (prototype → real Reader)

| Prototype | Reader (shipped) |
|---|---|
| Poppins / IBM Plex Mono | **Inter** (`--font-inter`, inherited from `body`) |
| `InkBytes-Logo-White.svg` | the real **`<LogoMark>`** (`components/logo.tsx`, `currentColor`) |
| `--m-navy #152028` background | **`--accent` #1a1a2e** |
| `--m-blue #007dfc` (CTA, counts, dot) | **`--accent-dot` #e05c5c** for the streak dot + `+N` counts; **white pill / navy text** CTA (inverse of the Reader's standard navy button). The Reader has no bright-blue brand colour, so the prototype's blue was re-expressed in the Reader's real accent language. |
| fake iOS status bar | none — real PWA draws the OS bar; the overlay uses `.safe-top` and sits at `z-[60]` (above the bottom nav's `z-50`). |

Entrance: `animate-splash-in` (fade + 10px rise, 0.42s), disabled under
`prefers-reduced-motion` — mirrors the existing `animate-slide-up` convention.

### Real data, not faked

There is no backend user model, so rather than invent numbers:

- **Streak** = distinct local calendar days the reader is opened, tracked in
  `localStorage` (`inkbytes.streak.v1 {lastDay,count}`). +1 on the day after
  `lastDay`, resets on a skipped day. Honest local data.
- **"Since yesterday" counts** = events whose `freshness_at` is within the last
  24h, grouped by `category`, top 4 desc — computed from the live `events`
  array the feed already loads (no new endpoint). Total drives the "N stories"
  label. When nothing is new, the list is replaced by a "You're all caught up"
  line.
- **Greeting / date** = the reader's local clock.

### Gate

`inkbytes.splash.v1 {lastShown,neverShow}`. `shouldShow()` returns true if never
shown or ≥24h since `lastShown`; "Read now" / × call `markShown()`; "Don't show
again" calls `setNeverShow()`. Rolling 24h window (not calendar-day).

### Placement

Mounted inside `FeedClient` (`<DailySplash events={events} />`) so it only
appears over the home feed and has the event data for counts. `md:hidden` —
mobile only. The show-decision and all storage/clock reads run in a mount
`useEffect` (never during render) so SSR and first client paint both render
`null`, avoiding hydration mismatch.

## Files

- `lib/splash.ts` — gate, local streak, briefing computation, greeting/date (pure, SSR-safe).
- `components/daily-splash.tsx` — the overlay (client component).
- `app/feed-client.tsx` — mounts `<DailySplash>` over the feed.
- `app/globals.css` — `splash-in` keyframe.

## Consequences

- No backend or schema change; counts/streak are derived client-side. If a real
  per-user model arrives later, swap the localStorage streak + 24h-window counts
  for server values behind the same `Briefing` shape.
- "Since yesterday" is a rolling 24h window keyed on `freshness_at`. An event
  that merely *updated* (new article) within 24h counts as new — acceptable for
  a "what changed" digest.
- `?resetSplash` re-arms the gate in **development only** (inert in production) —
  a testing aid, not a shipped control. The prototype's on-screen reset button
  was not ported.
- ESLint `react-hooks/set-state-in-effect` fires on the mount effect — the same
  pre-existing pattern as `feed-client.tsx`; Next 16's build does not gate on
  ESLint, and the effect is the correct way to read client-only state on mount.

## Alternatives considered

- **Mount globally in `layout.tsx`** (like the PWA banner): rejected — the
  splash needs the home feed's event list for counts and should only appear over
  the feed, not every route.
- **Fake the streak / counts**: rejected — misleading in production. A real
  local streak + live event counts are available without a backend.
- **Keep the prototype's blue accent**: rejected — not a Reader brand colour;
  re-expressed via `--accent` / `--accent-dot` per the handoff's instruction to
  use the real design system.
