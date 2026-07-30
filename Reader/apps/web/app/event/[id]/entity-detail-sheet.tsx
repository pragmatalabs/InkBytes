"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { relativeTime, outletInitials } from "@/lib/api";
import { useLang } from "@/lib/prefs";
import { t, entityNoun } from "@/lib/i18n";
import type { EntityDetail, EntityType } from "@/lib/types";

/**
 * EntityDetailSheet — the "inside news" entity detail (prototype entOpen), a
 * stacked sub-sheet over the event page's "Entities in this story" drawer.
 *
 * Fetches Curator's single-entity slice via /api/entity/{id} on open. Rich when
 * the endpoint is live (stats · recent events · connections); degrades to a
 * light sheet (name + type + "View full profile →") on 404 — i.e. when the
 * entity isn't in a published event OR the Curator endpoint isn't deployed yet.
 */
const PALETTE = ["#5b6472", "#276749", "#2c5f62", "#7b341e", "#553c9a", "#97266d", "#2d5282", "#744210"];
function colorOf(s: string): string {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) & 0xffffffff;
  return PALETTE[Math.abs(h) % PALETTE.length];
}
export interface DrawerEntity { id: string; name: string; type: EntityType }

export default function EntityDetailSheet({ entity, onClose }: { entity: DrawerEntity | null; onClose: () => void }) {
  const lang = useLang();
  const [detail, setDetail] = useState<EntityDetail | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "light">("loading");

  // Key the fetch on the entity id (a string), not the object — defensive
  // against a fresh object reference ever re-firing the request in a loop.
  const entityId = entity?.id ?? null;
  useEffect(() => {
    if (!entityId) return;
    setDetail(null);
    setState("loading");
    let alive = true;
    fetch(`/api/entity/${encodeURIComponent(entityId)}`)
      .then((r) => r.json())
      .then((d) => {
        if (!alive) return;
        // Endpoint deferred (Curator ADR-0042) or entity not in a published
        // event → the proxy returns { available: false }. Render the light sheet.
        if (d && d.available !== false && typeof d.event_count === "number") {
          setDetail(d as EntityDetail);
          setState("ok");
        } else {
          setState("light");
        }
      })
      .catch(() => { if (alive) setState("light"); });
    return () => { alive = false; };
  }, [entityId]);

  useEffect(() => {
    if (!entity) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [entity, onClose]);

  if (!entity) return null;
  const noun = entityNoun(lang, entity.type);

  return (
    <>
      <button aria-label="Close" onClick={onClose} className="scrim-enter fixed inset-0 z-[72] bg-[rgba(10,10,15,0.44)]" />
      <div className="fixed inset-x-0 bottom-0 z-[73] flex justify-center px-0 sm:px-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-label={entity.name}
          className="sheet-enter w-full max-w-2xl max-h-[85vh] overflow-y-auto bg-white border-t-2 border-[var(--ink)] shadow-[0_-18px_40px_rgba(10,10,15,0.28)] px-5 pt-2.5 pb-8 safe-bottom"
        >
          <div className="w-10 h-1 rounded-full bg-[var(--border)] mx-auto mb-3.5" aria-hidden />

          {/* Header */}
          <div className="flex items-center gap-3 pb-3.5 border-b-2 border-[var(--ink)]">
            <span className="inline-flex items-center justify-center w-11 h-11 rounded-full text-white text-[13px] font-extrabold shrink-0 overflow-hidden" style={{ background: colorOf(entity.name) }}>
              {detail?.image
                // eslint-disable-next-line @next/next/no-img-element
                ? <img src={detail.image} alt="" className="w-full h-full object-cover" />
                : outletInitials(entity.name)}
            </span>
            <div className="min-w-0 flex-1">
              <div className="font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--ink-muted)]">{noun}</div>
              <div className="text-[19px] font-extrabold tracking-tight truncate">{entity.name}</div>
            </div>
            <button onClick={onClose} aria-label="Close" className="w-7 h-7 grid place-items-center border border-[var(--border)] bg-white hover:border-[var(--ink)] transition-colors shrink-0">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
          </div>

          {state === "loading" && (
            <div className="py-12 text-center text-[13px] text-[var(--ink-muted)]">Loading…</div>
          )}

          {state === "ok" && detail && (
            <div className="pt-4 flex flex-col gap-5">
              {detail.description && (
                <p className="-mt-1 text-[13px] leading-snug text-[var(--ink-muted)]">{detail.description}</p>
              )}
              {/* 3-up stats */}
              <div className="grid grid-cols-3 gap-px bg-[var(--border)] border border-[var(--border)]">
                {([[t(lang, "stat_stories"), detail.event_count], [t(lang, "stat_links"), detail.connection_count], [t(lang, "stat_today"), detail.today_count]] as const).map(([label, val]) => (
                  <div key={label} className="bg-white px-3 py-3">
                    <p className="text-xl font-bold tabular-nums leading-none">{val}</p>
                    <p className="text-[9.5px] font-semibold uppercase tracking-[0.1em] text-[var(--ink-muted)] mt-1.5">{label}</p>
                  </div>
                ))}
              </div>
              {/* Recent events */}
              {detail.recent_events.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-1">
                    {t(lang, "recent_events")}
                    {detail.event_count > detail.recent_events.length && (
                      <span className="normal-case tracking-normal font-normal"> — {detail.recent_events.length} {t(lang, "of")} {detail.event_count}</span>
                    )}
                  </p>
                  <div className="flex flex-col divide-y divide-[var(--border)]">
                    {detail.recent_events.map((ev) => (
                      <Link key={ev.id} href={`/event/${ev.id}`} onClick={onClose} className="py-3 group">
                        <p className="text-[13px] font-medium leading-snug group-hover:text-[var(--accent)] transition-colors line-clamp-2">{ev.headline}</p>
                        <p suppressHydrationWarning className="text-[11px] text-[var(--ink-muted)] mt-1">{ev.source_count} {t(lang, ev.source_count === 1 ? "source_one" : "source_many")} · {relativeTime(ev.freshness_at)}</p>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
              {/* Connections */}
              {detail.connections.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-2">{t(lang, "connections")}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {detail.connections.map((c) => (
                      <Link key={c.id} href={`/entities?e=${encodeURIComponent(c.id)}`} onClick={onClose} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border border-[var(--border)] bg-white text-xs font-medium hover:border-gray-300 transition-colors">
                        <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: colorOf(c.label) }} />
                        {c.label}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {state === "light" && (
            <div className="pt-4 flex flex-col gap-4">
              <p className="text-[13px] leading-relaxed text-[var(--ink-muted)]">
                {t(lang, "mentioned_in_story", { noun: noun.toLowerCase() })}
              </p>
              <Link
                href={`/entities?e=${encodeURIComponent(entity.id)}`}
                onClick={onClose}
                className="inline-flex items-center justify-center gap-2 py-3 border border-[var(--ink)] text-[13px] font-semibold hover:bg-[var(--ink)] hover:text-white transition-colors"
              >
                {t(lang, "view_full_profile")}
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
