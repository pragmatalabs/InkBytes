"use client";

import { relativeTime, outletInitials } from "@/lib/api";
import { useLang } from "@/lib/prefs";
import { t } from "@/lib/i18n";

/**
 * Client chrome for the (server-rendered) event page — the eyebrow, provenance
 * row, and cover caption. Split out so their labels localize via `useLang()`
 * (fill-after-mount) without turning the whole event page dynamic. All
 * data-derived values are computed server-side and passed as props; only the
 * chrome *labels* switch language. Time-relative + developing bits keep
 * `suppressHydrationWarning` (server UTC vs client tz / Date.now()).
 */
const OUTLET_COLORS = ["#1a1a2e", "#2d5282", "#276749", "#7b341e", "#553c9a", "#97266d", "#2c5f62", "#744210"];
function outletColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
  return OUTLET_COLORS[Math.abs(h) % OUTLET_COLORS.length];
}
type CorrKey = "corr_strong" | "corr_moderate" | "corr_limited";
function corroboration(n: number): { key: CorrKey; color: string } {
  return n >= 5 ? { key: "corr_strong", color: "#16a34a" }
    : n >= 3 ? { key: "corr_moderate", color: "#d97706" }
    : { key: "corr_limited", color: "#9ca3af" };
}
function shortAgo(iso: string): string {
  return relativeTime(iso).replace(/\s*ago$/i, "").toUpperCase();
}

/** ● Developing (left) · CATEGORY (right). Category is a taxonomy key — not localized. */
export function EventEyebrow({ developing, category }: { developing: boolean; category: string }) {
  const lang = useLang();
  return (
    <div className="flex items-center gap-2 mb-3">
      {developing && (
        <span suppressHydrationWarning className="inline-flex items-center gap-1.5">
          <span className="developing-dot" aria-hidden="true" />
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-red-600">{t(lang, "developing")}</span>
        </span>
      )}
      {category && (
        <span className="ml-auto font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--ink-muted)]">
          {category}
        </span>
      )}
    </div>
  );
}

/** Avatars + sources·quotes + corroboration strength + STARTED/UPDATED clock. */
export function EventProvenance({
  sourceCount,
  quotes,
  outletNames,
  occurredAt,
  freshnessAt,
}: {
  sourceCount: number;
  quotes: number;
  outletNames: string[];
  occurredAt?: string | null;
  freshnessAt: string;
}) {
  const lang = useLang();
  const corrob = corroboration(sourceCount);
  return (
    <div className="flex items-center gap-3 mt-4 mb-8 py-3 border-t border-b border-[var(--border)]">
      {outletNames.length > 0 && (
        <span className="flex items-center shrink-0">
          {outletNames.slice(0, 3).map((name, i) => (
            <span
              key={i}
              title={name}
              className="inline-flex items-center justify-center w-5 h-5 rounded-full text-white text-[7.5px] font-bold uppercase ring-2 ring-[var(--bg)]"
              style={{ background: outletColor(name), marginLeft: i === 0 ? 0 : -6, zIndex: 3 - i }}
            >
              {outletInitials(name)}
            </span>
          ))}
          {sourceCount > 3 && (
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-gray-200 text-gray-600 text-[7.5px] font-bold ring-2 ring-[var(--bg)]" style={{ marginLeft: -6 }}>
              +{sourceCount - 3}
            </span>
          )}
        </span>
      )}
      <div className="leading-[1.35] min-w-0">
        <div className="text-[12px] font-semibold text-[var(--ink)] tabular-nums">
          {sourceCount} {t(lang, sourceCount === 1 ? "source_one" : "source_many")}
          {quotes > 0 && ` · ${quotes} ${t(lang, quotes === 1 ? "quote_one" : "quote_many")}`}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: corrob.color }} aria-hidden />
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: corrob.color }}>
            {t(lang, corrob.key)} · {sourceCount} {t(lang, "of")} {sourceCount}
          </span>
        </div>
        <div suppressHydrationWarning className="font-mono text-[10.5px] text-[var(--ink-muted)] mt-0.5 uppercase tracking-[0.02em]">
          {occurredAt && <>{t(lang, "started")} {shortAgo(occurredAt)} · </>}{t(lang, "updated")} {shortAgo(freshnessAt)}
        </div>
      </div>
    </div>
  );
}

/** "Illustrative. Not a photograph of this event." under the owned cover. */
export function CoverCaption() {
  const lang = useLang();
  return (
    <figcaption className="mt-2 text-center text-[11px] text-[var(--ink-muted)] italic">
      {t(lang, "cover_caption")}
    </figcaption>
  );
}
