"use client";

/**
 * Saved assistant conversations — the reader's personal "file drawer" for
 * chats with Ask InkBytes. localStorage for now (a signed-in profile later),
 * same shape/pattern as lib/saved-events. Capped so the drawer never bloats.
 */
export interface ChatSource {
  n: number;
  title: string;
  url: string;
  outlet?: string;
  // Router-card fields (1B) — /ask now returns these per cited event.
  event_id?: string;
  category?: string | null;   // broad theme → card accent
  source_count?: number;
  article_count?: number;
  freshness_at?: string | null;
  summary?: string;
}
/** Corpus coverage for an answer — "read from N events · M articles" (1B). */
export interface ChatCoverage { events: number; articles: number }
export interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  coverage?: ChatCoverage;
}
export interface SavedChat {
  id: string;
  title: string;      // derived from the first user question
  created: string;    // ISO
  messages: ChatMsg[];
}

const KEY = "inkbytes:chats";
const EVT = "inkbytes:chats-changed";
const MAX_CHATS = 50;

export const SAVED_CHATS_EVENT = EVT;

function emit() {
  try { window.dispatchEvent(new Event(EVT)); } catch { /* SSR */ }
}

function read(): SavedChat[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? (arr as SavedChat[]) : [];
  } catch {
    return [];
  }
}

function write(list: SavedChat[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX_CHATS)));
    emit();
  } catch {
    /* quota / disabled — no-op */
  }
}

/** Newest first. */
export function listChats(): SavedChat[] {
  return read().sort((a, b) => b.created.localeCompare(a.created));
}

export function getChat(id: string): SavedChat | null {
  return read().find((c) => c.id === id) ?? null;
}

/** Upsert by id — re-saving an updated conversation replaces it in place. */
export function saveChat(chat: SavedChat): void {
  const list = read().filter((c) => c.id !== chat.id);
  list.unshift(chat);
  write(list);
}

export function deleteChat(id: string): void {
  write(read().filter((c) => c.id !== id));
}

export function clearChats(): void {
  write([]);
}
