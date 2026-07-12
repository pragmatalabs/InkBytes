"use client";

import { useState } from "react";
import type { MediaRailItem } from "@/lib/types";
import VideoCoverflow from "@/components/video-coverflow";

// ── Streaming icon (SVG from design assets) ───────────────────────────────────

function StreamingIcon() {
  return (
    <span className="relative inline-flex flex-none items-center justify-center w-5 h-5">
      {/* Two staggered rings — subtle ambient pulse */}
      <span
        className="absolute inset-[-4px] rounded-sm animate-ping opacity-25 [animation-duration:2s]"
        style={{ background: "#6A6493" }}
      />
      <span
        className="absolute inset-[-2px] rounded-sm animate-ping opacity-15 [animation-duration:2s] [animation-delay:1s]"
        style={{ background: "#FC4442" }}
      />
      <svg className="relative w-5 h-5" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <path style={{ fill: "#FC4442" }} d="M54.364,52.952h-1.603v-2.167h1.603c1.423,0,2.582-1.158,2.582-2.582V15.796c0-1.424-1.158-2.582-2.582-2.582H9.636c-1.424,0-2.582,1.158-2.582,2.582v2.056H4.887v-2.056c0-2.618,2.131-4.749,4.749-4.749h44.728c2.618,0,4.748,2.131,4.748,4.749v32.407C59.113,50.822,56.983,52.952,54.364,52.952z"/>
        <path style={{ fill: "#FC4442" }} d="M59.251,48.065h-1.602v-2.167h1.602c1.424,0,2.582-1.158,2.582-2.582V10.909c0-1.423-1.158-2.582-2.582-2.582H14.524c-1.424,0-2.582,1.158,2.582,2.582v2.056H9.775v-2.056c0-2.618,2.131-4.748,4.749-4.748h44.727C61.869,6.16,64,8.29,64,10.909v32.407C64,45.934,61.869,48.065,59.251,48.065z"/>
        <path style={{ fill: "#6A6493" }} d="M49.893,57.84H4.333C1.944,57.84,0,55.896,0,53.507V20.268c0-2.389,1.944-4.333,4.333-4.333h45.559c2.389,0,4.333,1.944,4.333,4.333v33.239C54.226,55.896,52.282,57.84,49.893,57.84z M4.333,18.101c-1.195,0-2.167,0.972-2.167,2.167v33.239c0,1.195,0.972,2.167,2.167,2.167h45.559c1.195,0,2.167-0.972,2.167-2.167V20.268c0-1.195-0.972-2.167-2.167-2.167H4.333z"/>
        <path style={{ fill: "#6A6493" }} d="M18.56,46.137c-0.211,0-0.42-0.061-0.6-0.181c-0.301-0.201-0.483-0.54-0.483-0.902V28.721c0-0.362,0.181-0.701,0.483-0.902c0.3-0.201,0.684-0.239,1.018-0.098l19.549,8.166c0.404,0.169,0.666,0.563,0.666,1c0,0.437-0.262,0.831-0.666,1l-19.549,8.166C18.844,46.109,18.701,46.137,18.56,46.137z M19.643,30.347v13.08l15.656-6.54L19.643,30.347z"/>
      </svg>
    </span>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface Props {
  rail: MediaRailItem[];
  /** Rendered in the left slot of the action bar (e.g. ← All events link) */
  back: React.ReactNode;
  /** Rendered in the right slot of the action bar (e.g. ShareButton) */
  share: React.ReactNode;
}

export default function MediaRailDrawer({ rail, back, share }: Props) {
  const [open, setOpen] = useState(false);

  // Media rail is video-only (ADR-R-0006) — images are filtered at the
  // Curator layer and not stored.  Existing pages may have image items;
  // we skip them here so the drawer is always video-first.
  const videos = rail.filter((m) => m.type === "video");
  const hasMedia = videos.length > 0;

  return (
    <div className="mb-8">
      {/* Action bar */}
      <div className="flex items-center justify-between">
        {back}
        <div className="flex items-center gap-3">
          {hasMedia && (
            <button
              onClick={() => setOpen((o) => !o)}
              aria-expanded={open}
              aria-label={open ? "Hide videos" : "Show videos"}
              className="inline-flex items-center gap-1.5 text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors"
            >
              <StreamingIcon />
              <span className="text-[11px] font-mono tabular-nums">{videos.length}</span>
            </button>
          )}
          {share}
        </div>
      </div>

      {/* Expandable video panel — 3D coverflow (was a flat chip row) */}
      {open && hasMedia && (
        <div className="mt-4">
          <VideoCoverflow videos={videos} />
        </div>
      )}
    </div>
  );
}
