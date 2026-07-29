import type { Metadata } from "next";
import { getEvents, getTrendingTopics, getOutlookArchive } from "@/lib/api";
import type { EventSummary, TrendingTopic, OutlookArchiveEntry } from "@/lib/types";
import FeedClient from "../feed-client";

// force-dynamic — internal Curator service is only resolvable at runtime (ADR-R-0005).
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Browse",
  description: "Search and filter every event — by theme, language, and trending topic.",
};

// Browse (Slice C-B): the full searchable/filterable feed. Everything the
// finite briefing (/) leaves out lives here — search, theme + language filters,
// trending drill-down (?topic=), and the complete paginated stream.
export default async function BrowsePage({
  searchParams,
}: {
  searchParams?: Promise<{ search?: string; topic?: string }>;
}) {
  const params = await (searchParams ?? Promise.resolve({} as Record<string, string>));
  const focusSearch = (params as Record<string, string>).search === "1";
  const topic = ((params as Record<string, string>).topic ?? "").trim() || null;

  let events: EventSummary[] = [];
  let trending: TrendingTopic[] = [];
  let outlookLead: (OutlookArchiveEntry & { lang: string }) | null = null;
  let error: string | null = null;

  const OUTLOOK_LANG = "es";

  try {
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
    error = "We're having trouble loading the latest stories right now. It usually resolves in a moment.";
  }

  return (
    <FeedClient
      mode="browse"
      events={events}
      trending={trending}
      activeTopic={topic}
      error={error}
      focusSearch={focusSearch}
      outlookLead={outlookLead}
    />
  );
}
