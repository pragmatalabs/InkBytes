"use client";

import Link from "next/link";
import { useState, useMemo } from "react";
import { relativeTime, isDeveloping, outletInitials } from "@/lib/api";
import type { EventSummary } from "@/lib/types";

// ── Avatar stack ────────────────────────────────────────────────────────────

const OUTLET_COLORS = [
  "#1a1a2e", "#2d5282", "#276749", "#7b341e",
  "#553c9a", "#97266d", "#2c5f62", "#744210",
];

function colorFor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
  return OUTLET_COLORS[Math.abs(h) % OUTLET_COLORS.length];
}

function AvatarStack({ outlets, count }: { outlets: string[]; count: number }) {
  const shown = outlets.slice(0, 4);
  const extra = count - shown.length;
  return (
    <span className="inline-flex items-center gap-2">
      <span className="flex items-center">
        {shown.map((name, i) => (
          <span
            key={i}
            title={name}
            className="inline-flex items-center justify-center rounded-full text-white ring-2 ring-white"
            style={{
              width: 20, height: 20,
              fontSize: 7, fontWeight: 700,
              background: colorFor(name),
              marginLeft: i === 0 ? 0 : -6,
              zIndex: shown.length - i,
            }}
          >
            {outletInitials(name)}
          </span>
        ))}
        {extra > 0 && (
          <span
            className="inline-flex items-center justify-center rounded-full bg-gray-300 text-gray-600 ring-2 ring-white"
            style={{ width: 20, height: 20, fontSize: 7, fontWeight: 700, marginLeft: -6 }}
          >
            +{extra}
          </span>
        )}
      </span>
      <span className="text-xs text-[var(--ink-muted)] font-medium">
        {count} {count === 1 ? "source" : "sources"}
      </span>
    </span>
  );
}

// ── Single event card ────────────────────────────────────────────────────────

function EventCard({ event }: { event: EventSummary }) {
  const developing = isDeveloping(event.freshness_at);

  return (
    <Link
      href={`/event/${event.id}`}
      className="group block bg-white border border-[var(--border)] rounded-xl p-5 hover:shadow-md hover:border-gray-300 transition-all"
    >
      {/* Top row: topic chip + DEVELOPING badge */}
      <div className="flex items-center gap-2 mb-3 min-h-[20px]">
        {event.topic && (
          <span className="text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
            {event.topic}
          </span>
        )}
        {developing && (
          <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-red-600">
            <span className="developing-dot" aria-hidden="true" />
            Developing
          </span>
        )}
        {event.language !== "en" && (
          <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 uppercase tracking-wide">
            {event.language}
          </span>
        )}
      </div>

      {/* Headline */}
      <h2 className="text-[15px] sm:text-[16px] font-semibold leading-snug tracking-tight group-hover:text-[var(--accent)] transition-colors mb-4">
        {event.headline}
      </h2>

      {/* Footer: avatar stack + article count + time */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <AvatarStack outlets={event.outlet_names ?? []} count={event.source_count} />

        <div className="flex items-center gap-3 text-xs text-[var(--ink-muted)]">
          {/* Coverage count */}
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>
            </svg>
            {event.article_count} {event.article_count === 1 ? "article" : "articles"}
          </span>
          <span>·</span>
          <span>{relativeTime(event.freshness_at)}</span>
        </div>
      </div>
    </Link>
  );
}

// ── Feed client (search + topic filter) ─────────────────────────────────────

interface Props {
  events: EventSummary[];
  error: string | null;
}

export default function FeedClient({ events, error }: Props) {
  const [search, setSearch] = useState("");
  const [activeTopic, setActiveTopic] = useState<string | null>(null);

  const topics = useMemo(
    () => Array.from(new Set(events.map((e) => e.topic).filter(Boolean))) as string[],
    [events],
  );

  const filtered = useMemo(() => {
    let list = events;
    if (activeTopic) list = list.filter((e) => e.topic === activeTopic);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((e) => e.headline.toLowerCase().includes(q));
    }
    return list;
  }, [events, activeTopic, search]);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">

      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold tracking-tight text-[var(--ink)]">
          Today&rsquo;s events
        </h1>
        <p className="text-xs text-[var(--ink-muted)] mt-0.5">
          One page per story · multiple sources · no noise
        </p>
      </div>

      {/* Search + topic chips */}
      {!error && events.length > 0 && (
        <div className="mb-5 flex flex-col sm:flex-row gap-3 sm:items-center">
          {/* Search input */}
          <div className="relative flex-1 max-w-xs">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--ink-muted)] pointer-events-none"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            >
              <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
            </svg>
            <input
              type="text"
              placeholder="Search events…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-sm bg-white border border-[var(--border)] rounded-full outline-none focus:border-gray-400 transition-colors"
            />
          </div>

          {/* Topic chips + entity graph CTA */}
          <div id="topics" className="flex items-center gap-1.5 flex-wrap">
            {topics.length > 0 && (
              <>
                <button
                  onClick={() => setActiveTopic(null)}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                    activeTopic === null
                      ? "bg-[var(--accent)] border-[var(--accent)] text-white"
                      : "bg-white border-[var(--border)] text-[var(--ink-muted)] hover:border-gray-400"
                  }`}
                >
                  All
                </button>
                {topics.map((t) => (
                  <button
                    key={t}
                    onClick={() => setActiveTopic(activeTopic === t ? null : t)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                      activeTopic === t
                        ? "bg-[var(--accent)] border-[var(--accent)] text-white"
                        : "bg-white border-[var(--border)] text-[var(--ink-muted)] hover:border-gray-400"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </>
            )}
            {/* Entity graph CTA — always visible, links to R3 */}
            <Link
              href="/entities"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border border-[var(--border)] text-[var(--accent)] hover:bg-[var(--accent)]/5 hover:border-[var(--accent)]/40 transition-colors"
            >
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="5" cy="6" r="2.4"/><circle cx="19" cy="7" r="2.4"/><circle cx="12" cy="18" r="2.4"/>
                <path d="M7 7 17 7M6.5 8 11 16M17.5 9 13 16"/>
              </svg>
              Entity graph
            </Link>
          </div>
        </div>
      )}

      {/* States */}
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </div>
      ) : events.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border)] px-5 py-10 text-center text-sm text-[var(--ink-muted)]">
          No published events yet.
          <span className="block mt-1 text-xs opacity-70">
            Run Curator with real API keys to generate pages.
          </span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border)] px-5 py-10 text-center text-sm text-[var(--ink-muted)]">
          No events match your filter.
          <button
            onClick={() => { setSearch(""); setActiveTopic(null); }}
            className="block mx-auto mt-2 text-xs underline hover:text-[var(--ink)] transition-colors"
          >
            Clear filters
          </button>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-2.5">
            {filtered.map((ev) => (
              <EventCard key={ev.id} event={ev} />
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-[var(--ink-muted)]">
            {filtered.length} {filtered.length === 1 ? "event" : "events"}
            {activeTopic || search ? " matching your filter" : ""}
          </p>
        </>
      )}
    </div>
  );
}
