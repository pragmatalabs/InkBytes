import { getEvents, getTrendingTopics, getOutlookArchive } from "@/lib/api";
import type { EventSummary, TrendingTopic, OutlookArchiveEntry } from "@/lib/types";
import FeedClient from "./feed-client";

// force-dynamic: pages calling internal Docker services must never use ISR —
// the build container can't reach inkbytes-curator-api and would bake the
// error state permanently (ADR-R-0005). force-dynamic gives a fresh server
// render on every request; the 20-min client-side router.refresh() in
// FeedClient handles background updates while the tab is open.
export const dynamic = "force-dynamic";

export default async function HomePage({
  searchParams,
}: {
  searchParams?: Promise<{ search?: string; topic?: string }>;
}) {
  const params = await (searchParams ?? Promise.resolve({} as Record<string, string>));
  const focusSearch = (params as Record<string, string>).search === "1";
  // Trending-topic drill-down (ADR-0027): ?topic= server-filters the feed via
  // the Curator ?topic= param (article-level EXISTS — same semantics as the
  // trending count, so the chip's number matches what the reader sees).
  const topic = ((params as Record<string, string>).topic ?? "").trim() || null;

  let events: EventSummary[] = [];
  let trending: TrendingTopic[] = [];
  let outlookLead: (OutlookArchiveEntry & { lang: string }) | null = null;
  let error: string | null = null;

  // The day's lead Outlook column surfaced in the feed (Stage 2c). Uses es
  // (Outlook's primary language); a 7-day window so the card still shows the most
  // recent column across a weekend / missed-cron gap (editions are newest-first).
  const OUTLOOK_LANG = "es";

  try {
    // Trending + Outlook are best-effort — a failure must not blank the feed.
    const [ev, tr, outlook] = await Promise.all([
      getEvents(500, topic ? { topic } : undefined),
      getTrendingTopics().catch(() => [] as TrendingTopic[]),
      getOutlookArchive(OUTLOOK_LANG, 7)
        .then((r) => r.editions[0] ?? null)
        .catch(() => null),
    ]);
    events = ev;
    trending = tr;
    outlookLead = outlook ? { ...outlook, lang: OUTLOOK_LANG } : null;
  } catch {
    // Reader-facing copy — never leak internals (service names, ports).
    error = "We're having trouble loading the latest stories right now. It usually resolves in a moment.";
  }

  return (
    <FeedClient
      events={events}
      trending={trending}
      activeTopic={topic}
      error={error}
      focusSearch={focusSearch}
      outlookLead={outlookLead}
    />
  );
}
