"use client";

/**
 * Saved-outlooks store — localStorage for now (a signed-in profile later).
 * One key holds an array of saved editions; entries are keyed by
 * theme+lang+date so a column/day/language is saved once.
 */
export interface SavedOutlook {
  theme: string;
  lang: string;
  date: string;      // edition_date (YYYY-MM-DD)
  headline: string;
  persona: string;   // reader display name, e.g. "El Circuito"
  savedAt: number;   // epoch ms
}

const KEY = "inkbytes:saved-outlooks";

// Notify same-tab listeners (the storage event only fires cross-tab).
const EVT = "inkbytes:saved-outlooks-changed";

function read(): SavedOutlook[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function write(list: SavedOutlook[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(list));
    window.dispatchEvent(new Event(EVT));
  } catch {
    /* quota / disabled — no-op */
  }
}

const idOf = (o: { theme: string; lang: string; date: string }) =>
  `${o.theme}::${o.lang}::${o.date}`;

export function listSaved(): SavedOutlook[] {
  return read().sort((a, b) => b.savedAt - a.savedAt);
}

export function isSaved(o: { theme: string; lang: string; date: string }): boolean {
  const id = idOf(o);
  return read().some((s) => idOf(s) === id);
}

/** Add or remove; returns the new saved state (true = now saved). */
export function toggleSaved(o: Omit<SavedOutlook, "savedAt">): boolean {
  const id = idOf(o);
  const list = read();
  const existing = list.filter((s) => idOf(s) !== id);
  if (existing.length !== list.length) {
    write(existing);          // was saved → removed
    return false;
  }
  write([{ ...o, savedAt: Date.now() }, ...existing]);
  return true;
}

export function removeSaved(o: { theme: string; lang: string; date: string }): void {
  const id = idOf(o);
  write(read().filter((s) => idOf(s) !== id));
}

export const SAVED_EVENT = EVT;
