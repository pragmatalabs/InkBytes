import { getEvents } from "@/lib/api";
import type { EventSummary } from "@/lib/types";
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
  searchParams?: Promise<{ search?: string }>;
}) {
  const params = await (searchParams ?? Promise.resolve({} as Record<string, string>));
  const focusSearch = (params as Record<string, string>).search === "1";

  let events: EventSummary[] = [];
  let error: string | null = null;

  try {
    events = await getEvents();
  } catch {
    error = "Could not reach the Curator service. Is it running on port 8060?";
  }

  return <FeedClient events={events} error={error} focusSearch={focusSearch} />;
}
