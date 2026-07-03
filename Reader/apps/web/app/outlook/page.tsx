import Link from "next/link";
import type { Metadata } from "next";
import { getOutlookAvailable } from "@/lib/api";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Today's Outlooks" };

const titleCase = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

export default async function OutlookIndex({
  searchParams,
}: { searchParams: Promise<{ lang?: string }> }) {
  const sp = await searchParams;
  const lang = sp.lang === "en" ? "en" : "es";
  const { topics } = await getOutlookAvailable(lang);

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      <div className="flex items-center justify-between gap-3 mb-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Today&apos;s Outlooks</h1>
        <span className="flex items-center gap-1.5 text-[11px] font-mono text-[var(--ink-muted)]">
          <Link href="?lang=es" className={lang === "es" ? "text-[var(--accent)] font-bold" : "hover:underline"}>ES</Link>
          <span aria-hidden>·</span>
          <Link href="?lang=en" className={lang === "en" ? "text-[var(--accent)] font-bold" : "hover:underline"}>EN</Link>
        </span>
      </div>
      <p className="text-sm text-[var(--ink-muted)] mb-6">
        A daily editorial per topic — one column per vertical, cut at 11:59 AM.
      </p>

      {topics.length === 0 ? (
        <p className="text-[var(--ink-muted)] text-sm">No outlooks published yet — check back after the daily cut.</p>
      ) : (
        <div className="grid gap-3">
          {topics.map((t) => (
            <Link key={t.theme} href={`/outlook/${t.theme}?lang=${lang}`}
                  className="block bg-white border border-[var(--border)] rounded-xl p-5 hover:shadow-md hover:border-gray-300 transition-all">
              <div className="text-[10px] font-semibold uppercase tracking-widest text-[var(--accent)]">
                Today&apos;s {titleCase(t.theme)} Outlook
              </div>
              <div className="text-[11px] text-[var(--ink-muted)] mt-0.5">
                {t.persona} · <span suppressHydrationWarning>{t.edition_date}</span>
              </div>
              <div className="text-[15px] font-bold leading-snug mt-2 line-clamp-2"
                   style={{ textWrap: "balance" } as React.CSSProperties}>
                {t.headline}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
