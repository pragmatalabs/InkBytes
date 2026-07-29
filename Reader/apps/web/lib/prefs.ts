"use client";

/**
 * Reader preferences — localStorage for now (a signed-in profile later).
 * Backs the You screen (Slice B2): default reading language + notification
 * toggles. The reading language is stored now; the feed/event defaults wire to
 * it in the briefing work (Slice C).
 */
export type Lang = "en" | "es";

export interface NotifPrefs {
  developing: boolean; // developing-story alerts
  followed: boolean; // updates on stories you follow
  briefing: boolean; // the daily briefing is ready
}

const LANG_KEY = "inkbytes:pref-lang";
const NOTIF_KEY = "inkbytes:pref-notif";
const EVT = "inkbytes:prefs-changed";

const DEFAULT_NOTIF: NotifPrefs = { developing: true, followed: true, briefing: false };

function emit() {
  window.dispatchEvent(new Event(EVT));
}

export function getLang(): Lang {
  if (typeof window === "undefined") return "en";
  return window.localStorage.getItem(LANG_KEY) === "es" ? "es" : "en";
}

export function setLang(lang: Lang): void {
  try {
    window.localStorage.setItem(LANG_KEY, lang);
    emit();
  } catch {
    /* quota / disabled — no-op */
  }
}

export function getNotif(): NotifPrefs {
  if (typeof window === "undefined") return DEFAULT_NOTIF;
  try {
    const raw = window.localStorage.getItem(NOTIF_KEY);
    return raw ? { ...DEFAULT_NOTIF, ...JSON.parse(raw) } : DEFAULT_NOTIF;
  } catch {
    return DEFAULT_NOTIF;
  }
}

export function setNotif(next: NotifPrefs): void {
  try {
    window.localStorage.setItem(NOTIF_KEY, JSON.stringify(next));
    emit();
  } catch {
    /* quota / disabled — no-op */
  }
}

export const PREFS_EVENT = EVT;
