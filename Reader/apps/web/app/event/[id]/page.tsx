import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { getEvent, getRelatedEvents, relativeTime, parseJson, isDeveloping, outletInitials } from "@/lib/api";
import type { EvidenceItem, EntityItem, RelatedEvent } from "@/lib/types";

export const revalidate = 300;

const ENTITY_COLORS: Record<string, string> = {
  PERSON: "bg-blue-50 text-blue-700 border-blue-200",
  ORG:    "bg-purple-50 text-purple-700 border-purple-200",
  LOC:    "bg-emerald-50 text-emerald-700 border-emerald-200",
  EVENT:  "bg-orange-50 text-orange-700 border-orange-200",
  OTHER:  "bg-gray-50 text-gray-600 border-gray-200",
};

/** First sentence of synthesis — used for OG description. */
function firstSentence(text: string): string {
  const match = text.replace(/\[(?:Source|Fuente): [^\]]+\]/g, "").match(/[^.!?]+[.!?]/);
  return match ? match[0].trim() : text.slice(0, 160);
}

export async function generateMetadata(
  { params }: { params: Promise<{ id: string }> }
): Promise<Metadata> {
  const { id } = await params;
  try {
    const page = await getEvent(id);
    const description = firstSentence(page.synthesis_md);
    const ogImages = page.lead_image
      ? [{ url: page.lead_image, alt: page.headline }]
      : [];
    return {
      title: page.headline,
      description,
      openGraph: {
        title: page.headline,
        description,
        type: "article",
        publishedTime: page.published_at,
        modifiedTime: page.freshness_at,
        section: page.topic ?? "News",
        images: ogImages,
      },
      twitter: {
        card: page.lead_image ? "summary_large_image" : "summary",
        title: page.headline,
        description,
        images: page.lead_image ? [page.lead_image] : [],
      },
    };
  } catch {
    return { title: "Event" };
  }
}

/** Split synthesis text by citation markers for inline highlighting. */
function renderSynthesis(text: string) {
  const paragraphs = text.trim().split(/\n\n+/);
  return paragraphs.map((para, i) => {
    const parts = para.split(/(\[(?:Source|Fuente): [^\]]+\])/g);
    return (
      <p key={i} className="mb-5 last:mb-0">
        {parts.map((part, j) =>
          /^\[(?:Source|Fuente):/.test(part) ? (
            <span
              key={j}
              className="inline-block text-[10px] font-mono font-medium text-[var(--ink-muted)] bg-gray-100 rounded px-1 py-px mx-0.5 align-middle leading-none"
            >
              {part.replace(/^\[|\]$/g, "")}
            </span>
          ) : (
            part
          )
        )}
      </p>
    );
  });
}

export default async function EventPage(
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  let page;
  try {
    page = await getEvent(id);
  } catch {
    notFound();
  }

  const evidence = parseJson<EvidenceItem[]>(page.evidence_rail);
  const entities = parseJson<EntityItem[]>(page.entities);
  // Note: isDeveloping uses Date.now() — server value may differ from client.
  // The Developing badge element has suppressHydrationWarning to prevent #418.
  const developing = isDeveloping(page.freshness_at);

  // Fetch related events in parallel — silent failure (empty list) if unavailable.
  let related: RelatedEvent[] = [];
  try {
    related = await getRelatedEvents(id);
  } catch {
    // non-fatal: the event page renders fine without related events
  }

  // Outlet-initials avatar stack, de-duped, built from the evidence source names.
  const outletNames = Array.from(new Set(evidence.map((e) => e.source_name))).slice(0, 6);

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      {/* Back */}
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-xs text-[var(--ink-muted)] hover:text-[var(--ink)] mb-8 transition-colors"
      >
        ← All events
      </Link>

      {/* Hero cover image — rendered only when Messor extracted an og:image */}
      {page.lead_image && (
        <div className="w-full rounded-xl overflow-hidden mb-8 bg-gray-100 aspect-video">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={page.lead_image}
            alt={page.headline}
            className="w-full h-full object-cover"
            loading="eager"
          />
        </div>
      )}

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-2 mb-4 text-xs text-[var(--ink-muted)]">
        {page.topic && (
          <span className="px-2 py-0.5 rounded-full bg-gray-100 font-medium text-gray-700">
            {page.topic}
          </span>
        )}
        <span className="flex items-center gap-1">
          <svg className="w-3 h-3 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
          </svg>
          {page.source_count} {page.source_count === 1 ? "source" : "sources"}
        </span>
        <span>·</span>
        {/* suppressHydrationWarning: relativeTime uses Date.now() — differs
            between server (UTC) and client (local tz), causing error #418. */}
        <span suppressHydrationWarning>Updated {relativeTime(page.freshness_at)}</span>
        {developing && (
          <span suppressHydrationWarning className="inline-flex items-center gap-1.5 font-semibold uppercase tracking-wide text-[10px] text-red-600">
            <span className="developing-dot" aria-hidden="true" />
            Developing
          </span>
        )}
        {page.language !== "en" && (
          <span className="font-mono px-1.5 py-0.5 rounded bg-gray-100 uppercase text-[10px] tracking-wide">
            {page.language}
          </span>
        )}
      </div>

      {/* Headline */}
      <h1 className="text-[1.6rem] sm:text-[1.75rem] md:text-3xl font-bold leading-tight tracking-tight mb-7">
        {page.headline}
      </h1>

      {/* Entity chips */}
      {entities.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-8">
          {entities.map((e, i) => (
            <span
              key={i}
              className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border ${ENTITY_COLORS[e.type] ?? ENTITY_COLORS.OTHER}`}
            >
              {e.type && (
                <span className="font-mono text-[9px] opacity-50 uppercase">{e.type}</span>
              )}
              {e.name}
            </span>
          ))}
        </div>
      )}

      {/* Stat cards: Sources (+ outlet avatar stack) and Coverage. Factuality deferred. */}
      <div className="grid grid-cols-2 gap-px bg-[var(--border)] border border-[var(--border)] rounded-lg overflow-hidden mb-10">
        <div className="bg-white p-4 sm:p-5">
          <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-[var(--ink-muted)]">
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
            </svg>
            Sources
          </div>
          <div className="mt-2.5 flex items-baseline gap-1.5">
            <span className="text-2xl sm:text-3xl font-extrabold tracking-tight leading-none">{page.source_count}</span>
            <span className="text-xs font-medium text-[var(--ink-muted)]">outlets</span>
          </div>
          {outletNames.length > 0 && (
            <div className="mt-3 flex items-center">
              {outletNames.map((name, i) => (
                <span
                  key={i}
                  title={name}
                  className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-[var(--accent)] text-white text-[9px] font-bold uppercase ring-2 ring-white"
                  style={{ marginLeft: i === 0 ? 0 : -6, zIndex: outletNames.length - i }}
                >
                  {outletInitials(name)}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="bg-white p-4 sm:p-5">
          <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-[var(--ink-muted)]">
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>
            </svg>
            Coverage
          </div>
          <div className="mt-2.5 flex items-baseline gap-1.5">
            <span className="text-2xl sm:text-3xl font-extrabold tracking-tight leading-none">{page.article_count}</span>
            <span className="text-xs font-medium text-[var(--ink-muted)]">
              {page.article_count === 1 ? "article" : "articles"}
            </span>
          </div>
        </div>
      </div>

      {/* Synthesis */}
      <div className="synthesis-body text-[16px] sm:text-[17px] leading-[1.8] text-[var(--ink)] mb-10">
        {renderSynthesis(page.synthesis_md)}
      </div>

      {/* Evidence rail */}
      {evidence.length > 0 && (
        <div className="border-t border-[var(--border)] pt-7">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)]">
              Sources
            </h2>
            <span className="text-[10px] text-[var(--ink-muted)]">
              {evidence.length} {evidence.length === 1 ? "quote" : "quotes"}
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {evidence.map((item, i) => (
              <a
                key={i}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block border border-[var(--border)] rounded-lg p-4 hover:border-[var(--accent)] hover:shadow-sm transition-all bg-white group"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-semibold text-[var(--accent)]">
                    {item.source_name}
                  </span>
                  <span className="text-[10px] text-[var(--ink-muted)] group-hover:text-[var(--accent)] transition-colors">↗</span>
                </div>
                <blockquote className="text-[13px] text-[var(--ink-muted)] leading-relaxed italic">
                  &ldquo;{item.quote}&rdquo;
                </blockquote>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Related events strip — entity + topic overlap (ADR-0005 Approach A) */}
      {related.length > 0 && (
        <div className="border-t border-[var(--border)] pt-7">
          <h2 className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-4">
            Related events
          </h2>
          <div className="flex flex-col gap-2">
            {related.map((ev) => (
              <Link
                key={ev.id}
                href={`/event/${ev.id}`}
                className="group flex items-start justify-between gap-4 rounded-lg border border-[var(--border)] bg-white px-4 py-3 hover:border-gray-300 hover:shadow-sm transition-all"
              >
                <div className="min-w-0">
                  {ev.topic && (
                    <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] block mb-1">
                      {ev.topic}
                    </span>
                  )}
                  <p className="text-[14px] font-medium leading-snug tracking-tight group-hover:text-[var(--accent)] transition-colors line-clamp-2">
                    {ev.headline}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5 text-[11px] text-[var(--ink-muted)]">
                    {/* Outlet initials */}
                    <span className="flex items-center gap-0.5">
                      {(ev.outlet_names ?? []).slice(0, 3).map((name) => (
                        <span
                          key={name}
                          title={name}
                          className="inline-flex items-center justify-center rounded-full bg-[var(--accent)] text-white"
                          style={{ width: 16, height: 16, fontSize: 6, fontWeight: 700 }}
                        >
                          {outletInitials(name)}
                        </span>
                      ))}
                    </span>
                    <span>{ev.source_count} {ev.source_count === 1 ? "source" : "sources"}</span>
                    <span>·</span>
                    <span suppressHydrationWarning>{relativeTime(ev.freshness_at)}</span>
                    {ev.language !== "en" && (
                      <span className="font-mono uppercase px-1 py-0.5 rounded bg-gray-100 text-gray-500 text-[9px]">
                        {ev.language}
                      </span>
                    )}
                  </div>
                </div>
                {/* Similarity score badge */}
                <span
                  className="shrink-0 mt-0.5 text-[10px] font-semibold tabular-nums px-1.5 py-0.5 rounded-full bg-gray-100 text-[var(--ink-muted)]"
                  title={`Similarity score: ${ev.score}`}
                >
                  {Math.round(ev.score * 100)}%
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
