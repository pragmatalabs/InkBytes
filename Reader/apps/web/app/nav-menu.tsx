"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { getLang, setLang, PREFS_EVENT, type Lang } from "@/lib/prefs";

/**
 * NavMenu — the header's ☰ hamburger + right-drawer (InkBytes Reader.dc.html
 * chromeBrand + menuOpen). The prototype nav keeps Brief/Outlook/Browse/Entities
 * in the bottom bar and moves Saved / Settings / About into this drawer, plus a
 * reading-language toggle. Renders the current screen label next to the ☰.
 */
const SCREEN_LABELS: [RegExp, string][] = [
  [/^\/event\//, "STORY"],
  [/^\/outlook/, "OUTLOOK"],
  [/^\/browse/, "BROWSE"],
  [/^\/entities/, "ENTITIES"],
  [/^\/saved/, "SAVED"],
  [/^\/you/, "SETTINGS"],
  [/^\/about/, "ABOUT"],
  [/^\/$/, "BRIEF"],
];
const labelFor = (path: string) => SCREEN_LABELS.find(([re]) => re.test(path))?.[1] ?? "";

const MENU = [
  { href: "/saved", label: "Saved", rail: "var(--accent-dot)" },
  { href: "/you", label: "Settings", rail: "var(--accent)" },
  { href: "/about", label: "About", rail: "#16a34a" },
];

export default function NavMenu() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    const sync = () => setLangState(getLang());
    sync();
    window.addEventListener(PREFS_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(PREFS_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  const pickLang = (l: Lang) => { setLang(l); setLangState(l); };
  const label = labelFor(pathname);
  // The event page carries its own EN/ES (EventActionBar) — don't double it.
  const isEvent = /^\/event\//.test(pathname);

  return (
    <>
      <div className="flex items-center gap-3">
        {label && (
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-white/55">{label}</span>
        )}
        {!isEvent && (
          <div className="flex border border-white/30">
            {(["en", "es"] as Lang[]).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => pickLang(l)}
                aria-pressed={lang === l}
                className={`font-mono text-[10px] font-bold px-2 py-1 leading-none transition-colors ${lang === l ? "bg-white text-[var(--accent)]" : "text-white/60 hover:text-white"}`}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        )}
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open menu"
          aria-expanded={open}
          className="grid gap-[4px] place-items-end p-1.5 -mr-1.5"
        >
          <i className="block w-[17px] h-[2px] bg-white" />
          <i className="block w-[17px] h-[2px] bg-white" />
          <i className="block w-[11px] h-[2px] bg-[var(--accent-dot)]" />
        </button>
      </div>

      {open && (
        <>
          <button
            aria-label="Close menu"
            onClick={() => setOpen(false)}
            className="scrim-enter fixed inset-0 z-[60] bg-[rgba(10,10,15,0.5)]"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Menu"
            className="sheet-enter fixed top-0 right-0 bottom-0 z-[61] w-[296px] max-w-[85vw] bg-[var(--bg)] border-l-2 border-[var(--ink)] shadow-[-18px_0_44px_rgba(10,10,15,0.3)] overflow-y-auto"
          >
            <div className="h-[52px] bg-[var(--accent)] flex items-center justify-between px-4">
              <span className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-white/55">Menu</span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="w-[26px] h-[26px] grid place-items-center border border-white/35"
              >
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
              </button>
            </div>

            <div className="px-[18px] pt-5 pb-7">
              <div className="text-[20px] font-extrabold tracking-tight">InkBytes<span className="text-[var(--accent-dot)]">.</span></div>
              <div className="flex items-center gap-1.5 mt-1.5">
                <span className="w-1.5 h-1.5 bg-[#16a34a]" />
                <span className="font-mono text-[9.5px] font-bold uppercase tracking-[0.1em] text-[var(--ink-muted)]">Paid · ad-free</span>
              </div>

              <div className="h-0.5 bg-[var(--ink)] mt-[18px]" />

              {MENU.map((m) => (
                <Link
                  key={m.href}
                  href={m.href}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-3 py-4 border-b border-[var(--border)] hover:bg-black/[0.03] transition-colors -mx-[18px] px-[18px]"
                >
                  <i className="block w-1 h-4 shrink-0" style={{ background: m.rail }} />
                  <span className="flex-1 text-[15.5px] font-bold tracking-tight text-[var(--ink)]">{m.label}</span>
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#9a9a9a" strokeWidth="2"><polyline points="9 6 15 12 9 18" /></svg>
                </Link>
              ))}

              <div className="flex items-center gap-2.5 mt-5">
                <span className="font-mono text-[9.5px] font-bold uppercase tracking-[0.12em] text-[var(--ink-muted)]">Reading language</span>
                <span className="ml-auto flex border border-[var(--border)]">
                  {(["en", "es"] as Lang[]).map((l) => (
                    <button
                      key={l}
                      type="button"
                      onClick={() => pickLang(l)}
                      className={`font-mono text-[10px] font-bold px-2.5 py-1 ${lang === l ? "bg-[var(--accent)] text-white" : "text-[var(--ink)]"}`}
                    >
                      {l.toUpperCase()}
                    </button>
                  ))}
                </span>
              </div>

              <div className="font-mono text-[10px] tracking-[0.06em] text-[var(--ink-muted)] mt-6 leading-relaxed">
                INKBYTES · PAID, AD-FREE<br />ONE PAGE PER EVENT
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
