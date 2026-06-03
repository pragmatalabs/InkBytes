import Link from "next/link";
import { getEvents, relativeTime, freshnessClass, freshnessLabel } from "@/lib/api";
import type { EventSummary } from "@/lib/types";

export const revalidate = 60;

const TOPIC_COLORS: Record<string, string> = {
  Economy:    "bg-emerald-100 text-emerald-800",
  Technology: "bg-blue-100 text-blue-800",
  Politics:   "bg-purple-100 text-purple-800",
  Business:   "bg-amber-100 text-amber-800",
  Sports:     "bg-orange-100 text-orange-800",
  Science:    "bg-cyan-100 text-cyan-800",
  Health:     "bg-rose-100 text-rose-800",
};

function topicColor(topic: string | null): string {
  return topic && TOPIC_COLORS[topic] ? TOPIC_COLORS[topic] : "bg-gray-100 text-gray-600";
}

function EventCard({ event }: { event: EventSummary }) {
  const ribbon = freshnessClass(event.freshness_at);
  const { label: freshLabel, color: freshColor } = freshnessLabel(event.freshness_at);

  return (
    <Link
      href={`/event/${event.id}`}
      className={`group block border border-l-4 ${ribbon} border-[var(--border)] rounded-lg p-5 hover:shadow-md transition-all bg-white`}
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-[15px] sm:text-base font-semibold leading-snug group-hover:text-[var(--accent)] transition-colors flex-1">
          {event.headline}
        </h2>
        {event.language !== "en" && (
          <span className="shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 uppercase tracking-wide mt-0.5">
            {event.language}
          </span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[var(--ink-muted)]">
        {event.topic && (
          <span className={`px-2 py-0.5 rounded-full font-medium ${topicColor(event.topic)}`}>
            {event.topic}
          </span>
        )}
        <span className="flex items-center gap-1">
          <svg className="w-3 h-3 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
          </svg>
          {event.source_count} {event.source_count === 1 ? "source" : "sources"}
        </span>
        <span>·</span>
        <span>
          {freshLabel && (
            <span className={`font-semibold mr-1 ${freshColor}`}>{freshLabel}</span>
          )}
          {relativeTime(event.freshness_at)}
        </span>
      </div>
    </Link>
  );
}

export default async function HomePage() {
  let events: EventSummary[] = [];
  let error: string | null = null;

  try {
    events = await getEvents();
  } catch {
    error = "Could not reach the Curator service. Is it running on port 8060?";
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <div className="mb-7">
        <h1 className="text-xl font-bold tracking-tight text-[var(--ink)]">Today&rsquo;s events</h1>
        <p className="text-xs text-[var(--ink-muted)] mt-0.5">
          One page per story &middot; multiple sources &middot; no noise
        </p>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </div>
      ) : events.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[var(--border)] px-5 py-10 text-center text-sm text-[var(--ink-muted)]">
          No published events yet.
          <span className="block mt-1 text-xs opacity-70">
            Run Curator with real API keys to generate pages.
          </span>
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {events.map((ev) => (
            <EventCard key={ev.id} event={ev} />
          ))}
        </div>
      )}
    </div>
  );
}
