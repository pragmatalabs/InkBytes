"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  getLang, setLang, getNotif, setNotif, PREFS_EVENT,
  type Lang, type NotifPrefs,
} from "@/lib/prefs";
import { listFollowed, clearFollowed, FOLLOWED_EVENT } from "@/lib/followed";
import { listSaved as listSavedEvents, clearSaved as clearSavedEvents, SAVED_EVENT as SAVED_EVENTS_EVENT } from "@/lib/saved-events";
import { listSaved as listSavedOutlooks, clearSaved as clearSavedOutlooks, SAVED_EVENT as SAVED_OUTLOOKS_EVENT } from "@/lib/saved-outlooks";

/**
 * You screen (mobile redesign, Slice B2) — reader preferences, all localStorage
 * (a signed-in profile later). Reading language + notification toggles persist;
 * the "your data" block reports and can clear the Save/Follow stores. Values
 * render after mount to avoid an SSR/hydration mismatch.
 *
 * Deferred with the briefing work (Slice C): citation-style + brief-length
 * prefs, and wiring the reading language into the feed/event defaults.
 */
const LABEL = "text-[11px] font-bold uppercase tracking-widest text-[var(--ink-muted)] mb-3";
const ROW = "flex items-center justify-between gap-4 py-3.5 border-b border-[var(--border)]";

const NOTIF_ROWS: { key: keyof NotifPrefs; label: string; sub: string }[] = [
  { key: "developing", label: "Developing stories", sub: "When a story you can see is moving fast" },
  { key: "followed", label: "Followed updates", sub: "New coverage on stories you follow" },
  { key: "briefing", label: "Daily briefing", sub: "When the day's briefing is ready" },
];

function Toggle({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={onClick}
      className={`relative w-[42px] h-6 shrink-0 rounded-full transition-colors ${on ? "bg-[var(--accent)]" : "bg-[var(--border)]"}`}
    >
      <span
        className="absolute top-[2.5px] w-[19px] h-[19px] rounded-full bg-white shadow transition-[left]"
        style={{ left: on ? 20 : 2.5 }}
      />
    </button>
  );
}

export default function YouPage() {
  const [mounted, setMounted] = useState(false);
  const [lang, setLangState] = useState<Lang>("en");
  const [notif, setNotifState] = useState<NotifPrefs>({ developing: true, followed: true, briefing: false });
  const [counts, setCounts] = useState({ following: 0, saved: 0, outlooks: 0 });
  const [confirmClear, setConfirmClear] = useState(false);

  useEffect(() => {
    const sync = () => {
      setLangState(getLang());
      setNotifState(getNotif());
      setCounts({
        following: listFollowed().length,
        saved: listSavedEvents().length,
        outlooks: listSavedOutlooks().length,
      });
    };
    sync();
    setMounted(true);
    const events = [PREFS_EVENT, FOLLOWED_EVENT, SAVED_EVENTS_EVENT, SAVED_OUTLOOKS_EVENT, "storage"];
    events.forEach((e) => window.addEventListener(e, sync));
    return () => events.forEach((e) => window.removeEventListener(e, sync));
  }, []);

  const pickLang = (l: Lang) => { setLang(l); setLangState(l); };
  const toggleNotif = (key: keyof NotifPrefs) => {
    const next = { ...notif, [key]: !notif[key] };
    setNotif(next);
    setNotifState(next);
  };
  const clearAll = () => {
    clearFollowed();
    clearSavedEvents();
    clearSavedOutlooks();
    setConfirmClear(false);
  };

  const total = counts.following + counts.saved + counts.outlooks;

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      <h1 className="text-[1.6rem] sm:text-3xl font-bold tracking-tight mb-8">You</h1>

      {/* Reading language */}
      <section className="mb-9">
        <div className={LABEL}>Reading language</div>
        <div className={ROW}>
          <span className="text-[14px]">Briefs written in</span>
          <span className="flex border border-[var(--border)] rounded-full overflow-hidden">
            {(["es", "en"] as Lang[]).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => pickLang(l)}
                className={`px-3.5 py-1 text-[11px] font-semibold ${lang === l ? "bg-[var(--accent)] text-white" : "text-[var(--ink)]"}`}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </span>
        </div>
        <p className="mt-2 text-[11.5px] leading-relaxed text-[var(--ink-muted)]">
          Sources always stay in their original language, labelled. You can flip any single story while reading it.
        </p>
      </section>

      {/* Notifications */}
      <section className="mb-9">
        <div className={LABEL}>Notifications</div>
        {NOTIF_ROWS.map((r) => (
          <div key={r.key} className={ROW}>
            <span className="min-w-0">
              <span className="block text-[14px]">{r.label}</span>
              <span className="block text-[11px] text-[var(--ink-muted)] leading-snug">{r.sub}</span>
            </span>
            <Toggle on={notif[r.key]} onClick={() => toggleNotif(r.key)} />
          </div>
        ))}
        <p className="mt-2 text-[11.5px] leading-relaxed text-[var(--ink-muted)]">
          Saved on this device — delivery turns on when notifications ship.
        </p>
      </section>

      {/* Your data */}
      <section className="mb-9">
        <div className={LABEL}>Your data</div>
        <p className="text-[13px] text-[var(--ink)] mb-3" suppressHydrationWarning>
          {mounted
            ? `${counts.following} following · ${counts.saved} saved · ${counts.outlooks} outlooks — on this device.`
            : "—"}
        </p>
        {confirmClear ? (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={clearAll}
              className="px-3.5 py-2 text-[12px] font-semibold rounded-full bg-red-600 text-white hover:opacity-90 transition-opacity"
            >
              Clear everything
            </button>
            <button
              type="button"
              onClick={() => setConfirmClear(false)}
              className="px-3.5 py-2 text-[12px] font-semibold rounded-full border border-[var(--border)] hover:border-[var(--ink)] transition-colors"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            disabled={total === 0}
            onClick={() => setConfirmClear(true)}
            className="px-3.5 py-2 text-[12px] font-semibold rounded-full border border-[var(--border)] hover:border-[var(--ink)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Clear saved &amp; following
          </button>
        )}
      </section>

      {/* About */}
      <section>
        <div className={LABEL}>About</div>
        <p className="text-[13px] leading-relaxed text-[var(--ink-muted)]">
          InkBytes is a paid, ad-free news reader — one elegant page per event, synthesized from dozens of
          outlets and cited. Built in the Dominican Republic by Julian De La Rosa.
        </p>
        <Link href="/about" className="inline-block mt-3 text-[12px] font-semibold text-[var(--accent)] hover:underline">
          More about InkBytes →
        </Link>
      </section>
    </div>
  );
}
