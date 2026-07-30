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
