"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { relativeTime, outletInitials } from "@/lib/api";
import { useLang, type Lang } from "@/lib/prefs";
import { t, entityNoun } from "@/lib/i18n";
import type {
  MediaRailItem,
  EvidenceItem,
  EntityItem,
  RelatedEvent,
  TitleHistoryEntry,
} from "@/lib/types";
import VideoCoverflow from "@/components/video-coverflow";
import EntityDetailSheet, { type DrawerEntity } from "./entity-detail-sheet";

/**
 * StoryNav — the event page's "This story" 2×2 action grid, and the bottom-sheet
 * drawers each tile opens (InkBytes Reader Prototype). The event page stays lean
 * (synthesis + cover + grid); the detail — Watch / Evidence / Entities / Related —
 * lives in progressive-disclosure sheets that slide up over a scrim, instead of
 * long inline sections.
 *
 * A tile only renders when its count > 0. Next story links to the top related
 * event when there is one.
 */
type SheetKey = "watch" | "evidence" | "entities" | "related";

interface Props {
  videos: MediaRailItem[];
  evidence: EvidenceItem[];
  entities: EntityItem[];
  related: RelatedEvent[];
  /** Prior headlines (ADR-0035) — rendered as the story timeline in the Related sheet. */
  timeline: TitleHistoryEntry[];
  currentHeadline: string;
  nextId?: string | null;
  /** Category accent (themeAccent) — the 4px rail bars + match bars. */
  accent: string;
}

const ICONS: Record<SheetKey, React.ReactNode> = {
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

const SHEET_LABEL: Record<SheetKey, "sheet_watch" | "sheet_evidence" | "sheet_entities" | "sheet_related"> = {
  watch: "sheet_watch",
  evidence: "sheet_evidence",
  entities: "sheet_entities",
  related: "sheet_related",
};

// Colored entity avatars (prototype "Entities in this story") + friendly type
// nouns. Event-page entities carry only name+type, so the row meta is the type;
// tapping deep-links to the full entity profile (stories/connections) in /graph.
const ENTITY_PALETTE = ["#5b6472", "#276749", "#2c5f62", "#7b341e", "#553c9a", "#97266d", "#2d5282", "#744210"];
function entityColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
  return ENTITY_PALETTE[Math.abs(h) % ENTITY_PALETTE.length];
}
// ── Bottom sheet shell ─────────────────────────────────────────────────────────

function Sheet({
  which,
  count,
  onClose,
  children,
  title,
  lang,
}: {
  which: SheetKey;
  count: number;
  onClose: () => void;
  children: React.ReactNode;
  /** Overrides the default header label (e.g. "Entities in this story"). */
  title?: string;
  lang: Lang;
}) {
  const heading = title ?? t(lang, SHEET_LABEL[which]);
  return (
    <>
      {/* Scrim */}
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="scrim-enter fixed inset-0 z-[70] bg-[rgba(10,10,15,0.44)]"
      />
      {/* Sheet — bottom-anchored, centred to the content column on desktop */}
      <div className="fixed inset-x-0 bottom-0 z-[71] flex justify-center px-0 sm:px-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-label={heading}
          className="sheet-enter w-full max-w-2xl max-h-[85vh] overflow-y-auto bg-white border-t-2 border-[var(--ink)] shadow-[0_-18px_40px_rgba(10,10,15,0.28)] px-5 pt-2.5 pb-8 safe-bottom"
        >
          {/* grabber */}
          <div className="w-10 h-1 rounded-full bg-[var(--border)] mx-auto mb-3.5" aria-hidden />
          <div className="flex items-center gap-2.5 pb-2.5 border-b-2 border-[var(--ink)]">
            <span className="text-[var(--ink)]">{ICONS[which]}</span>
            <span className="font-mono text-[12px] font-bold uppercase tracking-[0.12em]">{heading}</span>
            <span className="font-mono text-[12px] font-bold text-[var(--ink-muted)] tabular-nums">· {count}</span>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="ml-auto w-7 h-7 grid place-items-center border border-[var(--border)] bg-white hover:border-[var(--ink)] transition-colors"
            >
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <path d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
          </div>
          {children}
        </div>
      </div>
    </>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function StoryNav({
  videos,
  evidence,
  entities,
  related,
  timeline,
  currentHeadline,
  nextId,
  accent,
}: Props) {
  const lang = useLang();
  const [open, setOpen] = useState<SheetKey | null>(null);
  // Source to scroll to + flash when Evidence opens from a citation tap.
  const [focusSource, setFocusSource] = useState<string | null>(null);
  // Entity tapped in the Entities drawer → in-place detail sub-sheet.
  const [openEntity, setOpenEntity] = useState<DrawerEntity | null>(null);

  // Escape closes; lock body scroll while a sheet is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(null);
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Open a sheet from elsewhere on the page (inline citation chips → Evidence).
  useEffect(() => {
    const onOpenSheet = (e: Event) => {
      const detail = (e as CustomEvent).detail ?? {};
      const sheet = typeof detail === "string" ? detail : detail.sheet;
      if (sheet === "watch" || sheet === "evidence" || sheet === "entities" || sheet === "related") {
        setOpen(sheet);
        setFocusSource(sheet === "evidence" && detail.source ? String(detail.source) : null);
      }
    };
    window.addEventListener("inkb:open-sheet", onOpenSheet);
    return () => window.removeEventListener("inkb:open-sheet", onOpenSheet);
  }, []);

  // When Evidence opens focused on a source, scroll it into view + flash it.
  useEffect(() => {
    if (open !== "evidence" || !focusSource) return;
    const scroll = setTimeout(() => {
      const el = document.querySelector(`[data-evidence-src="${CSS.escape(focusSource)}"]`);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 60);
    const clear = setTimeout(() => setFocusSource(null), 1800);
    return () => {
      clearTimeout(scroll);
      clearTimeout(clear);
    };
  }, [open, focusSource]);

  const tiles = [
    videos.length > 0 && { key: "watch" as const, n: videos.length },
    evidence.length > 0 && { key: "evidence" as const, n: evidence.length },
    entities.length > 0 && { key: "entities" as const, n: entities.length },
    related.length > 0 && { key: "related" as const, n: related.length },
  ].filter(Boolean) as { key: SheetKey; n: number }[];

  if (tiles.length === 0 && !nextId) return null;

  const close = () => setOpen(null);

  return (
    <div className="mb-10">
      {tiles.length > 0 && (
        <>
          <div className="flex items-center gap-2 mb-2.5 pb-1.5 border-b-2 border-[var(--ink)]">
            <span className="font-mono text-[11px] font-bold uppercase tracking-[0.12em]">{t(lang, "this_story")}</span>
            <span className="ml-auto font-mono text-[11px] font-bold text-[var(--ink-muted)]">{t(lang, "tap_to_open")}</span>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {tiles.map((tile) => (
              <button
                key={tile.key}
                type="button"
                onClick={() => setOpen(tile.key)}
                aria-haspopup="dialog"
                className="flex flex-col gap-1.5 p-3 border border-[var(--border)] bg-white text-left text-[var(--ink)] hover:border-[var(--ink)] transition-colors"
              >
                {ICONS[tile.key]}
                <span className="text-[13px] font-bold tracking-tight leading-tight">
                  {t(lang, SHEET_LABEL[tile.key])}{" "}
                  <span className="font-mono text-[10px] font-bold text-[var(--ink-muted)] tabular-nums">{tile.n}</span>
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
          {t(lang, "next_story")}
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <polyline points="9 6 15 12 9 18" />
          </svg>
        </Link>
      )}

      {/* ── Watch ─────────────────────────────────────────────────────────── */}
      {open === "watch" && (
        <Sheet which="watch" count={videos.length} onClose={close} lang={lang}>
          <div className="mt-4">
            <VideoCoverflow videos={videos} />
          </div>
          <div className="mt-3 font-mono text-[10.5px] tracking-[0.05em] text-[var(--ink-muted)]">
            {t(lang, "video_only")}
          </div>
        </Sheet>
      )}

      {/* ── Evidence ──────────────────────────────────────────────────────── */}
      {open === "evidence" && (
        <Sheet which="evidence" count={evidence.length} onClose={close} lang={lang}>
          {evidence.map((q, i) => (
            <a
              key={i}
              href={q.url}
              target="_blank"
              rel="noopener noreferrer"
              data-evidence-src={q.source_name}
              className={`grid grid-cols-[4px_1fr] gap-3.5 py-4 border-b border-[var(--border)] group transition-colors ${
                focusSource === q.source_name ? "bg-gray-50" : ""
              }`}
            >
              <i className="block" style={{ background: accent }} />
              <div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-[18px] h-[18px] rounded-full bg-[var(--accent)] text-white text-[7px] font-bold uppercase">
                    {outletInitials(q.source_name)}
                  </span>
                  <span className="text-[11px] font-bold">{q.source_name}</span>
                  <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" className="ml-auto text-[var(--ink-muted)] group-hover:text-[var(--accent)] transition-colors">
                    <path d="M14 4h6v6M20 4 11 13" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
                  </svg>
                </div>
                <p className="mt-2.5 synthesis-body !text-[15px] !leading-[1.5] !mb-0">
                  &ldquo;{q.quote}&rdquo;
                </p>
              </div>
            </a>
          ))}
        </Sheet>
      )}

      {/* ── Entities in this story (prototype isEntsDrawer) ──────────────────── */}
      {open === "entities" && (
        <Sheet which="entities" count={entities.length} onClose={close} title={t(lang, "entities_in_story")} lang={lang}>
          {entities.map((e, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setOpenEntity({ id: e.name.toLowerCase(), name: e.name, type: e.type })}
              className="flex items-center gap-3 py-3 border-b border-[var(--border)] w-full text-left group"
            >
              <span
                className="inline-flex items-center justify-center w-9 h-9 rounded-full text-white text-[11px] font-extrabold shrink-0"
                style={{ background: entityColor(e.name) }}
              >
                {outletInitials(e.name)}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-[15px] font-bold tracking-tight truncate group-hover:text-[var(--accent)] transition-colors">{e.name}</div>
                {e.type && <div className="text-[12px] text-[var(--ink-muted)]">{entityNoun(lang, e.type)}</div>}
              </div>
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#9a9a9a" strokeWidth="2" className="shrink-0"><polyline points="9 6 15 12 9 18" /></svg>
            </button>
          ))}
          <Link
            href="/entities"
            onClick={close}
            className="mt-4 inline-flex items-center gap-1.5 font-mono text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--accent)] hover:underline"
          >
            {t(lang, "explore_graph")}
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><polyline points="9 6 15 12 9 18" /></svg>
          </Link>
        </Sheet>
      )}

      {/* ── Related (story timeline + related events) ─────────────────────── */}
      {open === "related" && (
        <Sheet which="related" count={related.length} onClose={close} lang={lang}>
          {timeline.length > 0 && (
            <div className="mt-3.5 ml-1.5 pl-4 border-l border-[var(--border)]">
              {timeline.map((ti, i) => (
                <div key={i} className="relative pb-4">
                  <span className="absolute top-1 -left-[21px] w-1.5 h-1.5 bg-[var(--border)]" aria-hidden />
                  {ti.at && (
                    <div suppressHydrationWarning className="font-mono text-[10.5px] font-bold uppercase tracking-[0.1em] text-[var(--ink-muted)]">
                      {relativeTime(ti.at)}
                    </div>
                  )}
                  <div className="text-[14.5px] leading-snug tracking-tight mt-1">{ti.headline}</div>
                </div>
              ))}
              <div className="relative pb-1">
                <span className="absolute top-1 -left-[21px] w-2 h-2" style={{ background: accent }} aria-hidden />
                <div className="font-mono text-[10.5px] font-bold uppercase tracking-[0.1em] text-[var(--accent)]">{t(lang, "now")}</div>
                <div className="text-[14.5px] font-bold leading-snug tracking-tight mt-1">{currentHeadline}</div>
              </div>
            </div>
          )}

          {related.map((r) => {
            const pct = Math.round(r.score * 100);
            return (
              <Link
                key={r.id}
                href={`/event/${r.id}`}
                onClick={close}
                className="grid grid-cols-[4px_1fr] gap-3.5 pt-3.5 mt-2 border-t border-[var(--border)] group"
              >
                <i className="block" style={{ background: accent }} />
                <div>
                  <div className="text-[14.5px] font-bold leading-snug tracking-tight group-hover:text-[var(--accent)] transition-colors">
                    {r.headline}
                  </div>
                  <div className="flex items-center gap-2.5 mt-1.5 text-[11px] text-[var(--ink-muted)]">
                    <span>{r.source_count} {t(lang, r.source_count === 1 ? "source_one" : "source_many")}</span>
                    <span suppressHydrationWarning className="font-mono">{relativeTime(r.freshness_at)}</span>
                    {r.language !== "en" && (
                      <span className="font-mono uppercase text-[9px] px-1 py-0.5 rounded bg-gray-100 text-gray-500">{r.language}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2.5 mt-2.5 pt-2.5 border-t border-[var(--border)]">
                    <span className="block w-[52px] h-1 bg-[var(--border)] shrink-0">
                      <i className="block h-1" style={{ background: accent, width: `${pct}%` }} />
                    </span>
                    <span className="font-mono text-[11px] font-bold tabular-nums">{pct}%</span>
                    <span className="text-[11px] text-[var(--ink-muted)]">{t(lang, "match")}</span>
                  </div>
                </div>
              </Link>
            );
          })}
        </Sheet>
      )}

      {/* Entity detail — stacked over the Entities drawer (prototype entOpen) */}
      <EntityDetailSheet entity={openEntity} onClose={() => setOpenEntity(null)} />
    </div>
  );
}
