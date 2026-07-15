import Link from "next/link";
import type { Metadata } from "next";
import { getOutlook, getOutlookAvailable, relativeTime } from "@/lib/api";
import type { Outlook, OutlookTopic } from "@/lib/types";
import { NewsMarkdown } from "@/components/news-markdown";
import OutlookActions from "@/components/outlook-actions";
import OutlookAudio from "@/components/outlook-audio";
import OutlookSave from "@/components/outlook-save";
import { themeAccent } from "@/lib/theme-colors";
import { PersonaIcon } from "@/components/persona-icons";

// force-dynamic: this calls the internal Curator API (ADR-R-0005 — never ISR
// pre-render an internal-hostname fetch during docker build).
export const dynamic = "force-dynamic";

const titleCase = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
// Persona keys are stored kebab-case ("el-circuito"); show the display name ("El Circuito").
const prettyPersona = (p: string) => p.split("-").map(titleCase).join(" ");

// Human dates, localized to the column's language. Anchor at 12:00Z so the
// date never rolls back across a timezone (same trick as the index).
const longDate = (d: string, lang: string) =>
  new Date(`${d}T12:00:00Z`).toLocaleDateString(lang === "es" ? "es-ES" : "en-US", {
    month: "long", day: "numeric", year: "numeric", timeZone: "UTC",
  });
const chipDate = (d: string, lang: string) =>
  new Date(`${d}T12:00:00Z`).toLocaleDateString(lang === "es" ? "es-ES" : "en-US", {
    weekday: "short", day: "numeric", timeZone: "UTC",
  });

const readMinutes = (md: string) => Math.max(1, Math.round(md.split(/\s+/).length / 200));

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

  // "More outlooks today" is best-effort — its failure must not blank the column.
  const [data, available] = await Promise.all([
    getOutlook(topic, lang, date),
    getOutlookAvailable(lang).catch(() => ({ topics: [] as OutlookTopic[] })),
  ]);
  const o = "headline" in data ? (data as Outlook) : null;
  const accent = themeAccent(topic);
  const others = available.topics.filter((t) => t.theme !== topic);

  // The editorial's [n] citations → linkify each against the timeline (same [n]
  // order, per the /outlook contract) so a citation is a tappable superscript.
  // The LLM often wraps them in backticks (`[2]`), which would render as a code
  // span (and any injected link stays literal) — so the regex SWALLOWS optional
  // surrounding backticks and emits a clean markdown link (fixes ADR-0010's
  // backtick-wrapped citations without regenerating; the prompt also stopped
  // instructing backticks going forward).
  const bodyMd = o
    ? o.body_md.replace(/`?\[(\d{1,2})\]`?/g, (_m, n) => {
        const t = o.timeline[Number(n) - 1];
        return t ? `[${n}](/event/${t.id})` : `[${n}]`;
      })
    : "";

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      {/* ── Utility row — quiet, single line ────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 mb-6 print:hidden">
        <Link href="/outlook" className="text-xs text-[var(--ink-muted)] hover:text-[var(--accent)]">← Outlooks</Link>
        <span className="inline-flex items-center p-0.5 bg-gray-100 rounded-full gap-0.5" role="group" aria-label="Language">
          {(["es", "en"] as const).map((l) => (
            <Link key={l} href={q(l, date)} aria-current={lang === l}
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase transition-colors ${
                lang === l ? "bg-white text-[var(--ink)] shadow-sm" : "text-[var(--ink-muted)] hover:text-[var(--ink)]"
              }`}>
              {l}
            </Link>
          ))}
        </span>
      </div>

      {o ? (
        <>
          {/* ── Masthead — the persona is the product ───────────────────── */}
          <div className="flex items-center gap-3">
            <span
              className="grid place-items-center w-11 h-11 rounded-full text-white shrink-0"
              style={{ background: accent }}
              aria-hidden
            >
              <PersonaIcon persona={o.persona} className="w-6 h-6" />
            </span>
            <div className="min-w-0">
              <div className="text-[13px] font-bold uppercase tracking-[0.14em]" style={{ color: accent }}>
                {prettyPersona(o.persona)}
              </div>
              <div className="text-[12px] text-[var(--ink-muted)] mt-0.5" suppressHydrationWarning>
                {titleCase(topic)} · {longDate(o.edition_date, lang)} · {readMinutes(o.body_md)} min
              </div>
            </div>
          </div>
          <div className="h-[2px] w-14 my-5" style={{ background: accent }} aria-hidden />

          {/* ── Edition strip (context selection lives with the masthead) ── */}
          {o.available_dates.length > 1 && (
            <div className="-mx-4 px-4 mb-5 overflow-x-auto scrollbar-hide print:hidden">
              <div className="flex items-center gap-1.5 flex-nowrap">
                {o.available_dates.slice(0, 14).map((d) => {
                  const active = d === o.edition_date;
                  return (
                    <Link key={d} href={q(lang, d)} aria-current={active}
                      suppressHydrationWarning
                      className={`px-2.5 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap border transition-colors ${
                        active ? "text-white" : "bg-white border-[var(--border)] text-[var(--ink-muted)] hover:border-gray-400"
                      }`}
                      style={active ? { background: accent, borderColor: accent } : undefined}>
                      {chipDate(d, lang)}
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── The one loud thing ──────────────────────────────────────── */}
          <h1 className="text-[2rem] sm:text-[2.5rem] font-extrabold leading-[1.12] tracking-tight mb-6"
              style={{ textWrap: "balance" } as React.CSSProperties}>
            {o.headline}
          </h1>

          {/* ── Listen — spoken-word column (self-hosted TTS, ADR-0011) ──── */}
          {o.audio_url && (
            <div className="mb-7 max-w-[64ch]">
              <OutlookAudio src={o.audio_url} lang={lang} accent={accent} />
            </div>
          )}

          {/* ── Column body — 65ch measure, superscript citations ───────── */}
          <article
            className="outlook-prose outlook-body synthesis-body max-w-[64ch] mb-9"
            style={{ "--outlook-accent": accent } as React.CSSProperties}
          >
            <NewsMarkdown source={bodyMd} />
          </article>

          {/* ── Actions — after reading: Save (localStorage) + share/export ── */}
          <div className="mb-10 print:hidden flex flex-wrap items-center gap-2">
            <OutlookSave theme={topic} lang={lang} date={o.edition_date}
              headline={o.headline} persona={prettyPersona(o.persona)} />
            <OutlookActions headline={o.headline} bodyMd={o.body_md} theme={topic} editionDate={o.edition_date} />
          </div>

          {/* ── Timeline — numbered rail matching the [n] citations ─────── */}
          {o.timeline.length > 0 && (
            <div className="border-t border-[var(--border)] pt-7 mb-10 print:hidden">
              <h2 className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-5">
                {lang === "es" ? "Las historias de hoy" : "Today's stories"}
              </h2>
              <ol className="relative space-y-5">
                <span className="absolute left-[11px] top-1 bottom-1 w-px bg-[var(--border)]" aria-hidden />
                {o.timeline.map((t, i) => (
                  <li key={t.id} className="relative pl-9">
                    <span
                      className="absolute left-0 top-0 grid place-items-center w-[23px] h-[23px] rounded-full bg-white border text-[10px] font-bold tabular-nums"
                      style={{ borderColor: accent, color: accent }}
                      aria-hidden
                    >
                      {i + 1}
                    </span>
                    <Link href={`/event/${t.id}`} className="group block">
                      <span className="text-[14px] font-medium leading-snug group-hover:text-[var(--accent)] transition-colors">
                        {t.headline}
                      </span>
                      <span suppressHydrationWarning className="block text-[11px] text-[var(--ink-muted)] mt-0.5">
                        {relativeTime(t.freshness_at)} · {t.source_count} {t.source_count === 1 ? "source" : "sources"}
                      </span>
                    </Link>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* ── More outlooks today — the continuous morning read ────────── */}
          {others.length > 0 && (
            <div className="border-t border-[var(--border)] pt-7 print:hidden">
              <h2 className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-4">
                {lang === "es" ? "Más columnas de hoy" : "More outlooks today"}
              </h2>
              <div className="-mx-4 px-4 overflow-x-auto scrollbar-hide">
                <div className="flex gap-2.5 snap-x snap-mandatory pb-1">
                  {others.map((t) => {
                    const a = themeAccent(t.theme);
                    return (
                      <Link
                        key={t.theme}
                        href={`/outlook/${t.theme}?lang=${lang}`}
                        className="snap-start shrink-0 w-[200px] rounded-xl border border-[var(--border)] bg-white p-3.5 hover:shadow-md hover:border-gray-300 transition-all"
                      >
                        <span className="flex items-center gap-2 mb-2">
                          <span className="grid place-items-center w-7 h-7 rounded-full text-white shrink-0"
                            style={{ background: a }} aria-hidden>
                            <PersonaIcon persona={t.persona} className="w-4 h-4" />
                          </span>
                          <span className="min-w-0">
                            <span className="block text-[10px] font-bold uppercase tracking-wider truncate" style={{ color: a }}>
                              {prettyPersona(t.persona)}
                            </span>
                            <span className="block text-[9px] uppercase tracking-wider text-[var(--ink-muted)]">
                              {titleCase(t.theme)}
                            </span>
                          </span>
                        </span>
                        <span className="block text-[12.5px] font-semibold leading-snug line-clamp-2">
                          {t.headline}
                        </span>
                      </Link>
                    );
                  })}
                </div>
              </div>
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
