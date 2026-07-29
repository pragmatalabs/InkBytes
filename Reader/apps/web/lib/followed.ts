"use client";

/**
 * Followed-stories store — localStorage for now (a signed-in profile later).
 * Distinct from lib/saved-events: Save = read-later/offline; Follow = subscribe
 * to a story's updates (the Saved screen surfaces followed items with an
 * "Updated" badge — Slice B). Mirrors the saved-events shape.
 */
export interface FollowedStory {
  id: string;
  headline: string;
  category: string | null;
  language: string;
  followedAt: number; // epoch ms
}

const KEY = "inkbytes:followed";

// Same-tab listeners (the storage event only fires cross-tab).
const EVT = "inkbytes:followed-changed";

function read(): FollowedStory[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function write(list: FollowedStory[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(list));
    window.dispatchEvent(new Event(EVT));
  } catch {
    /* quota / disabled — no-op */
  }
}

export function listFollowed(): FollowedStory[] {
  return read().sort((a, b) => b.followedAt - a.followedAt);
}

export function isFollowed(id: string): boolean {
  return read().some((s) => s.id === id);
}

/** Add or remove; returns the new followed state (true = now following). */
export function toggleFollowed(e: Omit<FollowedStory, "followedAt">): boolean {
  const list = read();
  const without = list.filter((s) => s.id !== e.id);
  if (without.length !== list.length) {
    write(without); // was followed → unfollowed
    return false;
  }
  write([{ ...e, followedAt: Date.now() }, ...without]);
  return true;
}

export function clearFollowed(): void {
  write([]);
}

export const FOLLOWED_EVENT = EVT;
