"use client";

/**
 * TopicCarousel — 3D rotating ring of topic "folders" (mobile home nav).
 *
 * Replaces the 16-chip horizontal scroll row on small screens: each theme is a
 * folder card (live event count) arranged on a CSS 3D ring. Swipe/drag rotates
 * the ring; the card that settles front-and-center applies the category filter
 * (client-side — same setCat the chips use, zero server cost). Tap any visible
 * card to rotate straight to it.
 *
 * Deliberately NO WebAssembly / animation lib: `perspective` + `rotateY() ·
 * translateZ()` is GPU-composited and runs at 60fps on mid-range phones.
 * During drag we write the ring transform directly via rAF (no React re-render
 * per pointermove); React state only owns the settled angle.
 */

import { useEffect, useRef, useState } from "react";
import FolderGlyph from "@/components/folder-glyph";

export interface TopicItem {
  key: string;
  label: string;
  count: number;
}

interface Props {
  items: TopicItem[];
  active: string;
  onSelect: (key: string) => void;
}

// Per-theme accent — the icon is the ONLY colored element (the neutral-gray
// folder is a recessive container). Hues match CAT_STYLES / TREND_ACCENT.
const THEME_ACCENT: Record<string, string> = {
  all:           "#26264f",
  politics:      "#ef4444",
  business:      "#3b82f6",
  technology:    "#8b5cf6",
  sports:        "#22c55e",
  health:        "#ec4899",
  environment:   "#10b981",
  culture:       "#f59e0b",
  world:         "#64748b",
  science:       "#06b6d4",
  entertainment: "#d946ef",
  crime:         "#475569",
  education:     "#6366f1",
  lifestyle:     "#14b8a6",
  religion:      "#eab308",
  disaster:      "#f97316",
};

const CARD_W = 148;         // folder width (px) — must match .tc-ring CSS
const PX_PER_STEP = 80;     // horizontal drag distance = one card step
const TAP_SLOP = 8;         // px of movement below which a drag is a tap

function mod(n: number, m: number): number {
  return ((n % m) + m) % m;
}

export default function TopicCarousel({ items, active, onSelect }: Props) {
  const N = items.length;
  const theta = 360 / N;
  // Ring radius so adjacent folders just clear each other (+gap), floored so a
  // short list (few themes that day) still reads as a ring, not a flat fan.
  const radius = Math.max(
    170,
    Math.round((CARD_W / 2 + 14) / Math.tan(Math.PI / Math.max(N, 3))),
  );

  const [angle, setAngle] = useState(() => {
    const idx = items.findIndex((i) => i.key === active);
    return idx > 0 ? -idx * theta : 0;
  });
  const [dragging, setDragging] = useState(false);

  const ringRef = useRef<HTMLDivElement>(null);
  const angleRef = useRef(angle);
  angleRef.current = angle;
  const drag = useRef<{ startX: number; startAngle: number; live: number } | null>(null);
  const suppressClick = useRef(false);
  const raf = useRef(0);

  const setAngleTo = (a: number) => {
    angleRef.current = a;
    setAngle(a);
  };

  // Follow external category changes (chip on desktop, clearAll, localStorage
  // restore): rotate to the nearest ring-equivalent of the active index.
  useEffect(() => {
    const idx = items.findIndex((i) => i.key === active);
    if (idx < 0) return;
    const cur = angleRef.current;
    const k = Math.round((-cur / theta - idx) / N);
    const target = -(idx + k * N) * theta;
    if (Math.abs(target - cur) > 0.5) setAngleTo(target);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, N, theta]);

  const settle = (rawAngle: number) => {
    const nearest = Math.round(-rawAngle / theta);
    setAngleTo(-nearest * theta);
    const key = items[mod(nearest, N)]?.key;
    if (key && key !== active) onSelect(key);
  };

  // ── Pointer drag: rAF-batched direct transform writes ──────────────────────
  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    drag.current = { startX: e.clientX, startAngle: angleRef.current, live: angleRef.current };
    suppressClick.current = false;
    setDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    const d = drag.current;
    if (!d) return;
    const dx = e.clientX - d.startX;
    if (Math.abs(dx) > TAP_SLOP) suppressClick.current = true;
    d.live = d.startAngle + (dx / PX_PER_STEP) * theta;
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(() => {
      if (ringRef.current)
        ringRef.current.style.transform = `translateZ(${-radius}px) rotateY(${d.live}deg)`;
    });
  }

  function onPointerEnd() {
    const d = drag.current;
    drag.current = null;
    cancelAnimationFrame(raf.current);
    setDragging(false);
    if (d) settle(d.live);
  }

  function goTo(idx: number) {
    if (suppressClick.current) {
      suppressClick.current = false;
      return;
    }
    const k = Math.round((-angleRef.current / theta - idx) / N);
    setAngleTo(-(idx + k * N) * theta);
    const key = items[idx]?.key;
    if (key && key !== active) onSelect(key);
  }

  function step(dir: 1 | -1) {
    const next = Math.round(-angleRef.current / theta) + dir;
    setAngleTo(-next * theta);
    const key = items[mod(next, N)]?.key;
    if (key && key !== active) onSelect(key);
  }

  if (N === 0) return null;

  return (
    <div className="relative select-none">
      {/* Stage: perspective viewport, edge-faded; pan-y keeps page scroll alive */}
      <div
        className="tc-stage"
        role="listbox"
        aria-label="Browse topics"
        tabIndex={0}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerEnd}
        onPointerCancel={onPointerEnd}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") { e.preventDefault(); step(1); }
          if (e.key === "ArrowLeft")  { e.preventDefault(); step(-1); }
        }}
      >
        <div
          ref={ringRef}
          className={`tc-ring ${dragging ? "tc-dragging" : ""}`}
          style={{ transform: `translateZ(${-radius}px) rotateY(${angle}deg)` }}
        >
          {items.map((it, i) => {
            const accent = THEME_ACCENT[it.key] ?? THEME_ACCENT.world;
            return (
              <button
                key={it.key}
                type="button"
                role="option"
                aria-selected={it.key === active}
                className="tc-card"
                style={{ transform: `rotateY(${i * theta}deg) translateZ(${radius}px)` }}
                onClick={() => goTo(i)}
              >
                <span
                  className="tc-plate"
                  style={{ "--fa": accent } as React.CSSProperties}
                >
                  <span className="tc-fglyph">
                    <FolderGlyph className="w-full h-full" />
                  </span>
                  <span className="tc-meta">
                    <span className="tc-label">{it.label}</span>
                    <span className="tc-sub">
                      {it.count} {it.count === 1 ? "story" : "stories"}
                    </span>
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Chevrons — outside the masked stage so they don't fade */}
      <button
        type="button"
        aria-label="Previous topic"
        onClick={() => step(-1)}
        className="tc-chev left-0"
      >
        <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <button
        type="button"
        aria-label="Next topic"
        onClick={() => step(1)}
        className="tc-chev right-0"
      >
        <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>

    </div>
  );
}
