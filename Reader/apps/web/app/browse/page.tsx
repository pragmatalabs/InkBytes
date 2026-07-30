import type { Metadata } from "next";
import { getEvents } from "@/lib/api";
import type { EventSummary } from "@/lib/types";
import FeedClient from "../feed-client";

// force-dynamic — internal Curator service is only resolvable at runtime (ADR-R-0005).
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Browse",
  description: "Search and filter every event — by theme, language, and trending topic.",
};

// Browse (Slice C-B): the full searchable/filterable feed. Everything the
// finite briefing (/) leaves out lives here — search, theme + language filters,
// trending drill-down (?topic=), and the complete stream (prototype isBrowse:
// counted category rails + "ALL STORIES · NEWEST FIRST" + rail-card list).
export default async function BrowsePage({
  searchParams,
}: {
  searchParams?: Promise<{ search?: string; topic?: string }>;
}) {
  const params = await (searchParams ?? Promise.resolve({} as Record<string, string>));
  const focusSearch = (params as Record<string, string>).search === "1";
  const topic = ((params as Record<string, string>).topic ?? "").trim() || null;

  let events: EventSummary[] = [];
  let error: string | null = null;

  try {
    events = await getEvents(500, topic ? { topic } : undefined);
  } catch {
    error = "We're having trouble loading the latest stories right now. It usually resolves in a moment.";
  }

  return (
    <FeedClient
      mode="browse"
      events={events}
      activeTopic={topic}
      error={error}
      focusSearch={focusSearch}
    />
  );
}
