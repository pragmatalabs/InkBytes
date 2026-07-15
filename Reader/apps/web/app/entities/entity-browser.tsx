"use client";

/**
 * EntityBrowser — mobile-first entity navigation (Phase 1 of the entity rework).
 *
 * The force graph is a desktop interaction: on a phone its targets are tiny and
 * pan/zoom fights page scroll. This browser presents the SAME /graph payload the
 * way a phone wants it: type tabs → entity cards with story counts → a bottom
 * sheet with the entity's coverage, its connections, and a static radial
 * relationship preview (no physics). "View full graph" hands off to the force
 * graph for whoever wants it.
 *
 * Zero backend changes: nodes already carry label/type/event_count/pages and
 * edges carry co-occurrence weights (ADR-0036).
 */

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { relativeTime } from "@/lib/api";
import { countryFlag } from "@/lib/country-flags";
import type { GraphData, GraphNode, EntityType } from "@/lib/types";
import { TYPE_META, TYPE_ORDER } from "./type-meta";

// ── Type tab icons (match the TYPE_META palette) ─────────────────────────────

function TypeIcon({ type, className }: { type: EntityType; className?: string }) {
  const common = { className, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  switch (type) {
    case "PERSON":
      return (<svg {...common}><circle cx="12" cy="8" r="4"/><path d="M4 20c0-3.3 3.6-5 8-5s8 1.7 8 5"/></svg>);
    case "ORG":
      return (<svg {...common}><rect x="4" y="3" width="16" height="18" rx="1"/><path d="M9 8h1M14 8h1M9 12h1M14 12h1M9 16h1M14 16h1"/></svg>);
    case "LOC":
      return (<svg {...common}><path d="M12 21s-7-5.3-7-11a7 7 0 0 1 14 0c0 5.7-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>);
    case "EVENT":
      return (<svg {...common}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 11h18"/></svg>);
    default:
      return (<svg {...common}><path d="M20.59 13.41 13.4 20.6a2 2 0 0 1-2.83 0L3 13V3h10l7.59 7.59a2 2 0 0 1 0 2.82z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/></svg>);
  }
}

// ── Entity avatar: country flag for a country, else the type glyph ───────────
// A country (a LOC whose label resolves to an ISO code) shows its flag emoji;
// everything else keeps the accent type icon. (Person photos are the parked
// Wikidata phase — see ADR-R-0010.) `flagOf` returns the emoji or null.
function flagOf(n: { type: EntityType; label: string }): string | null {
  return n.type === "PERSON" ? null : countryFlag(n.label);
}

/** The disc contents for an entity: photo (people) > flag (countries) > type
 *  icon. The Commons portrait fills the disc; on load error it falls back. */
function EntityAvatar({ node, iconClass, flagClass }:
  { node: GraphNode; iconClass: string; flagClass: string }) {
  const [imgOk, setImgOk] = useState(true);
  if (node.image && imgOk) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={node.image} alt="" loading="lazy" onError={() => setImgOk(false)}
      className="w-full h-full object-cover rounded-full" />;
  }
  const flag = flagOf(node);
  if (flag) return <span className={flagClass} aria-hidden>{flag}</span>;
  return <TypeIcon type={node.type} className={iconClass} />;
}

// ── Static radial relationship preview (no physics) ─────────────────────────

function MiniGraph({
  node, neighbors, onSelect,
}: {
  node: GraphNode;
  neighbors: { n: GraphNode; w: number }[];
  onSelect: (id: string) => void;
}) {
  const shown = neighbors.slice(0, 6);
  if (shown.length === 0) return null;
  const W = 340, H = 210, cx = W / 2, cy = H / 2, R = 78;
  const maxW = Math.max(...shown.map((x) => x.w), 1);
  const center = TYPE_META[node.type] ?? TYPE_META.OTHER;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none" role="img"
      aria-label={`Entities most connected to ${node.label}`}>
      {shown.map(({ n, w }, i) => {
        const ang = -Math.PI / 2 + (i / shown.length) * Math.PI * 2;
        const x = cx + Math.cos(ang) * R;
        const y = cy + Math.sin(ang) * R * 0.82;
        const meta = TYPE_META[n.type] ?? TYPE_META.OTHER;
        const label = n.label.length > 16 ? `${n.label.slice(0, 15)}…` : n.label;
        return (
          <g key={n.id} onClick={() => onSelect(n.id)} style={{ cursor: "pointer" }}>
            <line x1={cx} y1={cy} x2={x} y2={y}
              stroke="#d4d4d8" strokeWidth={1 + (w / maxW) * 2.2} strokeOpacity={0.8} />
            <circle cx={x} cy={y} r={13} fill="#fff" stroke={meta.color} strokeWidth="2" />
            <circle cx={x} cy={y} r={4} fill={meta.color} />
            <text x={x} y={y > cy ? y + 26 : y - 19} textAnchor="middle" fontSize="10.5" fontWeight="600"
              fill="var(--ink)" paintOrder="stroke" stroke="var(--bg)" strokeWidth="3" strokeLinejoin="round">
              {label}
            </text>
            <text x={x} y={y > cy ? y + 37 : y - 8} textAnchor="middle" fontSize="8.5"
              fill="var(--ink-muted)" paintOrder="stroke" stroke="var(--bg)" strokeWidth="3">
              {w} shared
            </text>
          </g>
        );
      })}
      {/* Centre node on top */}
      <circle cx={cx} cy={cy} r={21} fill={center.color} stroke="#fff" strokeWidth="3" />
      <text x={cx} y={cy + 3.5} textAnchor="middle" fontSize="9.5" fontWeight="700" fill="#fff">
        {node.label.length > 9 ? `${node.label.slice(0, 8)}…` : node.label}
      </text>
    </svg>
  );
}

// ── Entity details bottom sheet ──────────────────────────────────────────────

function EntitySheet({
  node, deg, neighbors, onSelect, onClose,
}: {
  node: GraphNode;
  deg: number;
  neighbors: { n: GraphNode; w: number }[];
  onSelect: (id: string) => void;
  onClose: () => void;
}) {
  const meta = TYPE_META[node.type] ?? TYPE_META.OTHER;
  const pages = [...node.pages].sort(
    (a, b) => new Date(b.freshness_at).getTime() - new Date(a.freshness_at).getTime(),
  );

  // Lock page scroll behind the sheet; restore on close/unmount.
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={`${node.label} details`}>
      {/* Backdrop */}
      <button aria-label="Close" onClick={onClose}
        className="absolute inset-0 bg-black/35 backdrop-blur-[1px]" />
      {/* Sheet */}
      <div className="sheet-in absolute inset-x-0 bottom-0 max-h-[82vh] overflow-y-auto overscroll-contain rounded-t-2xl bg-white shadow-[0_-12px_40px_rgba(0,0,0,0.18)]">
        <div className="sticky top-0 bg-white/95 backdrop-blur px-5 pt-2.5 pb-3 border-b border-[var(--border)]">
          <div className="mx-auto mb-2.5 h-1 w-10 rounded-full bg-gray-300" aria-hidden />
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0">
              {/* photo (people) / flag (countries) / type glyph */}
              <span className="grid place-items-center w-11 h-11 rounded-full shrink-0"
                style={{ background: `${meta.color}18`, color: meta.color }}>
                <EntityAvatar node={node} iconClass="w-5 h-5" flagClass="text-[22px] leading-none" />
              </span>
              <div className="min-w-0">
                <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest" style={{ color: meta.color }}>
                  {meta.label}
                </span>
                <h2 className="text-xl font-bold tracking-tight mt-0.5 truncate">{node.label}</h2>
                {node.description && (
                  <p className="text-[12.5px] text-[var(--ink-muted)] leading-snug mt-0.5 line-clamp-2">
                    {node.description}
                  </p>
                )}
              </div>
            </div>
            <button onClick={onClose} aria-label="Close details"
              className="shrink-0 grid place-items-center w-8 h-8 rounded-full bg-gray-100 text-[var(--ink-muted)] hover:text-[var(--ink)]">
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
            </button>
          </div>
          {node.image && node.image_attribution && (
            <p className="text-[9.5px] text-[var(--ink-muted)] mt-2 truncate">
              {node.image_source ? (
                <a href={node.image_source} target="_blank" rel="noopener noreferrer nofollow" className="hover:underline">
                  Photo: {node.image_attribution} · Wikimedia
                </a>
              ) : (<>Photo: {node.image_attribution} · Wikimedia</>)}
            </p>
          )}
        </div>

        <div className="px-5 py-4 flex flex-col gap-5 pb-8">
          {/* Stats */}
          <div className="grid grid-cols-2 gap-2.5">
            <div className="rounded-xl border border-[var(--border)] px-3.5 py-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)]">Stories</p>
              <p className="text-lg font-bold tabular-nums">{node.event_count}</p>
            </div>
            <div className="rounded-xl border border-[var(--border)] px-3.5 py-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)]">Connections</p>
              <p className="text-lg font-bold tabular-nums">{deg}</p>
            </div>
          </div>

          {/* Relationship preview */}
          {neighbors.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-1.5">
                Entity relationships
              </p>
              <div className="rounded-xl border border-[var(--border)] px-2 py-1"
                style={{ background: "radial-gradient(circle at 1px 1px, rgba(20,22,28,.05) 1px, transparent 0) 0 0 / 22px 22px, #fff" }}>
                <MiniGraph node={node} neighbors={neighbors} onSelect={onSelect} />
              </div>
            </div>
          )}

          {/* Coverage — pages are pre-trimmed server-side to the freshest N
              (see PAGES_PER_NODE in page.tsx); event_count is the true total. */}
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-1">
              Appears in
              {node.event_count > pages.length && (
                <span className="normal-case tracking-normal font-normal"> — {pages.length} most recent of {node.event_count}</span>
              )}
            </p>
            <div className="flex flex-col divide-y divide-[var(--border)]">
              {pages.map((pg) => (
                <Link key={pg.id} href={`/event/${pg.id}`} className="py-3 group">
                  <p className="text-[13px] font-medium leading-snug group-hover:text-[var(--accent)] transition-colors line-clamp-2">
                    {pg.headline}
                  </p>
                  <p className="text-[11px] text-[var(--ink-muted)] mt-1">
                    {pg.source_count} sources · {relativeTime(pg.freshness_at)}
                  </p>
                </Link>
              ))}
            </div>
          </div>

          {/* All connections */}
          {neighbors.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-2">
                Connected entities
              </p>
              <div className="flex flex-wrap gap-1.5">
                {neighbors.map(({ n }) => {
                  const nm = TYPE_META[n.type] ?? TYPE_META.OTHER;
                  return (
                    <button key={n.id} onClick={() => onSelect(n.id)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border border-[var(--border)] bg-white text-xs font-medium hover:border-gray-300 transition-colors">
                      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: nm.color }} />
                      {n.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Browser ──────────────────────────────────────────────────────────────────

const TOP_CARDS = 10; // horizontal card row; the rest list vertically

export default function EntityBrowser({
  data, onShowGraph,
}: {
  data: GraphData;
  onShowGraph: () => void;
}) {
  const { nodes, edges } = data;
  const [tab, setTab] = useState<EntityType>("PERSON");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const nodeMap = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  // Weighted adjacency: neighbor lists sorted by shared-story count.
  const { adjW, deg } = useMemo(() => {
    const adjW = new Map<string, Map<string, number>>();
    const deg = new Map<string, number>();
    nodes.forEach((n) => { adjW.set(n.id, new Map()); deg.set(n.id, 0); });
    edges.forEach((e) => {
      adjW.get(e.source)?.set(e.target, e.weight);
      adjW.get(e.target)?.set(e.source, e.weight);
      deg.set(e.source, (deg.get(e.source) ?? 0) + 1);
      deg.set(e.target, (deg.get(e.target) ?? 0) + 1);
    });
    return { adjW, deg };
  }, [nodes, edges]);

  const byType = useMemo(() => {
    const m = new Map<EntityType, GraphNode[]>();
    TYPE_ORDER.forEach((t) => m.set(t, []));
    nodes.forEach((n) => (m.get(n.type) ?? m.get("OTHER")!).push(n));
    m.forEach((list) => list.sort((a, b) => b.event_count - a.event_count));
    return m;
  }, [nodes]);

  // Default to the first tab that actually has entities.
  useEffect(() => {
    if ((byType.get(tab) ?? []).length === 0) {
      const first = TYPE_ORDER.find((t) => (byType.get(t) ?? []).length > 0);
      if (first) setTab(first);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [byType]);

  const q = query.trim().toLowerCase();
  const results = useMemo(
    () => (q ? nodes.filter((n) => n.label.toLowerCase().includes(q))
                   .sort((a, b) => b.event_count - a.event_count).slice(0, 30)
             : null),
    [nodes, q],
  );

  const items = byType.get(tab) ?? [];
  const topItems = items.slice(0, TOP_CARDS);
  const restItems = items.slice(TOP_CARDS);

  const selNode = selected ? nodeMap.get(selected) ?? null : null;
  const selNeighbors = useMemo(() => {
    if (!selected) return [];
    return [...(adjW.get(selected) ?? new Map<string, number>())]
      .map(([id, w]) => ({ n: nodeMap.get(id), w }))
      .filter((x): x is { n: GraphNode; w: number } => Boolean(x.n))
      .sort((a, b) => b.w - a.w);
  }, [selected, adjW, nodeMap]);

  function EntityRow({ n }: { n: GraphNode }) {
    const meta = TYPE_META[n.type] ?? TYPE_META.OTHER;
    return (
      <button onClick={() => setSelected(n.id)}
        className="flex items-center gap-3 w-full py-3 border-b border-[var(--border)] last:border-0 text-left">
        <span className="grid place-items-center w-8 h-8 rounded-full shrink-0"
          style={{ background: `${meta.color}18`, color: meta.color }}>
          <EntityAvatar node={n} iconClass="w-4 h-4" flagClass="text-[15px] leading-none" />
        </span>
        <span className="flex-1 min-w-0">
          <span className="block text-sm font-semibold truncate">{n.label}</span>
          <span className="block text-[11px] text-[var(--ink-muted)]">
            {n.event_count} {n.event_count === 1 ? "story" : "stories"} · {deg.get(n.id) ?? 0} connections
          </span>
        </span>
        <svg className="w-4 h-4 shrink-0 text-[var(--ink-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Entities</h1>
          <p className="text-[11px] font-mono text-[var(--ink-muted)] mt-1 tracking-wide">
            {data.meta.node_count} ENTITIES · {data.meta.edge_count} LINKS · {data.meta.event_count} EVENTS
          </p>
        </div>
        <button onClick={onShowGraph}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border border-[var(--border)] text-[var(--accent)] hover:bg-[var(--accent)]/5 shrink-0">
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="5" cy="6" r="2.4"/><circle cx="19" cy="7" r="2.4"/><circle cx="12" cy="18" r="2.4"/>
            <path d="M7 7 17 7M6.5 8 11 16M17.5 9 13 16"/>
          </svg>
          Full graph
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--ink-muted)] pointer-events-none"
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
        </svg>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find an entity…"
          className="w-full pl-8 pr-3 py-2 text-sm bg-white border border-[var(--border)] rounded-full outline-none focus:border-gray-400 transition-colors" />
      </div>

      {results ? (
        /* Search results — flat, cross-type */
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-1">
            {results.length} {results.length === 1 ? "match" : "matches"}
          </p>
          <div>{results.map((n) => <EntityRow key={n.id} n={n} />)}</div>
          {results.length === 0 && (
            <p className="py-8 text-center text-sm text-[var(--ink-muted)]">No entity matches “{query.trim()}”.</p>
          )}
        </div>
      ) : (
        <>
          {/* Type tabs */}
          <div className="-mx-4 px-4 overflow-x-auto scrollbar-hide border-b border-[var(--border)]">
            <div className="flex items-center gap-1 flex-nowrap">
              {TYPE_ORDER.map((t) => {
                const meta = TYPE_META[t];
                const count = (byType.get(t) ?? []).length;
                if (count === 0) return null;
                const active = tab === t;
                return (
                  <button key={t} onClick={() => setTab(t)} aria-pressed={active}
                    className={`inline-flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors ${
                      active ? "border-[var(--accent)] text-[var(--ink)]" : "border-transparent text-[var(--ink-muted)]"
                    }`}>
                    <TypeIcon type={t} className="w-4 h-4" />
                    {meta.label}
                    <span className="text-[10px] font-mono text-[var(--ink-muted)]">{count}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Top entities — horizontal snap cards */}
          <div className="-mx-4 px-4 overflow-x-auto scrollbar-hide">
            <div className="flex gap-2.5 snap-x snap-mandatory pb-1">
              {topItems.map((n) => {
                const meta = TYPE_META[n.type] ?? TYPE_META.OTHER;
                return (
                  <button key={n.id} onClick={() => setSelected(n.id)}
                    className="snap-start shrink-0 w-[150px] rounded-xl border border-[var(--border)] bg-white p-3 text-left hover:shadow-sm transition-shadow">
                    <span className="grid place-items-center w-9 h-9 rounded-full mb-2"
                      style={{ background: `${meta.color}18`, color: meta.color }}>
                      <EntityAvatar node={n} iconClass="w-4.5 h-4.5" flagClass="text-[18px] leading-none" />
                    </span>
                    <span className="block text-[13px] font-bold leading-snug line-clamp-2 min-h-[2.4em]">{n.label}</span>
                    <span className="mt-1.5 inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{ background: `${meta.color}14`, color: meta.color }}>
                      {n.event_count} {n.event_count === 1 ? "story" : "stories"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* The rest — vertical rows */}
          {restItems.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-1">
                All {(TYPE_META[tab] ?? TYPE_META.OTHER).label.toLowerCase()}
              </p>
              <div>{restItems.map((n) => <EntityRow key={n.id} n={n} />)}</div>
            </div>
          )}
        </>
      )}

      {/* Details sheet */}
      {selNode && (
        <EntitySheet
          node={selNode}
          deg={deg.get(selNode.id) ?? 0}
          neighbors={selNeighbors}
          onSelect={(id) => setSelected(id)}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
