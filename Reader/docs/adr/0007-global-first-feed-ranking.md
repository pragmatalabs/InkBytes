> *Status: v1 · Owner: Reader · Last updated: 2026-06-09*

# ADR-R-0007 — Global-first feed ranking: Reader changes

## Status

Accepted

## Context

See [Curator ADR-0017](../../Curator/docs/adr/0017-global-first-feed-ranking.md) for the
full system-level context. This ADR records the Reader-specific decisions.

The API now returns events ordered by `freshness_at + 6h bonus for global events`, and
includes a `has_global_outlet: boolean` field on each `EventSummary`.

## Decision

### 1. `importance()` mirrors the API sort

The previous `importance()` function in `feed-client.tsx` added `source_count * 1000 ms`
to freshness — effectively a no-op (2–5 seconds swamped by millisecond-level
`freshness_at` differences). It is replaced to mirror the API exactly:

```typescript
const GLOBAL_BONUS_MS = 6 * 60 * 60 * 1000;   // 6 h in milliseconds

function importance(ev: EventSummary): number {
  const bonus = ev.has_global_outlet ? GLOBAL_BONUS_MS : 0;
  return new Date(ev.freshness_at).getTime() + bonus;
}
```

Why mirror the API? The Reader appends pages of results with infinite scroll. When a new
page is appended and re-sorted client-side, it must use the same ordering function as the
server, otherwise items jump position on load.

### 2. "Regional" section divider in the stream

In the stream of events below the editorial cards, a lightweight divider is injected
before the first event that has `has_global_outlet === false` (i.e., the first
regional-only story). The divider renders a globe icon + "Regional" label in the same
muted-uppercase style used for other section headers.

Implementation: the `streamVisible` array is mapped with index; when the current item
is the first regional item (its predecessor was global, or it is at index 0), a
`<RegionalDivider>` block is rendered using `Fragment` above the `StreamRow`.

The divider appears at most once per page load — it marks the tier boundary, not each
individual regional item.

The editorial row (top story + secondary grid) is **not split** — it naturally contains
globally-ranked stories after the API fix and needs no divider.

### 3. `has_global_outlet` in `EventSummary` type

```typescript
/** True when at least one article came from a global-region outlet (AP, Reuters,
 *  BBC, CNN, NPR, etc.). Drives the +6 h freshness bonus in the API ORDER BY
 *  (ADR-0017) and the "Regional" section divider in the Reader. */
has_global_outlet: boolean;
```

## Consequences

- The feed sort in `feed-client.tsx` is now a true mirror of the API sort. No more
  invisible no-op additions.
- Users see a clear "Regional" label when the feed transitions from globally-covered
  stories to regional-only ones.
- If the API constant changes (6h → 3h), `GLOBAL_BONUS_MS` in `feed-client.tsx` must be
  updated to match.
- `has_global_outlet` is part of the `EventSummary` contract. If the Curator API ever
  drops it, the Reader type will generate a TypeScript compile error — intentional.

## Files changed

- `Reader/apps/web/lib/types.ts` — `has_global_outlet` field
- `Reader/apps/web/app/feed-client.tsx` — `importance()` rewrite; "Regional" divider
