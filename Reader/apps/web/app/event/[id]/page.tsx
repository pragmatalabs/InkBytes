import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { getEvent, getRelatedEvents, relativeTime, parseJson, isDeveloping, outletInitials } from "@/lib/api";
import { themeAccent } from "@/lib/theme-colors";
import type { EvidenceItem, EntityItem, RelatedEvent, MediaRailItem, TitleHistoryEntry } from "@/lib/types";
import ShareButton from "./share-button";
import EventActionBar from "./event-action-bar";
import StoryNav from "./story-nav";
import FollowButton from "./follow-button";
import { NewsMarkdown } from "@/components/news-markdown";
import ReadTracker from "@/components/read-tracker";
import EventCover from "@/components/event-cover";

export const revalidate = 300;

/** First sentence of synthesis — used for OG description. */
function firstSentence(text: string): string {
  const match = text.replace(/\[(?:Source|Fuente): [^\]]+\]/g, "").match(/[^.!?]+[.!?]/);
  return match ? match[0].trim() : text.slice(0, 160);
}

// ── Prototype isEvent helpers ─────────────────────────────────────────────────
// Hashed outlet-avatar colours (mirrors feed-client), corroboration strength
// (source-count → label + colour, same thresholds as the feed StrengthDot), and
// a compact mono time ("2D", "41M") for the STARTED/UPDATED clock line.
const OUTLET_COLORS = ["#1a1a2e", "#2d5282", "#276749", "#7b341e", "#553c9a", "#97266d", "#2c5f62", "#744210"];
function outletColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
  return OUTLET_COLORS[Math.abs(h) % OUTLET_COLORS.length];
}
function corroboration(n: number): { label: string; color: string } {
  return n >= 5 ? { label: "Strong corroboration", color: "#16a34a" }
    : n >= 3 ? { label: "Moderate corroboration", color: "#d97706" }
    : { label: "Limited corroboration", color: "#9ca3af" };
}
function shortAgo(iso: string): string {
  return relativeTime(iso).replace(/\s*ago$/i, "").toUpperCase();
}

export async function generateMetadata(
  { params }: { params: Promise<{ id: string }> }
): Promise<Metadata> {
  const { id } = await params;
  try {
    const page = await getEvent(id);
    const description = firstSentence(page.synthesis_md);
    // ADR-0034 / M1: do NOT redistribute the source outlet's og:image in our own
    // share metadata either (same unlicensed-photo exposure as the hero). Omit it;
    // a static owned OG cover is a follow-up (P1).
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
      },
      twitter: {
        card: "summary",
        title: page.headline,
        description,
      },
    };
  } catch {
    return { title: "Event" };
  }
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

  // Merged away (ADR-0040) → 302 the old URL to the survivor event.
  if (page.merged_into) {
    redirect(`/event/${page.merged_into}`);
  }

  const evidence = parseJson<EvidenceItem[]>(page.evidence_rail);
  const entities = parseJson<EntityItem[]>(page.entities);
  const titleHistory = parseJson<TitleHistoryEntry[]>(page.title_history ?? []);
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

  // Media rail (video-only, ADR-R-0006) — parsed once for the drawer + the
  // "Watch · n" tile count in StoryNav.
  const rail: MediaRailItem[] = (() => {
    const raw = page.media_rail;
    return Array.isArray(raw) ? raw
      : typeof raw === "string" ? (JSON.parse(raw) as MediaRailItem[])
      : [];
  })();
  const videos = rail.filter((m) => m.type === "video");
  // Category accent — the drop cap, the sheet rail bars, the match bars.
  const accent = themeAccent(page.category);

  // Prototype isEvent provenance: sources·quotes + corroboration + clock line.
  const quotes = evidence.length;
  const corrob = corroboration(page.source_count);
  const catLabel = (page.category ?? page.topic ?? "").toUpperCase();

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      {/* Content-engagement analytics (Umami custom events) — no-op until configured */}
      <ReadTracker eventId={page.id} category={page.category} language={page.language} freshnessAt={page.freshness_at} />
      {/* Event chrome — back · EN/ES · Save · Share (prototype chromeEvent).
          Video now lives in the "Watch" sheet (StoryNav), not the action bar. */}
      <EventActionBar
        eventId={page.id}
        headline={page.headline}
        category={page.category}
        language={page.language}
        alsoLanguages={page.also_languages}
        back={
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-xs text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors"
          >
            ← All events
          </Link>
        }
        share={<ShareButton title={page.headline} text={firstSentence(page.synthesis_md)} />}
      />

      {/* Eyebrow (prototype isEvent): ● DEVELOPING (left) · CATEGORY (right). */}
      <div className="flex items-center gap-2 mb-3">
        {developing && (
          <span suppressHydrationWarning className="inline-flex items-center gap-1.5">
            <span className="developing-dot" aria-hidden="true" />
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-red-600">Developing</span>
          </span>
        )}
        {catLabel && (
          <span className="ml-auto font-mono text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--ink-muted)]">
            {catLabel}
          </span>
        )}
      </div>

      {/* Headline — heavy + tight (prototype isEvent: 29px/800/-.035em). */}
      <h1 className="text-[28px] sm:text-[32px] font-extrabold leading-[1.08] tracking-[-0.035em] text-balance">
        {page.headline}
      </h1>

      {/* Provenance row (prototype isEvent): avatars + sources·quotes +
          corroboration strength + STARTED/UPDATED clock. Bordered top+bottom.
          suppressHydrationWarning: relativeTime uses Date.now() (server UTC vs
          client local tz). */}
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
            {page.source_count > 3 && (
              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-gray-200 text-gray-600 text-[7.5px] font-bold ring-2 ring-[var(--bg)]" style={{ marginLeft: -6 }}>
                +{page.source_count - 3}
              </span>
            )}
          </span>
        )}
        <div className="leading-[1.35] min-w-0">
          <div className="text-[12px] font-semibold text-[var(--ink)] tabular-nums">
            {page.source_count} {page.source_count === 1 ? "source" : "sources"}
            {quotes > 0 && ` · ${quotes} ${quotes === 1 ? "quote" : "quotes"}`}
          </div>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: corrob.color }} aria-hidden />
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: corrob.color }}>
              {corrob.label} · {page.source_count} of {page.source_count}
            </span>
          </div>
          <div suppressHydrationWarning className="font-mono text-[10.5px] text-[var(--ink-muted)] mt-0.5 uppercase tracking-[0.02em]">
            {page.occurred_at && <>Started {shortAgo(page.occurred_at)} · </>}Updated {shortAgo(page.freshness_at)}
          </div>
        </div>
      </div>

      {/* Synthesis — the story, high on the page. Source Serif 4 body + a
          category-accent Inter drop cap (prototype). */}
      <div
        className="synthesis-body mb-8"
        style={{ ["--cap" as string]: accent }}
      >
        <NewsMarkdown source={page.synthesis_md} />
      </div>

      {/* Owned cover — inset + captioned, BELOW the prose (ADR-0034: never the
          source og:image, never a photo of this event). Was a full-width
          aspect-video hero above the fold (Stage 5). */}
      <figure className="mb-10">
        <EventCover
          id={page.id}
          category={page.category}
          cover={page.cover_image}
          className="w-full h-40 rounded-xl"
        />
        <figcaption className="mt-2 text-center text-[11px] text-[var(--ink-muted)] italic">
          Illustrative. Not a photograph of this event.
        </figcaption>
      </figure>

      {/* "This story" 2×2 action grid + the drawers each tile opens (prototype).
          Watch / Evidence / Entities / Related now live in progressive-disclosure
          bottom sheets instead of long inline sections. */}
      <StoryNav
        videos={videos}
        evidence={evidence}
        entities={entities}
        related={related}
        timeline={titleHistory}
        currentHeadline={page.headline}
        nextId={related[0]?.id ?? null}
        accent={accent}
      />

      {/* Follow this story — subscribe to updates (prototype). Distinct from the
          header Save (read-later): surfaces in the Saved screen with an
          "Updated" badge (Slice B). */}
      <FollowButton
        eventId={page.id}
        headline={page.headline}
        category={page.category}
        language={page.language}
      />
    </div>
  );
}
