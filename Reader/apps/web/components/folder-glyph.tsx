"use client";

import { useId } from "react";

/**
 * FolderGlyph — the definitive closed folder from Julian's folder-definitive.svg
 * (2026-07-12): back + tab, front body. White faces with a category-coloured
 * border (source greys → white fills; strokes → `currentColor` = the accent),
 * plus a soft accent sheen inside the front face dimming in from the top-right.
 * Set `color` on a parent to theme it. Faithful geometry (viewBox 512×400);
 * the carousel overlays the icon / count / name on the front body.
 */
export default function FolderGlyph({ className }: { className?: string }) {
  // Unique per instance so each folder's currentColor resolves its own accent
  // (duplicate gradient ids across SVGs would all bind to the first one).
  const gid = useId().replace(/:/g, "");
  const FRONT = "M62.22,81.21h380.72c27.66,0,50.09,19.47,50.09,43.48v226.1c0,24.01-22.43,43.48-50.09,43.48H62.22c-27.66,0-50.09-19.47-50.09-43.48V124.69c0-24.01,22.43-43.48,50.09-43.48Z";
  return (
    <svg viewBox="0 0 512 400" className={className} role="img" aria-hidden="true"
      preserveAspectRatio="xMidYMid meet">
      <defs>
        {/* soft accent sheen, dimmed, from the top-right corner */}
        <radialGradient id={gid} cx="1" cy="0" r="1.15">
          <stop offset="0" stopColor="currentColor" stopOpacity="0.15" />
          <stop offset="0.6" stopColor="currentColor" stopOpacity="0" />
        </radialGradient>
      </defs>
      {/* back + tab — white face, accent border */}
      <path
        d="M188.19,40.38h0c0-19.77-17.52-35.81-39.12-35.81H51.26C29.65,4.58,12.13,20.61,12.13,40.38v304.36c0,24.72,21.9,44.76,48.91,44.76h371.68c27.01,0,48.91-20.04,48.91-44.76V112c0-24.72-21.9-44.76-48.91-44.76h-215.19c-16.21,0-29.34-12.02-29.34-26.86Z"
        fill="#ffffff" stroke="currentColor" strokeWidth="6" strokeLinejoin="round" />
      {/* front body — lower layer, a hair of grey for the folded edge */}
      <path
        d="M62.22,76.44h380.72c27.66,0,50.09,19.47,50.09,43.48v226.1c0,24.01-22.43,43.48-50.09,43.48H62.22c-27.66,0-50.09-19.47-50.09-43.48V119.92c0-24.01,22.43-43.48,50.09-43.48Z"
        fill="#eeeeec" />
      {/* front body — top layer, white face, accent border */}
      <path d={FRONT} fill="#ffffff" stroke="currentColor" strokeWidth="6" strokeLinejoin="round" />
      {/* front body — accent sheen (dimmed, top-right), clipped to the front shape */}
      <path d={FRONT} fill={`url(#${gid})`} />
    </svg>
  );
}
