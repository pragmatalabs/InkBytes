"use client";

import type { EntityType } from "@/lib/types";

/**
 * Followed-entities store — localStorage for now (a signed-in profile later).
 * Companion to lib/followed (stories): following a person/org/place/topic from
 * the entity detail sheet surfaces it in the Saved screen (Slice B3). Mirrors
 * the same shape + change-event pattern.
 */
export interface FollowedEntity {
  id: string; // GraphNode.id — lowercased entity name, stable key
  label: string;
  type: EntityType;
  followedAt: number; // epoch ms
}

const KEY = "inkbytes:followed-entities";
const EVT = "inkbytes:followed-entities-changed";

function read(): FollowedEntity[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function write(list: FollowedEntity[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(list));
    window.dispatchEvent(new Event(EVT));
  } catch {
    /* quota / disabled — no-op */
  }
}

export function listFollowedEntities(): FollowedEntity[] {
  return read().sort((a, b) => b.followedAt - a.followedAt);
}

export function isFollowedEntity(id: string): boolean {
  return read().some((e) => e.id === id);
}

/** Add or remove; returns the new followed state (true = now following). */
export function toggleFollowedEntity(e: Omit<FollowedEntity, "followedAt">): boolean {
  const list = read();
  const without = list.filter((x) => x.id !== e.id);
  if (without.length !== list.length) {
    write(without); // was followed → unfollowed
    return false;
  }
  write([{ ...e, followedAt: Date.now() }, ...without]);
  return true;
}

export function clearFollowedEntities(): void {
  write([]);
}

export const FOLLOWED_ENTITIES_EVENT = EVT;
