import Link from "next/link";
import type { Metadata } from "next";
import { getOutlook, relativeTime } from "@/lib/api";
import type { Outlook } from "@/lib/types";
import { NewsMarkdown } from "@/components/news-markdown";
import OutlookActions from "@/components/outlook-actions";

// force-dynamic: this calls the internal Curator API (ADR-R-0005 — never ISR
// pre-render an internal-hostname fetch during docker build).
export const dynamic = "force-dynamic";

const titleCase = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
// Persona keys are stored kebab-case ("el-circuito"); show the display name ("El Circuito").
const prettyPersona = (p: string) => p.split("-").map(titleCase).join(" ");

export async function generateMetadata(
  { params }: { params: Promise<{ topic: string }> },
): Promise<Metadata> {
  const { topic } = await params;
  return { title: `Today's ${titleCase(topic)} Outlook` };
}

export default async function OutlookPage({
  params, searchParams,
}: {
  params: Promise<{ topic: string }>;
  searchParams: Promise<{ lang?: string; date?: string }>;
}) {
  const { topic } = await params;
  const sp = await searchParams;
  const lang = sp.lang === "en" ? "en" : "es";
  const date = typeof sp.date === "string" ? sp.date : undefined;
  const q = (l: string, d?: string) => `?lang=${l}${d ? `&date=${d}` : ""}`;

  const data = await getOutlook(topic, lang, date);
  const o = "headline" in data ? (data as Outlook) : null;

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      <div className="flex items-center justify-between gap-3 mb-3 print:hidden">
        <Link href="/outlook" className="text-xs text-[var(--ink-muted)] hover:text-[var(--accent)]">← Outlooks</Link>
        <span className="flex items-center gap-1.5 text-[11px] font-mono text-[var(--ink-muted)]">
          <Link href={q("es", date)} className={lang === "es" ? "text-[var(--accent)] font-bold" : "hover:underline"}>ES</Link>
          <span aria-hidden>·</span>
          <Link href={q("en", date)} className={lang === "en" ? "text-[var(--accent)] font-bold" : "hover:underline"}>EN</Link>
        </span>
      </div>

      <div className="text-[11px] font-semibold uppercase tracking-widest text-[var(--accent)]">
        Today&apos;s {titleCase(topic)} Outlook
      </div>

      {o ? (
        <>
          <div className="text-[11px] text-[var(--ink-muted)] mt-1 mb-3">
            {prettyPersona(o.persona)} · <span suppressHydrationWarning>{o.edition_date}</span>
          </div>
          <h1 className="text-2xl sm:text-[2rem] font-extrabold leading-tight tracking-tight mb-4"
              style={{ textWrap: "balance" } as React.CSSProperties}>
            {o.headline}
          </h1>

          <OutlookActions headline={o.headline} bodyMd={o.body_md} theme={topic} editionDate={o.edition_date} />

          <article className="synthesis-body text-[16px] sm:text-[17px] leading-[1.8] text-[var(--ink)] mt-6 mb-10">
            <NewsMarkdown source={o.body_md} />
          </article>

          {o.timeline.length > 0 && (
            <div className="border-t border-[var(--border)] pt-7 mb-8 print:hidden">
              <h2 className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-4">
                Timeline · today&apos;s stories
              </h2>
              <ol className="space-y-3 border-l border-[var(--border)] pl-4">
                {o.timeline.map((t, i) => (
                  <li key={t.id}>
                    <Link href={`/event/${t.id}`} className="text-sm leading-snug hover:text-[var(--accent)]">
                      <span className="text-[var(--ink-muted)]">[{i + 1}]</span> {t.headline}
                    </Link>
                    <span suppressHydrationWarning className="block text-[11px] text-[var(--ink-muted)] mt-0.5">
                      {relativeTime(t.freshness_at)} · {t.source_count} {t.source_count === 1 ? "source" : "sources"}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {o.available_dates.length > 1 && (
            <div className="text-[11px] text-[var(--ink-muted)] print:hidden">
              <span className="uppercase tracking-widest mr-2">Past editions</span>
              {o.available_dates.map((d) => (
                <Link key={d} href={q(lang, d)}
                      className={`mr-2 hover:underline ${d === o.edition_date ? "text-[var(--accent)] font-semibold" : ""}`}>
                  {d}
                </Link>
              ))}
            </div>
          )}
        </>
      ) : (
        <p className="text-[var(--ink-muted)] mt-6 text-sm leading-relaxed">
          No {titleCase(topic)} outlook has been published yet. Editions are cut daily
          at 11:59 AM — check back then.
        </p>
      )}
    </div>
  );
}
