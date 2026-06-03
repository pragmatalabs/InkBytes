import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { getEvent, relativeTime, parseJson } from "@/lib/api";
import type { EvidenceItem, EntityItem } from "@/lib/types";

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
    return {
      title: page.headline,
      description,
      openGraph: { title: page.headline, description, type: "article" },
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

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      {/* Back */}
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-xs text-[var(--ink-muted)] hover:text-[var(--ink)] mb-8 transition-colors"
      >
        ← All events
      </Link>

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
        <span>Updated {relativeTime(page.freshness_at)}</span>
        {page.language !== "en" && (
          <span className="font-mono px-1.5 py-0.5 rounded bg-gray-100 uppercase text-[10px] tracking-wide">
            {page.language}
          </span>
        )}
      </div>

      {/* Headline */}
      <h1 className="text-2xl sm:text-[1.75rem] font-bold leading-tight tracking-tight mb-7">
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
              <span className="font-mono text-[9px] opacity-50 uppercase">{e.type}</span>
              {e.name}
            </span>
          ))}
        </div>
      )}

      {/* Synthesis */}
      <div className="text-[16px] leading-[1.8] text-[var(--ink)] mb-10">
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
    </div>
  );
}
