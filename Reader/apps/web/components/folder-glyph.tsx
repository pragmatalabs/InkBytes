/**
 * FolderGlyph — the "live folder" (open folder + document) from Julian's
 * reference asset (folders/SVG/live-folder.svg), re-tinted to a single theme
 * accent via `currentColor`: the source blues map to the accent (outlines) and
 * two accent tints (folder faces); the document stays white. Set `color` on a
 * parent to theme it. Faithful to the original geometry (viewBox 40×40).
 */
export default function FolderGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} role="img" aria-hidden="true">
      {/* back folder body — accent tint */}
      <path fill="currentColor" fillOpacity="0.42"
        d="M1.5 35.5L1.5 4.5 11.793 4.5 14.793 7.5 35.5 7.5 35.5 35.5z" />
      {/* back folder outline — accent */}
      <path fill="currentColor"
        d="M11.586,5l2.707,2.707L14.586,8H15h20v27H2V5H11.586 M12,4H1v32h35V7H15L12,4L12,4z" />
      {/* document sheet — white */}
      <path fill="#ffffff" d="M4.5 7.5H35.5V25.5H4.5z" />
      {/* document outline — accent */}
      <path fill="currentColor" d="M35,8v17H5V8H35 M36,7H4v19h32V7L36,7z" />
      {/* front flap — lighter accent tint */}
      <path fill="currentColor" fillOpacity="0.20"
        d="M1.599 35.5L5.417 14.5 16.151 14.5 19.151 12.5 39.41 12.5 35.577 35.5z" />
      {/* front flap outline — accent */}
      <path fill="currentColor"
        d="M38.82,13l-3.667,22H2.198l3.636-20H16h0.303l0.252-0.168L19.303,13H38.82 M40,12H19l-3,2H5L1,36 h35L40,12L40,12z" />
    </svg>
  );
}
