/**
 * Read state — client-only, localStorage. Remembers which events the reader has
 * opened AND at what freshness_at, so a story that develops further after they
 * read it can resurface as "updated since you read it" (2026-07 mobile brief,
 * Stage 6). Storing the timestamp (not a boolean) is what makes that free.
 *
 * All reads are guarded for SSR (window undefined) and for disabled/blocked
 * storage — read state is a nicety, never load-bearing, so every path degrades
 * to "nothing read" rather than throwing.
 */

const KEY = "inkbytes-read"; // { [eventId]: freshness_at seen (ISO) }

export function getRead(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Record<string, string>) : {};
  } catch {
    return {};
  }
}

/** Record that the reader opened `id`, stamping the version (freshness_at) seen. */
export function markRead(id: string, freshnessAt: string): void {
  if (typeof window === "undefined") return;
  try {
    const m = getRead();
    // Only advance the stamp — never move it backwards.
    if (!m[id] || new Date(freshnessAt) > new Date(m[id])) {
      m[id] = freshnessAt;
      window.localStorage.setItem(KEY, JSON.stringify(m));
    }
  } catch {
    /* quota exceeded / storage disabled — non-fatal */
  }
}

/** True once the reader has opened this event (at any version). */
export function isRead(id: string, read: Record<string, string> = getRead()): boolean {
  return !!read[id];
}

/** True when the brief changed (newer freshness_at) after the reader last opened it. */
export function isUpdatedSinceRead(
  ev: { id: string; freshness_at: string },
  read: Record<string, string> = getRead(),
): boolean {
  const seen = read[ev.id];
  return !!seen && new Date(ev.freshness_at) > new Date(seen);
}
