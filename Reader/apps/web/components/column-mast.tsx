import { themeAccent } from "@/lib/theme-colors";
import { PersonaIcon } from "@/components/persona-icons";

// Shared helpers for Outlook column identity (were duplicated in outlook/page.tsx,
// the feed's OutlookCard, and saved-outlooks.tsx).
export const titleCase = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
export const prettyPersona = (p: string) =>
  p.split("-").map(titleCase).join(" ");

/**
 * ColumnMast — the Outlook column's identity: a theme-accent disc with the
 * persona glyph, the persona name, and a vertical/sublabel. One component so the
 * /outlook index card, the feed's "Today's Outlook" card, and (later) Saved all
 * render the column the same way (2026-07 mobile brief, Stage 4 item 1).
 */
export function ColumnMast({
  persona,
  theme,
  sublabel,
  discPx = 28,
  iconClass = "w-4 h-4",
}: {
  persona: string;
  theme: string;
  /** Muted second line. Defaults to the title-cased theme (the "vertical"). */
  sublabel?: string;
  discPx?: number;
  iconClass?: string;
}) {
  const accent = themeAccent(theme);
  return (
    <span className="flex items-center gap-2 min-w-0">
      <span
        className="grid place-items-center rounded-full text-white shrink-0"
        style={{ background: accent, width: discPx, height: discPx }}
        aria-hidden
      >
        <PersonaIcon persona={persona} className={iconClass} />
      </span>
      <span className="min-w-0">
        <span
          className="block text-[10px] font-bold uppercase tracking-wider truncate"
          style={{ color: accent }}
        >
          {prettyPersona(persona)}
        </span>
        <span className="block text-[9px] uppercase tracking-wider text-[var(--ink-muted)] truncate">
          {sublabel ?? titleCase(theme)}
        </span>
      </span>
    </span>
  );
}
