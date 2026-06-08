# ADR-R-0005 — force-dynamic for pages calling internal services + About page signature

> *Status: accepted · Owner: Julian · Date: 2026-06-07*

## Context

### 1. ISR bakes error state on pages that call internal Docker services

Next.js ISR (`export const revalidate = N`) pre-renders the page during
`docker build`. Inside a Docker build context the internal service hostnames
(e.g. `inkbytes-curator-api`) are not yet in any Docker network — they only
resolve at container runtime.

Result: the first render during build fetches a service that doesn't exist,
catches the error, and bakes the **error JSX** (`"Could not reach Curator"`)
into the static HTML. All subsequent requests are served the cached error until
the ISR interval expires — by which time it re-renders and succeeds, but the
initial page load is always broken.

This was observed on `/entities` which called `getGraph()` inside a `revalidate
= 120` page.

### 2. Founder signature on About page

The About page lacked a personal closing. A hand-written signature image was
provided to add warmth and authorship to the product story.

---

## Decisions

### 1. `export const dynamic = "force-dynamic"` for internal-service pages

Any Next.js page that calls an **internal Docker service** (reachable only
inside the running container network) must use:

```ts
export const dynamic = "force-dynamic";
```

This forces full SSR on every request, guaranteeing the hostname resolves at
request time inside the live container network rather than at build time.

**Scope rule:** pages that call only public URLs or static data can keep ISR.
Pages that call `inkbytes-curator-api`, `inkbytes-postgres`, or any other
`inkbytes-*` internal hostname must be `force-dynamic`.

**Currently affected:** `/entities` (entity graph), `/event/[id]` (already
`revalidate = 300` which is fine — event pages call the public-facing API URL,
not the internal hostname).

### 2. Founder signature: transparent PNG via PIL alpha-masking

The original image exported from the session had an RGB white background (no
alpha channel). PIL was used to convert to RGBA and mask all near-white pixels
(`R > 230 & G > 230 & B > 230 → alpha = 0`), producing a transparent PNG.

**File:** `public/signature.png` — 2000×667 RGBA PNG, displayed at `w=260`
in the About page with `select-none` to prevent accidental drag-selection.

**Placement:** Below the final paragraph of the About page, separated by a
`border-t` divider. Displays the image followed by `Julian De La Rosa — Founder`
in `text-xs text-[var(--ink-muted)]`.

---

## Alternatives considered

| Option | Rejected because |
|---|---|
| Keep `revalidate = 120` on /entities, fix hostname via build args | Build args can't inject a runtime hostname; the service genuinely doesn't exist during build |
| Use an ISR fallback page with `notFound()` | Still bakes a non-content page; force-dynamic is simpler and correct |
| Cache graph data in Redis / edge KV | Over-engineering for current scale; force-dynamic adds ~30ms vs the full entity graph query |
| SVG signature | A hand-drawn PNG is authentic; SVG tracing loses the personal quality |
| WebP signature | PNG was chosen for universal alpha support without re-encoding artifacts |

---

## Consequences

- `/entities` now SSRs on every request. The entity graph query is
  `O(nodes + edges)` on Postgres — fast, but adds ~50–100ms per load.
  Acceptable at current scale (<500 events, <1000 entities).
- Any future page added to the Reader that calls an internal service
  **must** default to `force-dynamic`. This is now the documented rule.
- `signature.png` is 32 KB (RGBA, un-compressed thumbnail). No `next/image`
  optimisation needed at this size.
