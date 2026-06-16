/**
 * Daily-splash gate + local reading streak + "since yesterday" briefing.
 *
 * Pure, client-only helpers (guard every localStorage access — these are
 * imported into a "use client" component but must never throw during SSR).
 *
 * Design ref: InkBytes Media/design_handoff_daily_splash (Variation A).
 * Adapted to the Reader's real design system: Inter, LogoMark, --accent navy,
 * --accent-dot red. The streak and counts are REAL (local + live events), not
 * faked — there is no backend user model, so the streak is computed from the
 * distinct local calendar days the reader is opened.
 */
import type { EventSummary } from "@/lib/types";

const DAY = 24 * 60 * 60 * 1000;

// ── 24-hour gate ──────────────────────────────────────────────────────────────
const GATE_KEY = "inkbytes.splash.v1";
type GateState = { lastShown?: number; neverShow?: boolean };

function readGate(): GateState {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(GATE_KEY) || "{}") as GateState;
  } catch {
    return {};
  }
}
function writeGate(s: GateState): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(GATE_KEY, JSON.stringify(s));
  } catch {
    /* storage disabled — splash simply shows every launch, harmless */
  }
}

export const splashGate = {
  /** Call on home mount. Show once per 24h; never after opt-out. */
  shouldShow(now: number = Date.now()): boolean {
    const s = readGate();
    if (s.neverShow) return false;
    if (!s.lastShown) return true;
    return now - s.lastShown >= DAY;
  },
  /** "Read now" / close → counts as seen today. */
  markShown(now: number = Date.now()): void {
    const s = readGate();
    s.lastShown = now;
    writeGate(s);
  },
  /** "Don't show again" → permanent opt-out. */
  setNeverShow(): void {
    const s = readGate();
    s.neverShow = true;
    writeGate(s);
  },
  /** Dev/testing only — re-arm the gate (used behind ?resetSplash in dev). */
  reset(): void {
    if (typeof window === "undefined") return;
    try {
      localStorage.removeItem(GATE_KEY);
    } catch {
      /* ignore */
    }
  },
};

// ── Local reading streak (real, not faked) ──────────────────────────────────────
const STREAK_KEY = "inkbytes.streak.v1";
type StreakState = { lastDay?: string; count?: number };

/** Local calendar day as YYYY-MM-DD (not UTC — streak is about the reader's day). */
function dayKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * Record an app-open for `now` and return the current consecutive-day streak.
 * Idempotent within a calendar day. +1 when opened on the day after `lastDay`,
 * resets to 1 when a day was skipped, starts at 1 on first ever open.
 */
export function bumpStreak(now: Date = new Date()): number {
  if (typeof window === "undefined") return 0;
  let s: StreakState = {};
  try {
    s = JSON.parse(localStorage.getItem(STREAK_KEY) || "{}") as StreakState;
  } catch {
    s = {};
  }
  const today = dayKey(now);
  if (s.lastDay === today) return s.count || 1; // already counted today

  const yesterday = dayKey(new Date(now.getTime() - DAY));
  const next: StreakState = {
    lastDay: today,
    count: s.lastDay === yesterday ? (s.count || 0) + 1 : 1,
  };
  try {
    localStorage.setItem(STREAK_KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
  return next.count!;
}

// ── Briefing content (real, from the live event list) ───────────────────────────
export interface CatCount {
  key: string;
  label: string;
  n: number;
}
export interface Briefing {
  total: number;
  cats: CatCount[];
}

/** Reader's canonical category labels (mirrors feed-client.tsx CATEGORIES). */
const CATEGORY_LABELS: Record<string, string> = {
  politics: "Politics",
  business: "Business",
  technology: "Tech",
  sports: "Sports",
  health: "Health",
  environment: "Climate",
  culture: "Culture",
  world: "World",
  // ADR-0032 item 1 — 7 added themes.
  science: "Science",
  entertainment: "Entertainment",
  crime: "Crime",
  education: "Education",
  lifestyle: "Lifestyle",
  religion: "Religion",
  disaster: "Disaster",
};

/**
 * Count events whose `freshness_at` is within the last 24h, grouped by category.
 * Returns the total plus the top categories (desc by count). All real data.
 */
export function computeBriefing(
  events: EventSummary[],
  now: number = Date.now(),
  topN: number = 4,
): Briefing {
  const since = now - DAY;
  const byCat: Record<string, number> = {};
  let total = 0;
  for (const e of events) {
    const t = new Date(e.freshness_at).getTime();
    if (!Number.isFinite(t) || t <= since) continue;
    const key = e.category ?? "world";
    byCat[key] = (byCat[key] || 0) + 1;
    total++;
  }
  const cats = Object.entries(byCat)
    .map(([key, n]) => ({ key, label: CATEGORY_LABELS[key] ?? "World", n }))
    .sort((a, b) => b.n - a.n)
    .slice(0, topN);
  return { total, cats };
}

/** Time-of-day greeting from the reader's local clock. */
export function greetingFor(d: Date = new Date()): string {
  const h = d.getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

/** Long local date, e.g. "Friday, January 5, 2023". */
export function longDate(d: Date = new Date()): string {
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}
