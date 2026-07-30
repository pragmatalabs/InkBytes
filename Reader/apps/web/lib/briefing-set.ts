"use client";

/**
 * Per-day briefing snapshot (Slice C-B follow-up). The home re-fetches live and
 * re-ranks by freshness, so an un-frozen top-N reshuffles through the day — a
 * finished story drops out, fresh unread ones enter, and "you're caught up"
 * never holds. This freezes the day's set: the first visit of a given day
 * captures the top-N event IDs; the rest of the day shows that same set (so the
 * reader can actually finish it). New stories flow to /browse. Resets when the
 * day (local YYYY-MM-DD) changes.
 */
const KEY = "inkbytes:briefing";

/** Read today's frozen briefing IDs (or [] if none / stale) — no side effects.
 *  Used to show a story's "BRIEFING n/m" position on the event page. */
export function readBriefingIds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const saved = raw ? JSON.parse(raw) : null;
    return saved && Array.isArray(saved.ids) ? (saved.ids as string[]) : [];
  } catch {
    return [];
  }
}

/** Return today's frozen set if present, else freeze `candidateIds` and return them. */
export function loadOrCreateBriefing(day: string, candidateIds: string[]): string[] {
  if (typeof window === "undefined") return candidateIds;
  try {
    const raw = window.localStorage.getItem(KEY);
    const saved = raw ? JSON.parse(raw) : null;
    if (saved && saved.day === day && Array.isArray(saved.ids) && saved.ids.length > 0) {
      return saved.ids as string[];
    }
    window.localStorage.setItem(KEY, JSON.stringify({ day, ids: candidateIds }));
    return candidateIds;
  } catch {
    return candidateIds;
  }
}

/**
 * Heal today's frozen set against the live feed and return up to `size` IDs.
 *
 * The plain freeze (loadOrCreateBriefing) only ever SHRINKS: as the morning's
 * stories age out of the feed window through the day, fewer of the frozen IDs
 * still resolve, so by evening the briefing dwindles to a handful (and its
 * sections collapse). This keeps the frozen members that are still present — in
 * their frozen order, so nothing the reader has been working through reshuffles —
 * then tops up from the current top-ranked IDs (freshness order) until the set
 * is full again, and PERSISTS the result so the backfilled stories stick too.
 *
 * `orderedCurrentIds` is the live feed's IDs in rank order (freshest first).
 */
export function reconcileBriefing(day: string, orderedCurrentIds: string[], size: number): string[] {
  const capped = orderedCurrentIds.slice(0, size);
  if (typeof window === "undefined") return capped;
  try {
    const raw = window.localStorage.getItem(KEY);
    const saved = raw ? JSON.parse(raw) : null;
    const frozen: string[] =
      saved && saved.day === day && Array.isArray(saved.ids) ? (saved.ids as string[]) : [];
    const present = new Set(orderedCurrentIds);
    const survivors = frozen.filter((id) => present.has(id));
    const have = new Set(survivors);
    const backfill = orderedCurrentIds.filter((id) => !have.has(id));
    const healed = [...survivors, ...backfill].slice(0, size);
    window.localStorage.setItem(KEY, JSON.stringify({ day, ids: healed }));
    return healed;
  } catch {
    return capped;
  }
}
