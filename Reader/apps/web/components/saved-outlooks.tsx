"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listSaved, removeSaved, SAVED_EVENT, type SavedOutlook } from "@/lib/saved-outlooks";
import { themeAccent } from "@/lib/theme-colors";
import { PersonaIcon } from "@/components/persona-icons";

const titleCase = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
const personaKey = (name: string) => name.toLowerCase().replace(/\s+/g, "-"); // "El Circuito" → "el-circuito"

/** "Saved" rail on the /outlook index — reads localStorage (profile later).
 *  Renders nothing until mount (avoids SSR/hydration mismatch) and only when
 *  the reader has saved something. */
export default function SavedOutlooks() {
  const [items, setItems] = useState<SavedOutlook[] | null>(null);

  useEffect(() => {
    const sync = () => setItems(listSaved());
    sync();
    window.addEventListener(SAVED_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(SAVED_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  if (!items || items.length === 0) return null;

  return (
    <section className="mb-9">
      <div className="flex items-center gap-2 mb-3">
        <svg className="w-3.5 h-3.5 text-[var(--accent)]" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
        </svg>
        <h2 className="text-[11px] font-bold uppercase tracking-widest text-[var(--accent)]">Saved</h2>
        <span className="text-[11px] text-[var(--ink-muted)]">— on this device</span>
      </div>
      <div className="grid gap-2.5 sm:grid-cols-2">
        {items.map((s) => {
          const accent = themeAccent(s.theme);
          return (
            <div key={`${s.theme}-${s.lang}-${s.date}`}
              className="group relative flex items-center gap-2.5 bg-white border border-[var(--border)] rounded-xl p-3 hover:shadow-md hover:border-gray-300 transition-all">
              <Link href={`/outlook/${s.theme}?lang=${s.lang}&date=${s.date}`}
                className="flex items-center gap-2.5 min-w-0 flex-1">
                <span className="grid place-items-center w-8 h-8 rounded-full text-white shrink-0" style={{ background: accent }} aria-hidden>
                  <PersonaIcon persona={personaKey(s.persona)} className="w-4 h-4" />
                </span>
                <span className="min-w-0">
                  <span className="block text-[10px] font-bold uppercase tracking-wider truncate" style={{ color: accent }}>
                    {titleCase(s.theme)} · {s.persona} · {s.lang.toUpperCase()}
                  </span>
                  <span className="block text-[13px] font-semibold leading-snug line-clamp-1">{s.headline}</span>
                </span>
              </Link>
              <button
                type="button"
                onClick={() => removeSaved(s)}
                aria-label="Remove from saved"
                className="shrink-0 grid place-items-center w-7 h-7 rounded-full text-[var(--ink-muted)] hover:bg-gray-100 hover:text-[var(--ink)] transition-colors"
              >
                <svg viewBox="0 0 24 24" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg>
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
