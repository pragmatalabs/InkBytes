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

      {/* Eyebrow — topic + developing + language. The developing dot now sits
          above the headline (Stage 5); the old meta row + stat grid are gone. */}
      <div className="flex flex-wrap items-center gap-2 mb-2 text-xs">
        {page.topic && (
          <span className="px-2 py-0.5 rounded-full bg-gray-100 font-medium text-gray-700">
            {page.topic}
          </span>
        )}
        {developing && (
          <span suppressHydrationWarning className="inline-flex items-center gap-1.5 font-semibold uppercase tracking-wide text-[10px] text-red-600">
            <span className="developing-dot" aria-hidden="true" />
            Developing
          </span>
        )}
        {page.language && page.language !== "en" && (
          <span className="font-mono px-1.5 py-0.5 rounded bg-gray-100 uppercase text-[10px] tracking-wide text-[var(--ink-muted)]">
            {page.language}
          </span>
        )}
      </div>

      {/* Headline — the first substantial content, above the fold (Stage 5). */}
      <h1 className="text-[1.6rem] sm:text-[1.75rem] md:text-3xl font-bold leading-tight tracking-tight mb-4">
        {page.headline}
      </h1>

      {/* Provenance row — avatars · sources · Started · Updated (informational).
          The full source quotes open in the Evidence sheet (StoryNav tile below).
          suppressHydrationWarning: relativeTime uses Date.now() (server UTC vs
          client local tz) — would otherwise throw React #418. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 mb-8 text-xs text-[var(--ink-muted)]">
        {outletNames.length > 0 && (
          <span className="flex items-center">
            {outletNames.map((name, i) => (
              <span
                key={i}
                title={name}
                className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[var(--accent)] text-white text-[8px] font-bold uppercase ring-2 ring-white"
                style={{ marginLeft: i === 0 ? 0 : -5, zIndex: outletNames.length - i }}
              >
                {outletInitials(name)}
              </span>
            ))}
          </span>
        )}
        <span className="font-semibold text-[var(--ink)]">
          {page.source_count} {page.source_count === 1 ? "source" : "sources"}
        </span>
        {page.occurred_at && (
          <>
            <span aria-hidden>·</span>
            <span suppressHydrationWarning>Started {relativeTime(page.occurred_at)}</span>
          </>
        )}
        <span aria-hidden>·</span>
        <span suppressHydrationWarning>Updated {relativeTime(page.freshness_at)}</span>
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
