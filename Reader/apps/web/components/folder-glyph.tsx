/**
 * FolderGlyph — the folder artwork from Julian's Folder.svg (2026-07-12), just
 * the shape: open folder body + white document + front flap. The placeholder
 * "Category Name" / "200" / icon circle from the source are NOT drawn here —
 * the carousel overlays live data over the white document region instead.
 *
 * Re-tinted to one theme accent via `currentColor`: source blues → accent (borders); all faces are WHITE — a white folder
 * with category-coloured borders. Set
 * `color` on a parent to theme it. Faithful geometry (viewBox 1024×1024).
 */
export default function FolderGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="117 83 888 772" className={className} role="img" aria-hidden="true"
      preserveAspectRatio="xMidYMid meet">
      {/* back folder body — accent tint */}
      <path fill="#ffffff"
        d="M127.32,843.14V95.81h208.4l60.74,72.32h419.24v675H127.32Z" />
      {/* back folder outline — accent */}
      <path fill="currentColor"
        d="M331.52,107.87l54.81,65.26,5.93,7.06h413.31v650.89H137.44V107.87h194.08M339.91,83.76H117.19v771.43h708.62V156.08h-425.17l-60.74-72.32h0Z" />
      {/* document sheet — white */}
      <path fill="#ffffff" d="M188.06,168.14h627.64v433.93H188.06V168.14Z" />
      {/* document outline — accent */}
      <path fill="currentColor"
        d="M805.57,180.19v409.82H198.18V180.19h607.39M825.82,156.08H177.93v458.04h647.89V156.08h0Z" />
      {/* front flap — lighter accent tint */}
      <path fill="#ffffff"
        d="M130.83,843.14l86.93-506.25h244.39l68.3-48.21h461.26l-87.27,554.46H130.83Z" />
      {/* front flap outline — accent */}
      <path fill="currentColor"
        d="M978.29,300.73l-83.49,530.36H144.47l82.79-482.14h238.36l5.74-4.05,62.57-44.16h444.37M1005.16,276.62h-478.13l-68.3,48.21h-250.45l-91.07,530.36h796.89l91.07-578.57h0Z" />
    </svg>
  );
}
