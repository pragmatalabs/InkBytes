"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { isSaved, toggleSaved, SAVED_EVENT } from "@/lib/saved-events";

/**
 * Event chrome (prototype `chromeEvent`): ← back · EN/ES reading-language toggle
 * · Save · Share. The language toggle swaps to the same story's sibling-language
 * page when one exists (ADR-0037 `also_languages`), otherwise the other button is
 * disabled. Save persists to localStorage (lib/saved-events; a profile later).
 */
const LANGS = ["en", "es"] as const;
type Lang = (typeof LANGS)[number];

interface Props {
  back: React.ReactNode;
  share: React.ReactNode;
  eventId: string;
  headline: string;
  category: string | null;
  language: string;
  alsoLanguages?: Record<string, string>;
}

export default function EventActionBar({
  back,
  share,
  eventId,
  headline,
  category,
  language,
  alsoLanguages,
}: Props) {
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const sync = () => setSaved(isSaved(eventId));
    sync();
    window.addEventListener(SAVED_EVENT, sync);
    window.addEventListener("storage", sync); // cross-tab
    return () => {
      window.removeEventListener(SAVED_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [eventId]);

  // language can be absent on some rows despite the type — default to EN active.
  const current = (language || "en").slice(0, 2).toLowerCase();

  return (
    <div className="flex items-center justify-between mb-8">
      {back}

      <div className="flex items-center gap-3">
        {/* Reading-language toggle */}
        <div className="flex border border-[var(--border)]">
          {LANGS.map((l: Lang) => {
            const active = current === l;
            const siblingId = alsoLanguages?.[l];
            const label = l.toUpperCase();
            const base = "font-mono text-[10px] font-bold px-2 py-1 leading-none";
            if (active) {
              return (
                <span key={l} className={`${base} bg-[var(--ink)] text-white`} aria-current="true">
                  {label}
                </span>
              );
            }
            if (siblingId) {
              return (
                <Link
                  key={l}
                  href={`/event/${siblingId}`}
                  className={`${base} text-[var(--ink)] hover:bg-gray-100 transition-colors`}
                  aria-label={`Read in ${label}`}
                >
                  {label}
                </Link>
              );
            }
            return (
              <span
                key={l}
                className={`${base} text-[var(--ink-muted)] opacity-40 cursor-not-allowed`}
                aria-disabled="true"
                title={`Not available in ${label}`}
              >
                {label}
              </span>
            );
          })}
        </div>

        {/* Save */}
        <button
          type="button"
          onClick={() => setSaved(toggleSaved({ id: eventId, headline, category, language }))}
          aria-pressed={saved}
          aria-label={saved ? "Remove from saved" : "Save this story"}
          className="inline-flex items-center text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors"
        >
          <svg viewBox="0 0 24 24" width="17" height="17" fill={saved ? "var(--accent)" : "none"} stroke={saved ? "var(--accent)" : "currentColor"} strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 3h14v18l-7-5-7 5z" />
          </svg>
        </button>

        {share}
      </div>
    </div>
  );
}
