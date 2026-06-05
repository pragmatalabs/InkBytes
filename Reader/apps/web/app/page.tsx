import { getEvents } from "@/lib/api";
import type { EventSummary } from "@/lib/types";
import FeedClient from "./feed-client";

export const revalidate = 60;

export default async function HomePage() {
  let events: EventSummary[] = [];
  let error: string | null = null;

  try {
    events = await getEvents();
  } catch {
    error = "Could not reach the Curator service. Is it running on port 8060?";
  }

  return <FeedClient events={events} error={error} />;
}
