"use client";

import { useEffect, useState } from "react";
import { isSaved, toggleSaved, SAVED_EVENT } from "@/lib/saved-outlooks";

/** Save/unsave an outlook edition to localStorage (profile later). Bookmark
 *  fills when saved. Reads state on mount + on the same-tab change event so
 *  every save button + the index list stay in sync. */
export default function OutlookSave(props: {
  theme: string; lang: string; date: string; headline: string; persona: string;
}) {
  const { theme, lang, date, headline, persona } = props;
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const sync = () => setSaved(isSaved({ theme, lang, date }));
    sync();
    window.addEventListener(SAVED_EVENT, sync);
    window.addEventListener("storage", sync);   // cross-tab
    return () => {
      window.removeEventListener(SAVED_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [theme, lang, date]);

  return (
    <button
      type="button"
      onClick={() => setSaved(toggleSaved({ theme, lang, date, headline, persona }))}
      aria-pressed={saved}
      aria-label={saved ? "Remove from saved" : "Save this outlook"}
      className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${
        saved
          ? "border-[var(--accent)] bg-[var(--accent)] text-white"
          : "border-[var(--border)] bg-white hover:bg-gray-50 text-[var(--ink)]"
      }`}
    >
      <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24"
        fill={saved ? "currentColor" : "none"} stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
      </svg>
      {saved ? "Saved" : "Save"}
    </button>
  );
}
