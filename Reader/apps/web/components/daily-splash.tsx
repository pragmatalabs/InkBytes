"use client";

/**
 * Daily splash — "Morning Briefing" (Variation A).
 *
 * A mobile-only, full-screen "welcome back" shown once per 24h over the home
 * feed: time-of-day greeting, the reader's local streak, and "what's new since
 * yesterday" grouped by category. Dismissed via Read now / × / Don't show again.
 *
 * Built on the Reader's real design system: Inter (inherited), <LogoMark>,
 * --accent (navy) background, --accent-dot (red) for the streak dot + counts,
 * a white CTA pill (inverse of the standard navy button). No fake status bar —
 * it sits under the OS status bar via .safe-top, above the bottom nav (z-60).
 */
import { useEffect, useState } from "react";
import { LogoMark } from "@/components/logo";
import type { EventSummary } from "@/lib/types";
import {
  splashGate,
  bumpStreak,
  computeBriefing,
  greetingFor,
  longDate,
  type Briefing,
} from "@/lib/splash";

interface Props {
  events: EventSummary[];
}

export function DailySplash({ events }: Props) {
  const [open, setOpen] = useState(false);
  const [greeting, setGreeting] = useState("");
  const [date, setDate] = useState("");
  const [streak, setStreak] = useState(0);
  const [briefing, setBriefing] = useState<Briefing>({ total: 0, cats: [] });

  // Client-only: gate check, streak bump, and content all derive from the
  // browser (local time + localStorage). Rendering null on the server and on
  // the first client paint avoids any hydration mismatch.
  useEffect(() => {
    // Dev-only testing aid: ?resetSplash re-arms the gate. Inert in production.
    if (
      process.env.NODE_ENV !== "production" &&
      new URLSearchParams(window.location.search).has("resetSplash")
    ) {
      splashGate.reset();
    }

    // Streak is independent of the gate — count the open even if the splash
    // is suppressed, so the count stays accurate.
    setStreak(bumpStreak());

    if (!splashGate.shouldShow()) return;

    const now = new Date();
    setGreeting(greetingFor(now));
    setDate(longDate(now));
    setBriefing(computeBriefing(events, now.getTime()));
    setOpen(true);
  }, [events]);

  if (!open) return null;

  // Read now / × → seen today, dismiss (stay on the feed, scroll to top).
  const dismiss = () => {
    splashGate.markShown();
    setOpen(false);
    if (typeof window !== "undefined") window.scrollTo({ top: 0 });
  };
  const never = () => {
    splashGate.setNeverShow();
    setOpen(false);
  };

  const showList = briefing.total > 0 && briefing.cats.length > 0;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Daily briefing"
      className="fixed inset-0 z-[60] flex flex-col overflow-hidden bg-[var(--accent)] text-white safe-top md:hidden animate-splash-in"
    >
      <div className="flex flex-1 flex-col px-7 pb-8 pt-2 min-h-0">
        {/* Header: brand lockup + close */}
        <div className="flex items-center justify-between pt-2">
          <span className="inline-flex items-center gap-2">
            <LogoMark className="h-6 w-auto text-white" />
            <span className="text-[15px] font-semibold tracking-tight">InkBytes</span>
          </span>
          <button
            type="button"
            onClick={dismiss}
            aria-label="Close"
            className="flex h-[38px] w-[38px] items-center justify-center rounded-full bg-white/[0.14] backdrop-blur-sm transition hover:bg-white/20 active:scale-95"
          >
            <svg width="15" height="15" viewBox="0 0 15 15" aria-hidden="true">
              <path d="M2 2l11 11M13 2L2 13" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Center block */}
        <div className="flex flex-1 flex-col justify-center">
          <div className="text-[40px] font-medium leading-[1.04] tracking-[-0.01em]">
            {greeting}
          </div>
          <div className="mt-2.5 text-[15px] text-white/80">{date}</div>

          {streak > 0 && (
            <div className="mt-4">
              <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3.5 py-2 text-[13px] font-medium ring-1 ring-inset ring-white/[0.14]">
                <span
                  className="h-[7px] w-[7px] rounded-full bg-[var(--accent-dot)]"
                  style={{ boxShadow: "0 0 0 3px color-mix(in oklab, var(--accent-dot) 30%, transparent)" }}
                />
                {streak}-day streak
              </span>
            </div>
          )}

          {showList ? (
            <>
              <div className="mt-[34px] flex items-center justify-between text-[11px] font-semibold uppercase tracking-[0.09em] text-white/60">
                <span>What&rsquo;s new since yesterday</span>
                <span>
                  {briefing.total} {briefing.total === 1 ? "story" : "stories"}
                </span>
              </div>
              <div className="mt-1.5">
                {briefing.cats.map((c) => (
                  <div
                    key={c.key}
                    className="flex items-baseline justify-between border-t border-white/10 py-[15px]"
                  >
                    <span className="text-[19px] font-medium">{c.label}</span>
                    <span className="text-[14px] tabular-nums text-[var(--accent-dot)]">
                      +{c.n}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="mt-[34px] text-[15px] text-white/70">
              You&rsquo;re all caught up — nothing new since yesterday.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-[18px]">
          <button
            type="button"
            onClick={dismiss}
            className="flex h-14 w-full items-center justify-center gap-2 rounded-full bg-white text-[17px] font-semibold text-[var(--accent)] transition hover:brightness-[1.06] active:translate-y-[0.5px] active:scale-[0.99]"
          >
            Read now
            <svg width="17" height="14" viewBox="0 0 17 14" aria-hidden="true">
              <path
                d="M1 7h13M10 1l5 6-5 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
            </svg>
          </button>
          <button
            type="button"
            onClick={never}
            className="mt-1.5 w-full py-3 text-[13px] font-medium text-white/55 transition hover:text-white/75"
          >
            Don&rsquo;t show again
          </button>
        </div>
      </div>
    </div>
  );
}
