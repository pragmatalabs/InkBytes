import { getEvents, getTrendingTopics } from "@/lib/api";
import type { EventSummary, TrendingTopic } from "@/lib/types";
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
  let error: string | null = null;

  try {
    // Trending is best-effort — a failure must not blank the feed.
    [events, trending] = await Promise.all([
      getEvents(500, topic ? { topic } : undefined),
      getTrendingTopics().catch(() => [] as TrendingTopic[]),
    ]);
  } catch {
    error = "Could not reach the Curator service. Is it running on port 8060?";
  }

  return (
    <FeedClient
      events={events}
      trending={trending}
      activeTopic={topic}
      error={error}
      focusSearch={focusSearch}
    />
  );
}
