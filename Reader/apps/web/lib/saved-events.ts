"use client";

/**
 * Saved-events store — localStorage for now (a signed-in profile later).
 * Mirrors lib/saved-outlooks.ts: one key holds an array of saved events,
 * keyed by event id. Powers the event chrome's Save toggle (Step C).
 */
export interface SavedEvent {
  id: string;
  headline: string;
  category: string | null;
  language: string;
  savedAt: number; // epoch ms
}

const KEY = "inkbytes:saved-events";

// Same-tab listeners (the storage event only fires cross-tab).
const EVT = "inkbytes:saved-events-changed";

function read(): SavedEvent[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function write(list: SavedEvent[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(list));
    window.dispatchEvent(new Event(EVT));
  } catch {
    /* quota / disabled — no-op */
  }
}

export function listSaved(): SavedEvent[] {
  return read().sort((a, b) => b.savedAt - a.savedAt);
}

export function isSaved(id: string): boolean {
  return read().some((s) => s.id === id);
}

/** Add or remove; returns the new saved state (true = now saved). */
export function toggleSaved(e: Omit<SavedEvent, "savedAt">): boolean {
  const list = read();
  const without = list.filter((s) => s.id !== e.id);
  if (without.length !== list.length) {
    write(without); // was saved → removed
    return false;
  }
  write([{ ...e, savedAt: Date.now() }, ...without]);
  return true;
}

export function clearSaved(): void {
  write([]);
}

export const SAVED_EVENT = EVT;
