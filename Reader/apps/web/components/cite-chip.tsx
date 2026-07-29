"use client";

/**
 * CiteChip — the inline `Source: X` citation chip inside a synthesis body.
 *
 * Tapping it opens the event page's Evidence drawer focused on the cited source
 * (dispatches inkb:open-sheet; StoryNav listens). Adapts the prototype's
 * tappable citation-superscript idea to InkBytes' named-source chips.
 */
export default function CiteChip({ label }: { label: string }) {
  // label is e.g. "Source: El Colombiano" / "Fuente: El País"
  const source = label.replace(/^(?:Source|Fuente):\s*/i, "").trim();
  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        window.dispatchEvent(
          new CustomEvent("inkb:open-sheet", { detail: { sheet: "evidence", source } }),
        );
      }}
      className="not-italic inline-flex items-center align-middle mx-0.5 rounded bg-gray-100 px-1.5 py-px font-mono text-[10px] font-medium leading-none text-[var(--ink-muted)] cursor-pointer hover:bg-[var(--accent)] hover:text-white transition-colors"
    >
      {label}
    </button>
  );
}
