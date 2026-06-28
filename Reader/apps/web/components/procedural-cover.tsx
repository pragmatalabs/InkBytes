import { CategoryIcon } from "@/components/icons";

/**
 * ADR-0034 Tier 1 — owned procedural event cover. Replaces the source outlet's
 * og:image (legal risk L3 / mitigation M1) with a deterministic, on-brand visual:
 * a theme-colored gradient + seeded soft blobs (unique per event) + the category
 * glyph. No stored asset, no external call, zero licensing, never misleading.
 *
 * Pure/deterministic (seed = event id) so the same story always looks the same.
 * No hooks → usable from both server and client components.
 */

// Per-theme [from, to] gradient hexes, aligned with the 15-theme palette
// (CAT_STYLES in feed-client.tsx). Mid + dark shade of each family.
const THEME_HEX: Record<string, [string, string]> = {
  politics:      ["#dc2626", "#7f1d1d"],
  business:      ["#2563eb", "#1e3a8a"],
  technology:    ["#7c3aed", "#4c1d95"],
  sports:        ["#16a34a", "#14532d"],
  health:        ["#db2777", "#831843"],
  environment:   ["#059669", "#064e3b"],
  culture:       ["#d97706", "#78350f"],
  world:         ["#475569", "#1e293b"],
  science:       ["#0891b2", "#164e63"],
  entertainment: ["#c026d3", "#701a75"],
  crime:         ["#334155", "#0f172a"],
  education:     ["#4f46e5", "#312e81"],
  lifestyle:     ["#0d9488", "#134e4a"],
  religion:      ["#ca8a04", "#713f12"],
  disaster:      ["#ea580c", "#7c2d12"],
};
const DEFAULT_HEX: [string, string] = ["#1a1a2e", "#0f0f1e"]; // brand navy

// Deterministic 0..1 PRNG from a string seed (LCG).
function seededRandom(seed: string): () => number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < seed.length; i++) h = Math.imul(h ^ seed.charCodeAt(i), 16777619) >>> 0;
  return () => { h = (Math.imul(h, 1103515245) + 12345) >>> 0; return h / 4294967296; };
}

export default function ProceduralCover({
  id, category, className = "",
}: { id: string; category?: string | null; className?: string }) {
  const cat = (category ?? "world").toLowerCase();
  const [c1, c2] = THEME_HEX[cat] ?? DEFAULT_HEX;
  const rnd = seededRandom(id);
  const blobs = Array.from({ length: 3 }, () => ({
    cx: 8 + rnd() * 84,
    cy: 8 + rnd() * 84,
    r: 18 + rnd() * 34,
    o: 0.08 + rnd() * 0.16,
  }));
  const gid = `pc-${id}`;
  return (
    <div className={`relative overflow-hidden ${className}`} aria-hidden="true">
      <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice"
           className="absolute inset-0 w-full h-full">
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={c1} />
            <stop offset="100%" stopColor={c2} />
          </linearGradient>
        </defs>
        <rect width="100" height="100" fill={`url(#${gid})`} />
        {blobs.map((b, i) => (
          <circle key={i} cx={b.cx} cy={b.cy} r={b.r} fill="#ffffff" opacity={b.o} />
        ))}
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <CategoryIcon category={cat} className="w-1/4 h-1/4 text-white/30" />
      </div>
    </div>
  );
}
