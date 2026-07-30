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
type Lead = (OutlookArchiveEntry & { lang: string }) | null;

export default async function HomePage() {
  let events: EventSummary[] = [];
  // Fetch BOTH language editions of the day's lead column server-side; the
  // client picks the one matching the reading pref (the pref is client-only, so
  // the server can't know it). Fixes EN readers seeing the ES column.
  let outlookLeadEn: Lead = null;
  let outlookLeadEs: Lead = null;
  let error: string | null = null;

  try {
    // The briefing only needs the top-N (snapshot) + the developing rail (the
    // freshest, always near the top), so 60 is plenty — no need to serialize all
    // ~500 to the client. The full set + total count live in /browse.
    const [ev, outlookEn, outlookEs] = await Promise.all([
      getEvents(60),
      getOutlookArchive("en", 7).then((r) => r.editions[0] ?? null).catch(() => null),
      getOutlookArchive("es", 7).then((r) => r.editions[0] ?? null).catch(() => null),
    ]);
    events = ev;
    outlookLeadEn = outlookEn ? { ...outlookEn, lang: "en" } : null;
    outlookLeadEs = outlookEs ? { ...outlookEs, lang: "es" } : null;
  } catch {
    error = "We're having trouble loading the latest stories right now. It usually resolves in a moment.";
  }

  return <FeedClient mode="briefing" events={events} error={error} outlookLeadEn={outlookLeadEn} outlookLeadEs={outlookLeadEs} />;
}
