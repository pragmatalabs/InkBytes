import Link from "next/link";
import type { Metadata } from "next";
import { getOutlookArchive } from "@/lib/api";
import type { OutlookArchiveEntry } from "@/lib/types";
import { ColumnMast } from "@/components/column-mast";
import SavedOutlooks from "@/components/saved-outlooks";
import NotifyToggle from "@/components/notify-toggle";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Today's Outlooks" };

const titleCase = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
const prettyPersona = (p: string) => p.split("-").map(titleCase).join(" ");

// Server-rendered only (no client hydration of these) → deterministic format is
// safe. Anchor at 12:00Z so the date never rolls back across a timezone.
const fmtDate = (d: string) =>
  new Date(`${d}T12:00:00Z`).toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", timeZone: "UTC",
  });

export default async function OutlookIndex({
  searchParams,
}: { searchParams: Promise<{ lang?: string }> }) {
  const sp = await searchParams;
  const lang = sp.lang === "en" ? "en" : "es";
  // Chrome must switch WITH the ES/EN toggle (Stage 1 fix) — the header was
  // hardcoded English while the notify button rendered Spanish. Also avoid the
  // internal scheduling phrase "cut at 11:59 AM".
  const copy = lang === "en"
    ? {
        title: "Today's Outlooks",
        sub: "A daily editorial per topic — one column per vertical. Updated each morning.",
      }
    : {
        title: "Editoriales de hoy",
        sub: "Una editorial diaria por tema — una columna por vertical. Se actualiza cada mañana.",
      };
  const { editions } = await getOutlookArchive(lang, 21);

  // Group editions by edition_date, preserving the API's newest-first order.
  const byDate: { date: string; items: OutlookArchiveEntry[] }[] = [];
  for (const e of editions) {
    const g = byDate.find((x) => x.date === e.edition_date);
    if (g) g.items.push(e);
    else byDate.push({ date: e.edition_date, items: [e] });
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      <div className="flex items-center justify-between gap-3 mb-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">{copy.title}</h1>
        <span className="flex items-center gap-1.5 text-[11px] font-mono text-[var(--ink-muted)]">
          <Link href="?lang=es" className={lang === "es" ? "text-[var(--accent)] font-bold" : "hover:underline"}>ES</Link>
          <span aria-hidden>·</span>
          <Link href="?lang=en" className={lang === "en" ? "text-[var(--accent)] font-bold" : "hover:underline"}>EN</Link>
        </span>
      </div>
      <div className="flex items-center justify-between gap-3 flex-wrap mb-8">
        <p className="text-sm text-[var(--ink-muted)]">
          {copy.sub}
        </p>
        {/* Opt-in push: "notify me when today's outlooks are ready" (PWA) */}
        <NotifyToggle lang={lang} />
      </div>

      {/* Reader's saved editions (localStorage; profile later) — self-hides when empty */}
      <SavedOutlooks />

      {byDate.length === 0 ? (
        <p className="text-[var(--ink-muted)] text-sm">No outlooks published yet — check back after the daily cut.</p>
      ) : (
        <div className="relative">
          {byDate.map(({ date, items }, di) => (
            <section key={date} className="relative pl-6 pb-8 border-l border-[var(--border)] last:border-l-transparent last:pb-0">
              {/* Timeline node */}
              <span
                className="absolute -left-[5px] top-1.5 w-[9px] h-[9px] rounded-full bg-[var(--accent)] ring-4 ring-[var(--bg,#fff)]"
                aria-hidden
              />
              <div className="flex items-baseline gap-2 mb-3 -mt-0.5">
                <h2 className="text-sm font-bold tracking-tight" suppressHydrationWarning>{fmtDate(date)}</h2>
                {di === 0 && (
                  <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--accent)] bg-[var(--accent)]/10 rounded-full px-2 py-0.5">
                    Latest
                  </span>
                )}
                <span className="text-[11px] text-[var(--ink-muted)]">
                  {items.length} {items.length === 1 ? "column" : "columns"}
                </span>
              </div>

              {/* Latest day: 2-col grid of persona cards (theme accents doing the
                  identity work); older days: the same cards, denser. */}
              <div className={`grid gap-2.5 ${di === 0 ? "sm:grid-cols-2" : ""}`}>
                {items.map((t) => (
                  <Link
                    key={`${date}-${t.theme}`}
                    href={`/outlook/${t.theme}?lang=${lang}&date=${date}`}
                    className="block bg-white border border-[var(--border)] rounded-xl p-4 hover:shadow-md hover:border-gray-300 transition-all"
                  >
                    <div className="mb-1.5">
                      <ColumnMast persona={t.persona} theme={t.theme} />
                    </div>
                    <div
                      className="text-[14px] font-bold leading-snug line-clamp-2"
                      style={{ textWrap: "balance" } as React.CSSProperties}
                    >
                      {t.headline}
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
