"use client";

import Link from "next/link";

/**
 * StoryNav — the event page's "This story" 2×2 action grid + Next story button
 * (from the InkBytes Reader Prototype). Sits below the synthesis + cover.
 *
 * Watch opens the video drawer (dispatches a custom event MediaRailDrawer listens
 * for); Evidence / Entities / Related smooth-scroll to their inline sections
 * (#evidence / #entities / #related). A tile only renders when its count > 0.
 * Next story links to the top related event when there is one.
 */
interface Props {
  clips: number;
  quotes: number;
  entities: number;
  related: number;
  nextId?: string | null;
}

const ICONS: Record<string, React.ReactNode> = {
  watch: (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2.5" y="7" width="13" height="10" rx="1.5" /><path d="M15.5 11.2 21.5 7.8v8.4l-6-3.4z" /><circle cx="9" cy="12" r="2.4" />
    </svg>
  ),
  evidence: (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16v12H8l-4 4z" /><path d="M9.2 8.2c-1.4 0-2 1-2 2s.6 1.6 1.5 1.6 1.4-.5 1.4-1.4c0-1.6-.9-2.2-.9-2.2" /><path d="M14.6 8.2c-1.4 0-2 1-2 2s.6 1.6 1.5 1.6 1.4-.5 1.4-1.4c0-1.6-.9-2.2-.9-2.2" />
    </svg>
  ),
  entities: (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="5" cy="6" r="2.4" /><circle cx="19" cy="7" r="2.4" /><circle cx="12" cy="18" r="2.4" /><path d="M7.3 6.4 16.6 6.8M6.1 8.2 10.9 15.9M17.5 9.2 13.1 15.9" />
    </svg>
  ),
  related: (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.5 13.5a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1.2 1.2" /><path d="M13.5 10.5a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1.2-1.2" />
    </svg>
  ),
};

export default function StoryNav({ clips, quotes, entities, related, nextId }: Props) {
  const scrollTo = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const tiles = [
    clips > 0 && { key: "watch", label: "Watch", n: clips, onClick: () => window.dispatchEvent(new Event("inkb:open-video")) },
    quotes > 0 && { key: "evidence", label: "Evidence", n: quotes, onClick: scrollTo("evidence") },
    entities > 0 && { key: "entities", label: "Entities", n: entities, onClick: scrollTo("entities") },
    related > 0 && { key: "related", label: "Related", n: related, onClick: scrollTo("related") },
  ].filter(Boolean) as { key: string; label: string; n: number; onClick: (e: React.MouseEvent) => void }[];

  if (tiles.length === 0 && !nextId) return null;

  return (
    <div className="mb-10">
      {tiles.length > 0 && (
        <>
          <div className="flex items-center gap-2 mb-2.5 pb-1.5 border-b-2 border-[var(--ink)]">
            <span className="font-mono text-[11px] font-bold uppercase tracking-[0.12em]">This story</span>
            <span className="ml-auto font-mono text-[11px] font-bold text-[var(--ink-muted)]">Tap to open</span>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {tiles.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={t.onClick}
                className="flex flex-col gap-1.5 p-3 border border-[var(--border)] bg-white text-left text-[var(--ink)] hover:border-[var(--ink)] transition-colors"
              >
                {ICONS[t.key]}
                <span className="text-[13px] font-bold tracking-tight leading-tight">
                  {t.label}{" "}
                  <span className="font-mono text-[10px] font-bold text-[var(--ink-muted)] tabular-nums">{t.n}</span>
                </span>
              </button>
            ))}
          </div>
        </>
      )}

      {nextId && (
        <Link
          href={`/event/${nextId}`}
          className="mt-5 w-full flex items-center justify-center gap-2.5 py-3.5 bg-[var(--ink)] text-white font-mono text-[12px] font-bold uppercase tracking-[0.12em] hover:opacity-90 transition-opacity"
        >
          Next story
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <polyline points="9 6 15 12 9 18" />
          </svg>
        </Link>
      )}
    </div>
  );
}
