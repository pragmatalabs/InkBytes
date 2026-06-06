"use client";

import Link from "next/link";
import { useState, useMemo, useRef, useEffect } from "react";
import { relativeTime, isDeveloping, outletInitials, freshnessClass } from "@/lib/api";
import type { EventSummary } from "@/lib/types";

// ── Types ────────────────────────────────────────────────────────────────────

type Lang = "all" | "en" | "es";

// ── Importance score: source count × recency (48-hour window) ────────────────

function importance(ev: EventSummary): number {
  const h = (Date.now() - new Date(ev.freshness_at).getTime()) / 3_600_000;
  const recency = Math.max(0, 48 - h) / 48; // 1 = now, 0 = 48h old
  return ev.source_count * (0.5 + 0.5 * recency);
}

// ── Shared atoms ─────────────────────────────────────────────────────────────

const OUTLET_COLORS = [
  "#1a1a2e", "#2d5282", "#276749", "#7b341e",
  "#553c9a", "#97266d", "#2c5f62", "#744210",
];

function colorFor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
  return OUTLET_COLORS[Math.abs(h) % OUTLET_COLORS.length];
}

function AvatarStack({ outlets, count, size = 20 }: { outlets: string[]; count: number; size?: number }) {
  const shown = outlets.slice(0, 5);
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
              width: size, height: size,
              fontSize: Math.round(size * 0.36), fontWeight: 700,
              background: colorFor(name),
              marginLeft: i === 0 ? 0 : -Math.round(size * 0.3),
              zIndex: shown.length - i,
            }}
          >
            {outletInitials(name)}
          </span>
        ))}
        {extra > 0 && (
          <span
            className="inline-flex items-center justify-center rounded-full bg-gray-300 text-gray-600 ring-2 ring-white"
            style={{ width: size, height: size, fontSize: Math.round(size * 0.36), fontWeight: 700, marginLeft: -Math.round(size * 0.3) }}
          >
            +{extra}
          </span>
        )}
      </span>
      <span className="text-xs text-[var(--ink-muted)] font-medium tabular-nums">
        {count} {count === 1 ? "source" : "sources"}
      </span>
    </span>
  );
}

function DevelopingBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-red-600">
      <span className="developing-dot" aria-hidden="true" />
      Developing
    </span>
  );
}

function TopicChip({ topic }: { topic: string }) {
  return (
    <span className="text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
      {topic}
    </span>
  );
}

function LangChip({ lang }: { lang: string }) {
  return (
    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 uppercase tracking-wide">
      {lang}
    </span>
  );
}

// ── Source strength dot — compact signal for stream rows ─────────────────────

function StrengthDot({ count, developing }: { count: number; developing: boolean }) {
  if (developing) return <span className="developing-dot shrink-0" aria-hidden="true" />;
  const color =
    count >= 5 ? "#16a34a" :  // green-600
    count >= 3 ? "#d97706" :  // amber-600
                 "#9ca3af";   // gray-400
  return (
    <span
      className="w-1.5 h-1.5 rounded-full shrink-0"
      style={{ background: color }}
      aria-hidden="true"
    />
  );
}

// ── LEAD card ─────────────────────────────────────────────────────────────────
// Full-width. Bold headline. Sources + coverage prominent.

function LeadCard({ event, showLang }: { event: EventSummary; showLang: boolean }) {
  const developing = isDeveloping(event.freshness_at);
  return (
    <Link
      href={`/event/${event.id}`}
      className={`group block bg-white border border-[var(--border)] border-l-4 ${freshnessClass(event.freshness_at)} rounded-xl p-6 sm:p-8 hover:shadow-lg hover:border-r-gray-200 hover:border-t-gray-200 hover:border-b-gray-200 transition-all`}
    >
      {/* Kicker row */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {event.topic && <TopicChip topic={event.topic} />}
        {developing && <DevelopingBadge />}
        {showLang && event.language !== "en" && <LangChip lang={event.language} />}
      </div>

      {/* Headline */}
      <h2 className="text-[1.5rem] sm:text-[1.75rem] font-extrabold leading-tight tracking-tight group-hover:text-[var(--accent)] transition-colors mb-5" style={{ textWrap: "balance" } as React.CSSProperties}>
        {event.headline}
      </h2>

      {/* Meta */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <AvatarStack outlets={event.outlet_names ?? []} count={event.source_count} size={22} />
        <div className="flex items-center gap-2.5 text-xs text-[var(--ink-muted)]">
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>
            </svg>
            {event.article_count} {event.article_count === 1 ? "article" : "articles"}
          </span>
          <span aria-hidden>·</span>
          <span>{relativeTime(event.freshness_at)}</span>
        </div>
      </div>
    </Link>
  );
}

// ── SECONDARY card ────────────────────────────────────────────────────────────
// 2-col grid. Medium weight.

function SecondaryCard({ event, showLang }: { event: EventSummary; showLang: boolean }) {
  const developing = isDeveloping(event.freshness_at);
  return (
    <Link
      href={`/event/${event.id}`}
      className="group block bg-white border border-[var(--border)] rounded-xl p-5 hover:shadow-md hover:border-gray-300 transition-all flex flex-col"
    >
      <div className="flex flex-wrap items-center gap-1.5 mb-3">
        {event.topic && <TopicChip topic={event.topic} />}
        {developing && <DevelopingBadge />}
        {showLang && event.language !== "en" && <LangChip lang={event.language} />}
      </div>

      <h3 className="text-[15px] font-bold leading-snug tracking-tight group-hover:text-[var(--accent)] transition-colors flex-1 mb-4" style={{ textWrap: "balance" } as React.CSSProperties}>
        {event.headline}
      </h3>

      <div className="flex items-center justify-between flex-wrap gap-2 mt-auto">
        <AvatarStack outlets={event.outlet_names ?? []} count={event.source_count} size={18} />
        <span className="text-xs text-[var(--ink-muted)]">
          {event.article_count} art · {relativeTime(event.freshness_at)}
        </span>
      </div>
    </Link>
  );
}

// ── STREAM row ────────────────────────────────────────────────────────────────
// Compact. Headline + strength dot + time. Apple "everything is available but quiet" feel.

function StreamRow({ event, showLang }: { event: EventSummary; showLang: boolean }) {
  const developing = isDeveloping(event.freshness_at);
  return (
    <Link
      href={`/event/${event.id}`}
      className="group flex items-center gap-3 py-3.5 border-b border-[var(--border)] last:border-0 hover:bg-gray-50 -mx-2 px-2 rounded transition-colors"
    >
      <StrengthDot count={event.source_count} developing={developing} />

      <span className="flex-1 min-w-0">
        <span className="text-sm font-medium leading-snug group-hover:text-[var(--accent)] transition-colors line-clamp-2">
          {event.headline}
        </span>
        {(event.topic || (showLang && event.language !== "en")) && (
          <span className="flex gap-1.5 mt-0.5">
            {event.topic && (
              <span className="text-[10px] text-[var(--ink-muted)] uppercase tracking-wide">
                {event.topic}
              </span>
            )}
            {showLang && event.language !== "en" && (
              <span className="text-[10px] font-mono text-[var(--ink-muted)] uppercase">
                {event.language}
              </span>
            )}
          </span>
        )}
      </span>

      <div className="shrink-0 flex items-center gap-1.5 text-xs text-[var(--ink-muted)] tabular-nums">
        <span className="font-semibold" style={{
          color: event.source_count >= 5 ? "#16a34a" : event.source_count >= 3 ? "#d97706" : undefined,
        }}>
          {event.source_count}
        </span>
        <span aria-hidden>·</span>
        <span>{relativeTime(event.freshness_at)}</span>
      </div>
    </Link>
  );
}

// ── Flat card (used when filtering) ──────────────────────────────────────────

function FlatCard({ event, showLang }: { event: EventSummary; showLang: boolean }) {
  const developing = isDeveloping(event.freshness_at);
  return (
    <Link
      href={`/event/${event.id}`}
      className={`group block bg-white border border-[var(--border)] border-l-4 ${freshnessClass(event.freshness_at)} rounded-xl p-5 hover:shadow-md hover:border-r-gray-300 hover:border-t-gray-300 hover:border-b-gray-300 transition-all`}
    >
      <div className="flex flex-wrap items-center gap-2 mb-3 min-h-[20px]">
        {event.topic && <TopicChip topic={event.topic} />}
        {developing && <DevelopingBadge />}
        {showLang && event.language !== "en" && <LangChip lang={event.language} />}
      </div>
      <h2 className="text-[15px] sm:text-[16px] font-semibold leading-snug tracking-tight group-hover:text-[var(--accent)] transition-colors mb-4">
        {event.headline}
      </h2>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <AvatarStack outlets={event.outlet_names ?? []} count={event.source_count} />
        <div className="flex items-center gap-2.5 text-xs text-[var(--ink-muted)]">
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

// ── Feed client ───────────────────────────────────────────────────────────────

interface Props {
  events: EventSummary[];
  error: string | null;
  focusSearch?: boolean;
}

const LANG_KEY = "inkbytes-lang";
const STREAM_INITIAL = 12;

const LANG_LABELS: Record<Lang, string> = { all: "All", en: "EN", es: "ES" };

export default function FeedClient({ events, error, focusSearch }: Props) {
  const [search, setSearch]           = useState("");
  const [activeTopic, setActiveTopic] = useState<string | null>(null);
  const [lang, setLangState]          = useState<Lang>("all");
  const [streamExpanded, setStreamExpanded] = useState(false);
  const searchRef                     = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem(LANG_KEY) as Lang | null;
    if (saved === "en" || saved === "es" || saved === "all") setLangState(saved);
  }, []);

  function setLang(l: Lang) {
    setLangState(l);
    localStorage.setItem(LANG_KEY, l);
  }

  useEffect(() => {
    if (focusSearch) {
      searchRef.current?.focus();
      searchRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [focusSearch]);

  const topics = useMemo(
    () => Array.from(new Set(events.map((e) => e.topic).filter(Boolean))) as string[],
    [events],
  );

  const hasFilter = lang !== "all" || !!activeTopic || !!search.trim();

  const filtered = useMemo(() => {
    let list = events;
    if (lang !== "all") list = list.filter((e) => e.language === lang);
    if (activeTopic)    list = list.filter((e) => e.topic === activeTopic);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (e) => e.headline.toLowerCase().includes(q) || (e.topic ?? "").toLowerCase().includes(q),
      );
    }
    return list;
  }, [events, lang, activeTopic, search]);

  // Editorial sort: highest importance first.
  const sorted = useMemo(
    () => [...filtered].sort((a, b) => importance(b) - importance(a)),
    [filtered],
  );

  function clearAll() {
    setSearch("");
    setActiveTopic(null);
    setLang("all");
  }

  const showLangChip = lang === "all";

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  });

  // Editorial tiers — only when there's no active filter.
  const useEditorial = !hasFilter && sorted.length >= 1;
  const lead      = useEditorial ? sorted[0]          : null;
  const secondary = useEditorial ? sorted.slice(1, 3)  : [];
  const stream    = useEditorial ? sorted.slice(3)     : [];
  const flatList  = useEditorial ? []                  : sorted;

  const streamVisible = streamExpanded ? stream : stream.slice(0, STREAM_INITIAL);
  const streamHidden  = stream.length - streamVisible.length;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-widest text-[var(--ink-muted)] mb-1">
            {today}
          </p>
          <h1 className="text-xl font-bold tracking-tight text-[var(--ink)]">
            Today&rsquo;s events
          </h1>
          <p className="text-xs text-[var(--ink-muted)] mt-0.5">
            One page per story · multiple sources · no noise
          </p>
        </div>

        {/* Language toggle */}
        {!error && events.length > 0 && (
          <div
            className="inline-flex items-center p-0.5 bg-gray-100 rounded-full gap-0.5 shrink-0 pt-1 self-start"
            role="group"
            aria-label="Language filter"
          >
            {(["all", "en", "es"] as Lang[]).map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                aria-pressed={lang === l}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                  lang === l
                    ? "bg-white text-[var(--accent)] shadow-sm"
                    : "text-[var(--ink-muted)] hover:text-[var(--ink)]"
                }`}
              >
                {LANG_LABELS[l]}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Search + filters ─────────────────────────────────────────────────── */}
      {!error && events.length > 0 && (
        <div className="mb-6 flex flex-col sm:flex-row gap-3 sm:items-center">
          <div className="relative flex-1 max-w-xs">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--ink-muted)] pointer-events-none"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            >
              <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
            </svg>
            <input
              ref={searchRef}
              type="text"
              placeholder={lang === "es" ? "Buscar eventos…" : "Search events…"}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-sm bg-white border border-[var(--border)] rounded-full outline-none focus:border-gray-400 transition-colors"
            />
          </div>

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

      {/* ── States ───────────────────────────────────────────────────────────── */}
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </div>
      ) : events.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border)] px-5 py-10 text-center text-sm text-[var(--ink-muted)]">
          No published events yet.
          <span className="block mt-1 text-xs opacity-70">Run Curator with real API keys to generate pages.</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border)] px-5 py-10 text-center text-sm text-[var(--ink-muted)]">
          {lang !== "all"
            ? `No ${LANG_LABELS[lang]} events${activeTopic || search ? " matching your filter" : ""}.`
            : "No events match your filter."}
          {hasFilter && (
            <button onClick={clearAll} className="block mx-auto mt-2 text-xs underline hover:text-[var(--ink)] transition-colors">
              Clear all filters
            </button>
          )}
        </div>
      ) : useEditorial ? (

        /* ── EDITORIAL LAYOUT ───────────────────────────────────────────────── */
        <div className="space-y-6">

          {/* Lead */}
          {lead && <LeadCard event={lead} showLang={showLangChip} />}

          {/* Secondary 2-col grid */}
          {secondary.length > 0 && (
            <div className={`grid gap-4 ${secondary.length === 1 ? "" : "sm:grid-cols-2"}`}>
              {secondary.map((ev) => (
                <SecondaryCard key={ev.id} event={ev} showLang={showLangChip} />
              ))}
            </div>
          )}

          {/* Stream */}
          {stream.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] mb-1 pb-2 border-b border-[var(--border)]">
                More stories
              </p>
              <div>
                {streamVisible.map((ev) => (
                  <StreamRow key={ev.id} event={ev} showLang={showLangChip} />
                ))}
              </div>
              {streamHidden > 0 && (
                <button
                  onClick={() => setStreamExpanded(true)}
                  className="mt-4 w-full py-2.5 text-xs font-semibold text-[var(--ink-muted)] hover:text-[var(--ink)] border border-[var(--border)] rounded-lg hover:border-gray-400 transition-colors"
                >
                  Show {streamHidden} more {streamHidden === 1 ? "story" : "stories"}
                </button>
              )}
            </div>
          )}
        </div>

      ) : (

        /* ── FLAT LIST (when filtering) ─────────────────────────────────────── */
        <>
          <div className="flex flex-col gap-2.5">
            {flatList.map((ev) => (
              <FlatCard key={ev.id} event={ev} showLang={showLangChip} />
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-[var(--ink-muted)]">
            {filtered.length} {filtered.length === 1 ? "event" : "events"} matching your filter
            {" · "}
            <button onClick={clearAll} className="underline hover:text-[var(--ink)] transition-colors">
              clear
            </button>
          </p>
        </>
      )}
    </div>
  );
}
