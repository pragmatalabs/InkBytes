"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useMemo } from "react";
import { relativeTime } from "@/lib/api";
import type { GraphData, GraphNode, GraphEdge, EntityType } from "@/lib/types";

// ── Type metadata ────────────────────────────────────────────────────────────

const TYPE_META: Record<EntityType, { label: string; color: string }> = {
  PERSON: { label: "People",        color: "#3b82f6" },
  ORG:    { label: "Organisations", color: "#8b5cf6" },
  LOC:    { label: "Places",        color: "#10b981" },
  EVENT:  { label: "Events",        color: "#f97316" },
  OTHER:  { label: "Topics",        color: "#6b7280" },
};
const TYPE_ORDER: EntityType[] = ["PERSON", "ORG", "LOC", "EVENT", "OTHER"];

// ── Force simulation constants ───────────────────────────────────────────────
const REP    = 6200;
const LINK_D = 110;
const LINK_S = 0.045;
const CENTER = 0.011;
const ANCHOR = 0.014;

// ── Helpers ──────────────────────────────────────────────────────────────────

function nodeRadius(n: GraphNode, deg: number): number {
  return 6 + Math.sqrt(n.event_count) * 4 + Math.min(deg, 8) * 0.45;
}

// ── Mobile entity list ───────────────────────────────────────────────────────

function MobileList({ nodes, onSelect }: {
  nodes: GraphNode[];
  onSelect: (n: GraphNode) => void;
}) {
  return (
    <div className="px-4 pb-10">
      {TYPE_ORDER.map((type) => {
        const group = nodes.filter((n) => n.type === type).sort((a, b) => b.event_count - a.event_count);
        if (group.length === 0) return null;
        const { label, color } = TYPE_META[type];
        return (
          <div key={type} className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: color }} />
              <span className="text-[11px] font-semibold uppercase tracking-widest text-[var(--ink-muted)]">
                {label}
              </span>
              <span className="text-[11px] text-[var(--ink-muted)]">({group.length})</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {group.map((n) => (
                <button
                  key={n.id}
                  onClick={() => onSelect(n)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[var(--border)] bg-white text-sm font-medium hover:border-gray-300 hover:shadow-sm transition-all"
                >
                  <span className="inline-block w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                  {n.label}
                  <span className="text-[11px] font-mono text-[var(--ink-muted)]">{n.event_count}</span>
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Entity side panel ────────────────────────────────────────────────────────

function EntityPanel({
  node, deg, neighbors, nodeMap, onSelect, onClose,
}: {
  node: GraphNode | null;
  deg: number;
  neighbors: Set<string>;
  nodeMap: Map<string, GraphNode>;
  onSelect: (id: string) => void;
  onClose: () => void;
}) {
  if (!node) {
    const topNodes = [...nodeMap.values()]
      .sort((a, b) => b.event_count - a.event_count)
      .slice(0, 8);
    return (
      <div className="p-5 flex flex-col gap-4">
        <h2 className="text-lg font-bold tracking-tight">Navigate the news by who &amp; what</h2>
        <p className="text-sm text-[var(--ink-muted)] leading-relaxed">
          Every story is parsed for named entities — people, places, organisations and topics.
          Nodes that share a story are linked. Click any node to pull up its coverage.
        </p>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-3">
            Most connected
          </p>
          <div className="flex flex-wrap gap-2">
            {topNodes.map((n) => {
              const { color } = TYPE_META[n.type] ?? TYPE_META.OTHER;
              return (
                <button key={n.id} onClick={() => onSelect(n.id)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[var(--border)] bg-white text-xs font-medium hover:border-gray-300 transition-colors">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                  {n.label}
                  <span className="font-mono text-[var(--ink-muted)]">{n.event_count}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  const { label, color } = TYPE_META[node.type] ?? TYPE_META.OTHER;
  const sortedPages = [...node.pages].sort(
    (a, b) => new Date(b.freshness_at).getTime() - new Date(a.freshness_at).getTime()
  );
  const neighborNodes = [...neighbors]
    .map((id) => nodeMap.get(id))
    .filter(Boolean)
    .sort((a, b) => b!.event_count - a!.event_count) as GraphNode[];

  return (
    <div className="p-5 overflow-y-auto flex flex-col gap-4 h-full">
      <button onClick={onClose}
        className="flex items-center gap-1.5 text-xs text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors">
        ← All entities
      </button>

      <div>
        <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest"
          style={{ color }}>
          <span className="w-2 h-2 rounded-full" style={{ background: color }} />
          {(TYPE_META[node.type] ?? TYPE_META.OTHER).label}
        </span>
        <h3 className="text-xl font-bold tracking-tight mt-2">{node.label}</h3>
        <p className="text-xs text-[var(--ink-muted)] mt-1">
          {node.event_count} {node.event_count === 1 ? "story" : "stories"} · {deg} {deg === 1 ? "connection" : "connections"}
        </p>
      </div>

      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-2">
          Appears in
        </p>
        <div className="flex flex-col divide-y divide-[var(--border)]">
          {sortedPages.map((pg) => (
            <Link key={pg.id} href={`/event/${pg.id}`}
              className="py-3 group">
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

      {neighborNodes.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-2">
            Connected entities
          </p>
          <div className="flex flex-wrap gap-1.5">
            {neighborNodes.map((n) => {
              const nc = TYPE_META[n.type] ?? TYPE_META.OTHER;
              return (
                <button key={n.id} onClick={() => onSelect(n.id)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[var(--border)] bg-white text-xs font-medium hover:border-gray-300 transition-colors">
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: nc.color }} />
                  {n.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Force graph (desktop) ────────────────────────────────────────────────────

interface Pos { x: number; y: number; vx: number; vy: number; fx: number | null; fy: number | null }

export default function GraphClient({ data }: { data: GraphData }) {
  const { nodes, edges } = data;

  // Precompute adjacency and degree
  const { adj, deg } = useMemo(() => {
    const adj = new Map<string, Set<string>>();
    const deg = new Map<string, number>();
    nodes.forEach((n) => { adj.set(n.id, new Set()); deg.set(n.id, 0); });
    edges.forEach((e) => {
      adj.get(e.source)?.add(e.target);
      adj.get(e.target)?.add(e.source);
      deg.set(e.source, (deg.get(e.source) ?? 0) + e.weight);
      deg.set(e.target, (deg.get(e.target) ?? 0) + e.weight);
    });
    return { adj, deg };
  }, [nodes, edges]);

  const nodeMap = useMemo(
    () => new Map(nodes.map((n) => [n.id, n])),
    [nodes],
  );

  // Force sim state — refs to avoid re-rendering on every tick
  const stageRef  = useRef<SVGSVGElement>(null);
  const posRef    = useRef<Record<string, Pos>>({});
  const alphaRef  = useRef(1);
  const rafRef    = useRef(0);
  const dragRef   = useRef<{ id: string; moved: boolean; ox: number; oy: number } | null>(null);
  const dimsRef   = useRef({ w: 800, h: 560 });

  const [dims, setDims]         = useState({ w: 800, h: 560 });
  const [, setFrame]            = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered]   = useState<string | null>(null);
  const [hidden, setHidden]     = useState<Set<EntityType>>(new Set());
  const [query, setQuery]       = useState("");

  // Type-cluster anchor points (ring layout)
  const anchors = useMemo(() => {
    const { w, h } = dims;
    const cx = w / 2, cy = h / 2;
    const R = Math.min(w, h) * 0.33;
    const a: Record<EntityType, { x: number; y: number }> = {} as never;
    TYPE_ORDER.forEach((t, i) => {
      const ang = -Math.PI / 2 + (i / TYPE_ORDER.length) * Math.PI * 2;
      a[t] = { x: cx + Math.cos(ang) * R, y: cy + Math.sin(ang) * R };
    });
    return a;
  }, [dims.w, dims.h]);

  // Initialise positions
  useEffect(() => {
    const p: Record<string, Pos> = {};
    const prev = posRef.current;
    nodes.forEach((n) => {
      if (prev[n.id]) { p[n.id] = prev[n.id]; return; }
      const an = anchors[n.type] ?? anchors.OTHER;
      p[n.id] = {
        x: an.x + (Math.random() - 0.5) * 80,
        y: an.y + (Math.random() - 0.5) * 80,
        vx: 0, vy: 0, fx: null, fy: null,
      };
    });
    posRef.current = p;
    alphaRef.current = 1;
    ensureRunning();
  }, [nodes, anchors]);

  // Resize observer
  useEffect(() => {
    const el = stageRef.current?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      const w = Math.max(320, r.width);
      const h = Math.max(360, r.height);
      dimsRef.current = { w, h };
      setDims({ w, h });
      alphaRef.current = Math.max(alphaRef.current, 0.5);
      ensureRunning();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);

  function ensureRunning() {
    if (rafRef.current) return;
    const loop = () => {
      step();
      setFrame((f) => (f + 1) & 0xffff);
      if (alphaRef.current > 0.02 || dragRef.current) {
        rafRef.current = requestAnimationFrame(loop);
      } else {
        rafRef.current = 0;
      }
    };
    rafRef.current = requestAnimationFrame(loop);
  }

  function reheat(v = 0.5) {
    alphaRef.current = Math.max(alphaRef.current, v);
    ensureRunning();
  }

  function step() {
    const p   = posRef.current;
    const { w, h } = dimsRef.current;
    const alpha = alphaRef.current;

    // Repulsion (all pairs)
    for (let i = 0; i < nodes.length; i++) {
      const a = p[nodes[i].id]; if (!a) continue;
      for (let j = i + 1; j < nodes.length; j++) {
        const b = p[nodes[j].id]; if (!b) continue;
        let dx = a.x - b.x, dy = a.y - b.y;
        let d2 = dx * dx + dy * dy; if (d2 < 1) d2 = 1;
        const d = Math.sqrt(d2);
        const f = (REP / d2) * alpha;
        const fx = (dx / d) * f, fy = (dy / d) * f;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
      }
    }
    // Spring forces along edges
    edges.forEach((l) => {
      const a = p[l.source], b = p[l.target]; if (!a || !b) return;
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const f = ((d - LINK_D) * LINK_S) * alpha;
      const fx = (dx / d) * f, fy = (dy / d) * f;
      a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
    });
    // Anchor + centre + integrate
    nodes.forEach((n) => {
      const a = p[n.id]; if (!a) return;
      const an = anchors[n.type] ?? { x: w / 2, y: h / 2 };
      a.vx += (an.x - a.x) * ANCHOR * alpha;
      a.vy += (an.y - a.y) * ANCHOR * alpha;
      a.vx += (w / 2 - a.x) * CENTER * alpha;
      a.vy += (h / 2 - a.y) * CENTER * alpha;
      if (a.fx != null) { a.x = a.fx; a.y = a.fy!; a.vx = 0; a.vy = 0; return; }
      a.vx *= 0.82; a.vy *= 0.82;
      const sp = Math.hypot(a.vx, a.vy);
      if (sp > 18) { a.vx *= 18 / sp; a.vy *= 18 / sp; }
      a.x += a.vx; a.y += a.vy;
      const pad = 32;
      a.x = Math.max(pad, Math.min(w - pad, a.x));
      a.y = Math.max(pad, Math.min(h - pad, a.y));
    });
    alphaRef.current = Math.max(0, alpha * 0.985);
  }

  function svgCoord(e: React.PointerEvent) {
    const r = (e.currentTarget as SVGElement).getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }
  function onPointerDownNode(e: React.PointerEvent, id: string) {
    e.stopPropagation();
    const pt   = svgCoord(e);
    const node = posRef.current[id];
    dragRef.current = { id, moved: false, ox: node.x - pt.x, oy: node.y - pt.y };
    node.fx = node.x; node.fy = node.y;
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    reheat(0.3);
  }
  function onPointerMove(e: React.PointerEvent) {
    if (!dragRef.current) return;
    const pt   = svgCoord(e);
    const node = posRef.current[dragRef.current.id];
    node.fx = pt.x + dragRef.current.ox;
    node.fy = pt.y + dragRef.current.oy;
    dragRef.current.moved = true;
    reheat(0.25);
  }
  function onPointerUp(e: React.PointerEvent) {
    if (!dragRef.current) return;
    const { id, moved } = dragRef.current;
    const node = posRef.current[id];
    node.fx = null; node.fy = null;
    if (!moved) setSelected((s) => s === id ? null : id);
    dragRef.current = null;
    reheat(0.3);
  }

  const q = query.trim().toLowerCase();
  const focusId     = hovered ?? selected;
  const neighborSet = focusId ? (adj.get(focusId) ?? new Set<string>()) : new Set<string>();

  function visible(n: GraphNode) { return !hidden.has(n.type); }
  function isDim(id: string) {
    const n = nodeMap.get(id);
    if (!n) return true;
    if (hidden.has(n.type)) return true;
    if (q && !n.label.toLowerCase().includes(q)) return true;
    if (focusId && id !== focusId && !neighborSet.has(id)) return true;
    return false;
  }

  const p = posRef.current;
  const typeCounts = TYPE_ORDER.map((t) => nodes.filter((n) => n.type === t).length);

  const selNode   = selected ? (nodeMap.get(selected) ?? null) : null;
  const selDeg    = selected ? (deg.get(selected) ?? 0) : 0;
  const selNeighbors = selected ? (adj.get(selected) ?? new Set<string>()) : new Set<string>();

  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Entity graph</h1>
          <p className="text-[11px] font-mono text-[var(--ink-muted)] mt-1 tracking-wide">
            {data.meta.node_count} ENTITIES · {data.meta.edge_count} LINKS · {data.meta.event_count} EVENTS
          </p>
        </div>
        {/* Search */}
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--ink-muted)] pointer-events-none"
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
          </svg>
          <input
            value={query}
            onChange={(e) => { setQuery(e.target.value); reheat(0.2); }}
            placeholder="Find an entity…"
            className="pl-8 pr-3 py-1.5 text-sm bg-white border border-[var(--border)] rounded-full outline-none focus:border-gray-400 transition-colors w-52"
          />
        </div>
      </div>

      {/* Type filter legend */}
      <div className="flex flex-wrap gap-2">
        {TYPE_ORDER.map((t, i) => {
          const { label, color } = TYPE_META[t];
          const off = hidden.has(t);
          return (
            <button key={t}
              onClick={() => {
                setHidden((h) => {
                  const s = new Set(h);
                  s.has(t) ? s.delete(t) : s.add(t);
                  return s;
                });
                reheat(0.4);
              }}
              className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium transition-all ${off ? "opacity-40 border-[var(--border)] bg-white" : "border-[var(--border)] bg-white"}`}
            >
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
              {label}
              <span className="font-mono text-[var(--ink-muted)]">{typeCounts[i]}</span>
            </button>
          );
        })}
      </div>

      {/* Desktop: force graph + side panel */}
      <div className="hidden md:grid gap-4" style={{ gridTemplateColumns: "1fr 320px" }}>
        {/* SVG stage */}
        <div
          className="relative rounded-xl border border-[var(--border)] overflow-hidden"
          style={{
            background: "radial-gradient(circle at 1px 1px, rgba(20,22,28,.05) 1px, transparent 0) 0 0 / 26px 26px, var(--bg)",
            height: "min(72vh, 700px)",
            minHeight: 440,
          }}
        >
          <svg
            ref={stageRef}
            viewBox={`0 0 ${dims.w} ${dims.h}`}
            className="block w-full h-full"
            style={{ cursor: dragRef.current ? "grabbing" : "grab" }}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerLeave={onPointerUp}
            onPointerDown={() => setSelected(null)}
          >
            {/* Edges */}
            <g>
              {edges.map((e, i) => {
                const a = p[e.source], b = p[e.target];
                if (!a || !b) return null;
                if (!visible(nodeMap.get(e.source)!) || !visible(nodeMap.get(e.target)!)) return null;
                const active = focusId && (e.source === focusId || e.target === focusId);
                return (
                  <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                    stroke={active ? "var(--accent)" : "#e5e5e5"}
                    strokeWidth={active ? 1.8 : 1}
                    strokeOpacity={focusId ? (active ? 0.9 : 0.1) : 0.6}
                  />
                );
              })}
            </g>
            {/* Nodes */}
            <g>
              {nodes.map((n) => {
                const a = p[n.id];
                if (!a || !visible(n)) return null;
                const r   = nodeRadius(n, deg.get(n.id) ?? 0);
                const dim = isDim(n.id);
                const sel = selected === n.id;
                const { color } = TYPE_META[n.type] ?? TYPE_META.OTHER;
                const showLabel = sel || hovered === n.id || n.event_count >= 4
                  || (focusId && (n.id === focusId || neighborSet.has(n.id)));
                return (
                  <g key={n.id} opacity={dim ? 0.22 : 1}
                    style={{ cursor: "pointer" }}
                    onPointerDown={(e) => onPointerDownNode(e, n.id)}
                    onPointerEnter={() => setHovered(n.id)}
                    onPointerLeave={() => setHovered(null)}
                  >
                    {sel && (
                      <circle cx={a.x} cy={a.y} r={r + 5}
                        fill="none" stroke={color} strokeWidth="2" opacity="0.5" />
                    )}
                    <circle cx={a.x} cy={a.y} r={r}
                      fill={color} stroke="var(--bg)" strokeWidth="2" />
                    {showLabel && (
                      <text
                        x={a.x} y={a.y + r + 13}
                        textAnchor="middle"
                        fontSize={n.event_count >= 4 ? 12 : 11}
                        fontWeight="600"
                        fill="var(--ink)"
                        paintOrder="stroke"
                        stroke="var(--bg)"
                        strokeWidth="3"
                        strokeLinejoin="round"
                        style={{ pointerEvents: "none" }}
                      >
                        {n.label}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>
          <p className="absolute left-3 bottom-2.5 text-[10px] font-mono text-[var(--ink-muted)] pointer-events-none">
            drag to rearrange · click a node to focus
          </p>
        </div>

        {/* Side panel */}
        <div className="rounded-xl border border-[var(--border)] bg-white overflow-y-auto" style={{ maxHeight: "min(72vh, 700px)" }}>
          <EntityPanel
            node={selNode}
            deg={selDeg}
            neighbors={selNeighbors}
            nodeMap={nodeMap}
            onSelect={(id) => { setSelected(id); setHovered(null); reheat(0.55); }}
            onClose={() => setSelected(null)}
          />
        </div>
      </div>

      {/* Mobile: entity list */}
      <div className="md:hidden">
        {selNode ? (
          <div className="rounded-xl border border-[var(--border)] bg-white">
            <EntityPanel
              node={selNode}
              deg={selDeg}
              neighbors={selNeighbors}
              nodeMap={nodeMap}
              onSelect={(id) => setSelected(id)}
              onClose={() => setSelected(null)}
            />
          </div>
        ) : (
          <MobileList nodes={nodes.filter((n) => !hidden.has(n.type))} onSelect={(n) => setSelected(n.id)} />
        )}
      </div>
    </div>
  );
}
