"use client";

/**
 * VideoCoverflow — the event page's video rail as a 3D coverflow (ADR-R-0010
 * family: same CSS perspective/rotateY technique as the topic carousel, no
 * libs, no WASM). Center card enlarged with a glow, neighbors angled away;
 * swipe / chevrons / dots / arrow keys navigate; tapping the center card opens
 * the video, tapping a side card brings it to center.
 *
 * Replaces the flat chip row in the media drawer (ADR-R-0006 video-only rail).
 */

import { useRef, useState } from "react";
import type { MediaRailItem } from "@/lib/types";

const SPACING = 170;    // px between card centers
const SIDE_ANGLE = 32;  // deg the side cards turn inward
const SIDE_DEPTH = 110; // px side cards recede
const SWIPE_PX = 48;    // horizontal movement that counts as a swipe

function qualityLabel(v: MediaRailItem): string | null {
  const h = v.height ?? 0;
  if (h >= 2160) return "4K";
  if (h >= 1080) return "1080p";
  if (h >= 720) return "720p";
  return null;
}

function dateLabel(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function VideoCoverflow({ videos }: { videos: MediaRailItem[] }) {
  const [active, setActive] = useState(0);
  const drag = useRef<{ x: number } | null>(null);
  const clamp = (i: number) => Math.max(0, Math.min(videos.length - 1, i));

  if (videos.length === 0) return null;

  return (
    <div
      className="relative rounded-2xl overflow-hidden select-none"
      style={{ background: "radial-gradient(120% 130% at 50% 0%, #14141f 0%, #0a0a11 60%)" }}
    >
      {/* Stage */}
      <div
        className="relative h-[248px] sm:h-[264px] outline-none"
        style={{ perspective: "1200px", touchAction: "pan-y" }}
        tabIndex={0}
        role="group"
        aria-label={`${videos.length} videos — use arrow keys to browse`}
        onPointerDown={(e) => { drag.current = { x: e.clientX }; }}
        onPointerUp={(e) => {
          const d = drag.current; drag.current = null;
          if (!d) return;
          const dx = e.clientX - d.x;
          if (Math.abs(dx) >= SWIPE_PX) setActive((a) => clamp(a + (dx < 0 ? 1 : -1)));
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") { e.preventDefault(); setActive((a) => clamp(a + 1)); }
          if (e.key === "ArrowLeft")  { e.preventDefault(); setActive((a) => clamp(a - 1)); }
        }}
      >
        {videos.map((vid, i) => {
          const d = i - active;
          const abs = Math.abs(d);
          if (abs > 3) return null;
          const isCenter = d === 0;
          const q = qualityLabel(vid);
          const date = dateLabel(vid.published_at);
          const transform =
            `translate(-50%, -50%) translateX(${d * SPACING}px) ` +
            `rotateY(${isCenter ? 0 : d < 0 ? SIDE_ANGLE : -SIDE_ANGLE}deg) ` +
            `translateZ(${isCenter ? 0 : -SIDE_DEPTH}px) scale(${isCenter ? 1 : 0.88})`;
          return (
            <a
              key={i}
              href={vid.url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={vid.title ?? `Video ${i + 1}`}
              aria-current={isCenter ? "true" : undefined}
              onClick={(e) => {
                if (!isCenter) { e.preventDefault(); setActive(i); }
              }}
              className="vcf-card absolute left-1/2 top-1/2 w-[min(64vw,270px)] rounded-xl overflow-hidden bg-[#12121c]"
              style={{
                transform,
                zIndex: 20 - abs,
                opacity: abs > 2 ? 0 : 1,
                pointerEvents: abs > 2 ? "none" : undefined,
                boxShadow: isCenter
                  ? "0 0 0 1.5px rgba(129,120,255,0.75), 0 14px 44px rgba(84,70,220,0.35)"
                  : "0 10px 30px rgba(0,0,0,0.5)",
              }}
              draggable={false}
            >
              {/* Thumb (16:9) with play + quality badge */}
              <span className="relative block aspect-video bg-[#191926]">
                {vid.thumb_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={vid.thumb_url} alt="" loading="lazy" draggable={false}
                    className="absolute inset-0 w-full h-full object-cover"
                  />
                )}
                <span className={`absolute inset-0 ${isCenter ? "bg-black/15" : "bg-black/45"} transition-colors`} />
                <span className="absolute inset-0 grid place-items-center">
                  <span className={`grid place-items-center rounded-full bg-black/55 backdrop-blur-[2px] ${isCenter ? "w-12 h-12" : "w-10 h-10"}`}>
                    <svg className="w-5 h-5 fill-white translate-x-[1px]" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                  </span>
                </span>
                {q && (
                  <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/70 text-white text-[10px] font-semibold tabular-nums">
                    {q}
                  </span>
                )}
              </span>
              {/* Caption */}
              <span className="block px-3 py-2.5">
                <span className="block text-[12.5px] font-semibold text-white leading-snug truncate">
                  {vid.title ?? vid.source_domain ?? "Watch video"}
                </span>
                <span className="block text-[10.5px] text-white/55 mt-0.5 truncate">
                  {[vid.source_domain, date].filter(Boolean).join(" · ") || "External video"}
                </span>
              </span>
            </a>
          );
        })}

        {/* Chevrons */}
        <button
          type="button" aria-label="Previous video" disabled={active === 0}
          onClick={() => setActive((a) => clamp(a - 1))}
          className="absolute left-2 top-1/2 -translate-y-1/2 z-30 grid place-items-center w-9 h-9 rounded-full bg-white/10 text-white/80 hover:bg-white/20 disabled:opacity-25 disabled:pointer-events-none transition-colors"
        >
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
        </button>
        <button
          type="button" aria-label="Next video" disabled={active === videos.length - 1}
          onClick={() => setActive((a) => clamp(a + 1))}
          className="absolute right-2 top-1/2 -translate-y-1/2 z-30 grid place-items-center w-9 h-9 rounded-full bg-white/10 text-white/80 hover:bg-white/20 disabled:opacity-25 disabled:pointer-events-none transition-colors"
        >
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
        </button>
      </div>

      {/* Dots */}
      <div className="flex items-center justify-center gap-1.5 pb-3.5">
        {videos.map((_, i) => (
          <button
            key={i}
            type="button"
            aria-label={`Go to video ${i + 1}`}
            aria-current={i === active}
            onClick={() => setActive(i)}
            className={`rounded-full transition-all ${
              i === active ? "w-4 h-1.5 bg-[#8178ff]" : "w-1.5 h-1.5 bg-white/25 hover:bg-white/45"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
