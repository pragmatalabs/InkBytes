import { getEvents, getOutlookArchive } from "@/lib/api";
import type { EventSummary, OutlookArchiveEntry } from "@/lib/types";
import FeedClient from "./feed-client";

// force-dynamic: pages calling internal Docker services must never use ISR —
// the build container can't reach inkbytes-curator-api and would bake the
// error state permanently (ADR-R-0005). force-dynamic gives a fresh server
// render on every request.
export const dynamic = "force-dynamic";

// The home is the finite "briefing" (Slice C-B): top-N ranked + progress +
// caught-up. Search / filters / trending / the full stream live in /browse.
export default async function HomePage() {
  let events: EventSummary[] = [];
  let outlookLead: (OutlookArchiveEntry & { lang: string }) | null = null;
  let error: string | null = null;

  const OUTLOOK_LANG = "es";

  try {
    // Still fetch the full set so the briefing can rank the top-N and show the
    // "Browse all N" count; trending isn't shown on the briefing.
    const [ev, outlook] = await Promise.all([
      getEvents(500),
      getOutlookArchive(OUTLOOK_LANG, 7)
        .then((r) => r.editions[0] ?? null)
        .catch(() => null),
    ]);
    events = ev;
    outlookLead = outlook ? { ...outlook, lang: OUTLOOK_LANG } : null;
  } catch {
    error = "We're having trouble loading the latest stories right now. It usually resolves in a moment.";
  }

  return <FeedClient mode="briefing" events={events} error={error} outlookLead={outlookLead} />;
}
