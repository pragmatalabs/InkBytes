/**
 * Per-theme accent colors — the single source for "identity" hues across the
 * Outlook column system (masthead monogram, rule, citations, timeline dots,
 * index cards). Same family as CAT_STYLES / the topic-carousel gradients
 * (tailwind 600-level), one flat hex per theme so server components can inline
 * them without Tailwind class gymnastics.
 */
export const THEME_ACCENT: Record<string, string> = {
  politics:      "#dc2626",
  business:      "#2563eb",
  technology:    "#7c3aed",
  sports:        "#16a34a",
  health:        "#db2777",
  environment:   "#059669",
  culture:       "#d97706",
  world:         "#475569",
  science:       "#0891b2",
  entertainment: "#c026d3",
  crime:         "#334155",
  education:     "#4f46e5",
  lifestyle:     "#0d9488",
  religion:      "#ca8a04",
  disaster:      "#ea580c",
};

export function themeAccent(theme?: string | null): string {
  return THEME_ACCENT[theme ?? ""] ?? "#1a1a2e";
}

/** "el-circuito" → "EC" — monogram initials from a kebab-case persona key. */
export function personaInitials(persona: string): string {
  return persona
    .split("-")
    .slice(0, 2)
    .map((w) => w.charAt(0).toUpperCase())
    .join("");
}
