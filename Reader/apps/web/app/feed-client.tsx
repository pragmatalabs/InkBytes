"use client";

import Link from "next/link";
import { useState, useMemo, useRef, useEffect, useTransition, Fragment } from "react";
import { useRouter } from "next/navigation";
import { relativeTime, isDeveloping, outletInitials, freshnessClass } from "@/lib/api";
import type { EventSummary, TrendingTopic } from "@/lib/types";
import { CategoryIcon } from "@/components/icons";
import { DailySplash } from "@/components/daily-splash";

// ── Types ────────────────────────────────────────────────────────────────────

type Lang     = "all" | "en" | "es";
type Category = "all" | "politics" | "business" | "technology" | "sports"
              | "health" | "environment" | "culture" | "world";

// ── Constants ─────────────────────────────────────────────────────────────────

const BREAKING_COUNT = 20;  // events pinned in the "Latest" strip
const STREAM_INITIAL = 60;  // stream rows shown before "show more"

const CATEGORIES: { key: Category; label: string }[] = [
  { key: "all",         label: "All"      },
  { key: "politics",    label: "Politics" },
  { key: "business",    label: "Business" },
  { key: "technology",  label: "Tech"     },
  { key: "sports",      label: "Sports"   },
  { key: "health",      label: "Health"   },
  { key: "environment", label: "Climate"  },
  { key: "culture",     label: "Culture"  },
  { key: "world",       label: "World"    },
];

// ── Sort: global-first, freshness_at DESC within each tier (ADR-0017) ──────────
// Mirrors the API's ORDER BY so the client never undoes the server ranking.
// Global events (has_global_outlet=true) receive a +6 h freshness bonus —
// identical to the INTERVAL '6 hours' applied in the SQL ORDER BY.

const GLOBAL_BONUS_MS = 6 * 60 * 60 * 1000; // 6 hours in milliseconds

function importance(ev: EventSummary): number {
  const bonus = ev.has_global_outlet ? GLOBAL_BONUS_MS : 0;
  return new Date(ev.freshness_at).getTime() + bonus;
}

// ── Category chip styles ──────────────────────────────────────────────────────

const CAT_STYLES: Record<string, string> = {
  politics:    "bg-red-50    text-red-600",
  business:    "bg-blue-50   text-blue-600",
  technology:  "bg-violet-50 text-violet-600",
  sports:      "bg-green-50  text-green-600",
  health:      "bg-pink-50   text-pink-600",
  environment: "bg-emerald-50 text-emerald-600",
  culture:     "bg-amber-50  text-amber-600",
  world:       "bg-gray-100  text-gray-500",
};

// ── Avatar helpers ────────────────────────────────────────────────────────────

const OUTLET_COLORS = [
  "#1a1a2e", "#2d5282", "#276749", "#7b341e",
  "#553c9a", "#97266d", "#2c5f62", "#744210",
];

function colorFor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
  return OUTLET_COLORS[Math.abs(h) % OUTLET_COLORS.length];
}

// ── Shared atoms ──────────────────────────────────────────────────────────────

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

function CategoryChip({ category }: { category: string }) {
  const cls   = CAT_STYLES[category] ?? "bg-gray-100 text-gray-500";
  const label = category === "environment" ? "Climate" : category;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full ${cls}`}>
      <CategoryIcon category={category} className="w-3 h-3 shrink-0" />
      {label}
    </span>
  );
}

function InlineCatBadge({ category }: { category: string }) {
  if (!category || category === "world") return null;
  const cls   = CAT_STYLES[category] ?? "bg-gray-100 text-gray-400";
  const label = category === "environment" ? "climate" : category;
  return (
    <span className={`text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full ${cls}`}>
      {label}
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

function StrengthDot({ count, developing }: { count: number; developing: boolean }) {
  if (developing) return <span className="developing-dot shrink-0" aria-hidden="true" />;
  const color =
    count >= 5 ? "#16a34a" :
    count >= 3 ? "#d97706" :
                 "#9ca3af";
  return (
    <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} aria-hidden="true" />
  );
}

// ── BREAKING card (horizontal strip) ─────────────────────────────────────────

function BreakingCard({ event, showLang }: { event: EventSummary; showLang: boolean }) {
  return (
    <Link
      href={`/event/${event.id}`}
      className="group block bg-white border border-[var(--border)] border-l-4 border-l-red-500 rounded-xl p-4 hover:shadow-md transition-all w-[270px] sm:w-[300px] shrink-0"
    >
      <div className="flex flex-wrap items-center gap-1.5 mb-2">
        {event.category && <CategoryChip category={event.category} />}
        {showLang && event.language !== "en" && <LangChip lang={event.language} />}
      </div>
      <h3
        className="text-[13px] font-bold leading-snug group-hover:text-[var(--accent)] transition-colors line-clamp-3 mb-3"
        style={{ textWrap: "balance" } as React.CSSProperties}
      >
        {event.headline}
      </h3>
      <div className="flex items-center justify-between gap-2">
        <AvatarStack outlets={event.outlet_names ?? []} count={event.source_count} size={16} />
        <span className="text-xs text-[var(--ink-muted)] tabular-nums shrink-0">
          {relativeTime(event.freshness_at)}
        </span>
      </div>
    </Link>
  );
}

// ── LEAD card ─────────────────────────────────────────────────────────────────

function LeadCard({ event, showLang }: { event: EventSummary; showLang: boolean }) {
  const developing = isDeveloping(event.freshness_at);
  return (
    <Link
      href={`/event/${event.id}`}
      className={`group block bg-white border border-[var(--border)] border-l-4 ${freshnessClass(event.freshness_at)} rounded-xl overflow-hidden hover:shadow-lg hover:border-r-gray-200 hover:border-t-gray-200 hover:border-b-gray-200 transition-all`}
    >
      {/* Cover image — only rendered when Messor extracted an og:image */}
      {event.lead_image && (
        <div className="w-full h-48 sm:h-56 overflow-hidden bg-gray-100">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={event.lead_image}
            alt=""
            className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
            loading="lazy"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        </div>
      )}
      <div className="p-6 sm:p-8">
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {event.category && <CategoryChip category={event.category} />}
          {developing && <DevelopingBadge />}
          {showLang && event.language !== "en" && <LangChip lang={event.language} />}
        </div>
        <h2
          className="text-[1.5rem] sm:text-[1.75rem] font-extrabold leading-tight tracking-tight group-hover:text-[var(--accent)] transition-colors mb-2"
          style={{ textWrap: "balance" } as React.CSSProperties}
        >
          {event.headline}
        </h2>
        {event.topic && (
          <p className="text-xs text-[var(--ink-muted)] italic mb-5 line-clamp-1">{event.topic}</p>
        )}
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
      </div>
    </Link>
  );
}

// ── SECONDARY card ────────────────────────────────────────────────────────────

function SecondaryCard({ event, showLang }: { event: EventSummary; showLang: boolean }) {
  const developing = isDeveloping(event.freshness_at);
  return (
    <Link
      href={`/event/${event.id}`}
      className="group block bg-white border border-[var(--border)] rounded-xl overflow-hidden hover:shadow-md hover:border-gray-300 transition-all flex flex-col"
    >
      {/* Thumbnail — 16:9 strip above text when image available */}
      {event.lead_image && (
        <div className="w-full h-36 overflow-hidden bg-gray-100 shrink-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={event.lead_image}
            alt=""
            className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
            loading="lazy"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        </div>
      )}
      <div className="p-5 flex flex-col flex-1">
        <div className="flex flex-wrap items-center gap-1.5 mb-3">
          {event.category && <CategoryChip category={event.category} />}
          {developing && <DevelopingBadge />}
          {showLang && event.language !== "en" && <LangChip lang={event.language} />}
        </div>
        <h3
          className="text-[15px] font-bold leading-snug tracking-tight group-hover:text-[var(--accent)] transition-colors flex-1 mb-1"
          style={{ textWrap: "balance" } as React.CSSProperties}
        >
          {event.headline}
        </h3>
        {event.topic && (
          <p className="text-[11px] text-[var(--ink-muted)] italic mb-3 line-clamp-1">{event.topic}</p>
        )}
        <div className="flex items-center justify-between flex-wrap gap-2 mt-auto">
          <AvatarStack outlets={event.outlet_names ?? []} count={event.source_count} size={18} />
          <span className="text-xs text-[var(--ink-muted)]">
            {event.article_count} art · {relativeTime(event.freshness_at)}
          </span>
        </div>
      </div>
    </Link>
  );
}

// ── STREAM row ────────────────────────────────────────────────────────────────

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
        <span className="flex gap-1.5 mt-0.5 items-center flex-wrap">
          {event.category && <InlineCatBadge category={event.category} />}
          {showLang && event.language !== "en" && (
            <span className="text-[10px] font-mono text-[var(--ink-muted)] uppercase">
              {event.language}
            </span>
          )}
        </span>
      </span>
      <div className="shrink-0 flex items-center gap-1.5 text-xs text-[var(--ink-muted)] tabular-nums">
        <span
          className="font-semibold"
          style={{ color: event.source_count >= 5 ? "#16a34a" : event.source_count >= 3 ? "#d97706" : undefined }}
        >
          {event.source_count}
        </span>
        <span aria-hidden>·</span>
        <span>{relativeTime(event.freshness_at)}</span>
      </div>
    </Link>
  );
}

// ── Flat card (filtered view) ─────────────────────────────────────────────────

function FlatCard({ event, showLang }: { event: EventSummary; showLang: boolean }) {
  const developing = isDeveloping(event.freshness_at);
  return (
    <Link
      href={`/event/${event.id}`}
      className={`group block bg-white border border-[var(--border)] border-l-4 ${freshnessClass(event.freshness_at)} rounded-xl p-5 hover:shadow-md hover:border-r-gray-300 hover:border-t-gray-300 hover:border-b-gray-300 transition-all`}
    >
      <div className="flex flex-wrap items-center gap-2 mb-3 min-h-[20px]">
        {event.category && <CategoryChip category={event.category} />}
        {developing && <DevelopingBadge />}
        {showLang && event.language !== "en" && <LangChip lang={event.language} />}
      </div>
      <h2 className="text-[15px] sm:text-[16px] font-semibold leading-snug tracking-tight group-hover:text-[var(--accent)] transition-colors mb-1">
        {event.headline}
      </h2>
      {event.topic && (
        <p className="text-[11px] text-[var(--ink-muted)] italic mb-3 line-clamp-1">{event.topic}</p>
      )}
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
  trending?: TrendingTopic[];
  /** Active trending topic from ?topic= — the feed `events` are already
   *  server-filtered to it (ADR-0027); we only drive chip state + navigation. */
  activeTopic?: string | null;
  error: string | null;
  focusSearch?: boolean;
}

const LANG_KEY = "inkbytes-lang";
const CAT_KEY  = "inkbytes-cat";

const LANG_LABELS: Record<Lang, string> = { all: "All", en: "EN", es: "ES" };

export default function FeedClient({ events, trending = [], activeTopic = null, error, focusSearch }: Props) {
  const [search, setSearch]                 = useState("");
  const [activeCategory, setActiveCategory] = useState<Category>("all");
  const [lang, setLangState]                = useState<Lang>("all");
  const [streamExpanded, setStreamExpanded] = useState(false);
  const searchRef                           = useRef<HTMLInputElement>(null);

  // ── 20-minute auto-refresh ─────────────────────────────────────────────────
  // router.refresh() re-runs the server component tree (re-fetches /events from
  // Curator) and reconciles the diff without a full page reload.  Client state
  // (filters, search, lang preference) is preserved across the refresh.
  const router                      = useRouter();
  const [isPending, startTransition] = useTransition();
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);

  useEffect(() => {
    const MS = 20 * 60 * 1000; // 20 minutes
    const id = setInterval(() => {
      startTransition(() => router.refresh());
      setRefreshedAt(new Date().toISOString());
    }, MS);
    return () => clearInterval(id);
  }, [router]);

  // Restore preferences from localStorage
  useEffect(() => {
    const savedLang = localStorage.getItem(LANG_KEY) as Lang | null;
    if (savedLang === "en" || savedLang === "es" || savedLang === "all") setLangState(savedLang);
    const savedCat = localStorage.getItem(CAT_KEY) as Category | null;
    if (savedCat && CATEGORIES.some((c) => c.key === savedCat)) setActiveCategory(savedCat);
  }, []);

  function setLang(l: Lang) { setLangState(l); localStorage.setItem(LANG_KEY, l); }
  function setCat(c: Category) {
    setActiveCategory(c);
    localStorage.setItem(CAT_KEY, c);
    setStreamExpanded(false);
    // If a server-side topic filter is active, clicking a theme chip drops it
    // (theme is the primary feed facet; topic is the trending drill-down).
    if (activeTopic && c !== "all") startTransition(() => router.push("/"));
  }
  // Trending-topic drill-down (ADR-0027): navigate to ?topic= so the server
  // filters the feed via the Curator ?topic= param (article-level — matches the
  // trending count). Toggling the active topic clears it. Theme is a separate
  // client filter that composes on top; we reset it so the two don't surprise.
  function toggleTopic(t: string) {
    setActiveCategory("all");
    localStorage.setItem(CAT_KEY, "all");
    setStreamExpanded(false);
    const next = activeTopic === t ? "/" : `/?topic=${encodeURIComponent(t)}`;
    startTransition(() => router.push(next));
  }

  useEffect(() => {
    if (focusSearch) {
      searchRef.current?.focus();
      searchRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [focusSearch]);

  const hasFilter = lang !== "all" || activeCategory !== "all" || !!activeTopic || !!search.trim();

  const filtered = useMemo(() => {
    let list = events;
    if (lang !== "all")           list = list.filter((e) => e.language === lang);
    if (activeCategory !== "all") list = list.filter((e) => (e.category ?? "world") === activeCategory);
    // NB: topic filtering is done server-side (events arrive pre-filtered to
    // ?topic=); no client-side topic filter here.
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (e) =>
          e.headline.toLowerCase().includes(q) ||
          (e.topic    ?? "").toLowerCase().includes(q) ||
          (e.category ?? "").toLowerCase().includes(q),
      );
    }
    return list;
  }, [events, lang, activeCategory, search]);

  const sorted = useMemo(
    () => [...filtered].sort((a, b) => importance(b) - importance(a)),
    [filtered],
  );

  function clearAll() {
    setSearch(""); setCat("all"); setLang("all");
    if (activeTopic) startTransition(() => router.push("/"));  // drop ?topic=
  }

  const showLangChip = lang === "all";

  // Date rendered only on client to avoid hydration mismatch
  const [today, setToday] = useState("");
  useEffect(() => {
    setToday(
      new Date().toLocaleDateString("en-US", {
        weekday: "long", month: "long", day: "numeric", year: "numeric",
      }),
    );
  }, []);

  // ── Editorial tiers ──────────────────────────────────────────────────────
  // No-filter view: breaking strip (top 5) + editorial layout (rest).
  // Filter active: flat list, no breaking strip.
  const useEditorial = !hasFilter && sorted.length >= 1;

  const breakingItems  = useEditorial ? sorted.slice(0, BREAKING_COUNT) : [];
  const afterBreaking  = useEditorial ? sorted.slice(BREAKING_COUNT)    : [];

  const lead      = afterBreaking[0]         ?? null;
  const secondary = afterBreaking.slice(1, 3);
  const stream    = afterBreaking.slice(3);
  const flatList  = useEditorial ? [] : sorted;

  const streamVisible = streamExpanded ? stream : stream.slice(0, STREAM_INITIAL);
  const streamHidden  = stream.length - streamVisible.length;

  // Category tabs: only show categories present in the full events list
  const availableCats = useMemo(() => {
    const seen = new Set(events.map((e) => e.category ?? "world"));
    return CATEGORIES.filter((c) => c.key === "all" || seen.has(c.key));
  }, [events]);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">

      {/* Daily splash — mobile-only "welcome back", once per 24h (over the feed) */}
      <DailySplash events={events} />

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-widest text-[var(--ink-muted)] mb-1">
            {today}
          </p>
          <h1 className="text-xl font-bold tracking-tight text-[var(--ink)]">
            Today&rsquo;s events
          </h1>
          <p className="text-xs text-[var(--ink-muted)] mt-0.5 flex items-center gap-1.5 flex-wrap">
            <span>
              {events.length > 0
                ? `${events.length} stories · one page per event · multiple sources`
                : "One page per story · multiple sources · no noise"}
            </span>
            {/* Live refresh indicator — spins during refresh, shows last-updated time after */}
            <span
              className="inline-flex items-center gap-0.5 opacity-50"
              title="Feed refreshes automatically every 20 minutes"
            >
              <svg
                className={`w-2.5 h-2.5 shrink-0 ${isPending ? "animate-spin" : ""}`}
                viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
              >
                <path d="M21 2v6h-6"/>
                <path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
                <path d="M3 22v-6h6"/>
                <path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
              </svg>
              <span suppressHydrationWarning>
                {isPending
                  ? "refreshing…"
                  : refreshedAt
                  ? `${new Date(refreshedAt).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`
                  : "20m"}
              </span>
            </span>
          </p>
        </div>

        {/* Language toggle */}
        {!error && events.length > 0 && (
          <div
            className="inline-flex items-center p-0.5 bg-gray-100 rounded-full gap-0.5 shrink-0 self-start"
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

      {/* ── Category tabs ────────────────────────────────────────────────────── */}
      {!error && events.length > 0 && (
        <div className="mb-4 -mx-1 px-1 overflow-x-auto scrollbar-hide">
          <div className="flex items-center gap-1.5 flex-nowrap pb-1">
            {availableCats.map((c) => (
              <button
                key={c.key}
                onClick={() => setCat(c.key)}
                aria-pressed={activeCategory === c.key}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap border transition-colors ${
                  activeCategory === c.key
                    ? "bg-[var(--accent)] border-[var(--accent)] text-white"
                    : "bg-white border-[var(--border)] text-[var(--ink-muted)] hover:border-gray-400 hover:text-[var(--ink)]"
                }`}
              >
                {c.key !== "all" && (
                  <CategoryIcon category={c.key} className="w-3.5 h-3.5 shrink-0 opacity-80" />
                )}
                {c.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Trending topics (ADR-0027) ──────────────────────────────────────── */}
      {!error && trending.length > 0 && (
        <div className="mb-4 -mx-1 px-1 overflow-x-auto scrollbar-hide">
          <div className="flex items-center gap-1.5 flex-nowrap pb-1">
            <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-[var(--accent)] whitespace-nowrap pr-1">
              <span className="developing-dot shrink-0" aria-hidden="true" />
              Trending
            </span>
            {trending.map((t) => (
              <button
                key={t.topic}
                onClick={() => toggleTopic(t.topic)}
                aria-pressed={activeTopic === t.topic}
                title={`${t.event_count} stories · ${t.article_count} articles`}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap border transition-colors ${
                  activeTopic === t.topic
                    ? "bg-[var(--accent)] border-[var(--accent)] text-white"
                    : "bg-white border-[var(--border)] text-[var(--ink-muted)] hover:border-gray-400 hover:text-[var(--ink)]"
                }`}
              >
                {t.topic}
                <span className={activeTopic === t.topic ? "text-white/70" : "text-[var(--ink-muted)] opacity-60"}>
                  {t.event_count}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Search + clear ───────────────────────────────────────────────────── */}
      {!error && events.length > 0 && (
        <div className="mb-6 flex items-center gap-2.5">
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
              onChange={(e) => { setSearch(e.target.value); setStreamExpanded(false); }}
              className="w-full pl-8 pr-3 py-1.5 text-sm bg-white border border-[var(--border)] rounded-full outline-none focus:border-gray-400 transition-colors"
            />
          </div>
          <Link
            href="/entities"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border border-[var(--border)] text-[var(--accent)] hover:bg-[var(--accent)]/5 hover:border-[var(--accent)]/40 transition-colors shrink-0"
          >
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="5" cy="6" r="2.4"/><circle cx="19" cy="7" r="2.4"/><circle cx="12" cy="18" r="2.4"/>
              <path d="M7 7 17 7M6.5 8 11 16M17.5 9 13 16"/>
            </svg>
            Entities
          </Link>
          {hasFilter && (
            <button
              onClick={clearAll}
              className="text-xs text-[var(--ink-muted)] hover:text-[var(--ink)] underline transition-colors shrink-0"
            >
              Clear
            </button>
          )}
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
          No events match your filter.
          <button onClick={clearAll} className="block mx-auto mt-2 text-xs underline hover:text-[var(--ink)] transition-colors">
            Clear filters
          </button>
        </div>

      ) : useEditorial ? (

        /* ── EDITORIAL LAYOUT ───────────────────────────────────────────────── */
        <div className="space-y-7">

          {/* ── Latest strip (top 5 most recent) ────────────────────────────── */}
          {breakingItems.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="developing-dot" aria-hidden="true" />
                <p className="text-[10px] font-bold uppercase tracking-widest text-red-600">
                  Latest
                </p>
                <span className="text-[10px] text-[var(--ink-muted)]">
                  — {breakingItems.length} most recent stories
                </span>
              </div>
              <div className="flex gap-3 overflow-x-auto pb-2 -mx-2 px-2 snap-x snap-mandatory">
                {breakingItems.map((ev) => (
                  <div key={ev.id} className="snap-start shrink-0">
                    <BreakingCard event={ev} showLang={showLangChip} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Lead ────────────────────────────────────────────────────────── */}
          {lead && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] pb-2 mb-3 border-b border-[var(--border)]">
                Top story
              </p>
              <LeadCard event={lead} showLang={showLangChip} />
            </div>
          )}

          {/* ── Secondary 2-col grid ─────────────────────────────────────────── */}
          {secondary.length > 0 && (
            <div className={`grid gap-4 ${secondary.length === 1 ? "" : "sm:grid-cols-2"}`}>
              {secondary.map((ev) => (
                <SecondaryCard key={ev.id} event={ev} showLang={showLangChip} />
              ))}
            </div>
          )}

          {/* ── Stream ──────────────────────────────────────────────────────── */}
          {stream.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)] pb-2 mb-1 border-b border-[var(--border)]">
                More stories — {stream.length} total
              </p>
              <div>
                {streamVisible.map((ev, idx) => {
                  // Insert a "Regional" section divider before the first event
                  // that has no global-outlet coverage (ADR-0017).  The divider
                  // only appears once — when the ranked list transitions from
                  // globally-covered stories to regional-only ones.
                  const isFirstRegional =
                    !ev.has_global_outlet &&
                    (idx === 0 || streamVisible[idx - 1].has_global_outlet);
                  return (
                    <Fragment key={ev.id}>
                      {isFirstRegional && (
                        <div className="flex items-center gap-2 mt-4 mb-1 pt-4 border-t border-[var(--border)]">
                          <svg className="w-3 h-3 text-[var(--ink-muted)] opacity-60 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                          </svg>
                          <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--ink-muted)]">
                            Regional
                          </span>
                        </div>
                      )}
                      <StreamRow event={ev} showLang={showLangChip} />
                    </Fragment>
                  );
                })}
              </div>
              {streamHidden > 0 && (
                <button
                  onClick={() => setStreamExpanded(true)}
                  className="mt-4 w-full py-2.5 text-xs font-semibold text-[var(--ink-muted)] hover:text-[var(--ink)] border border-[var(--border)] rounded-lg hover:border-gray-400 transition-colors"
                >
                  Show all {streamHidden} more {streamHidden === 1 ? "story" : "stories"}
                </button>
              )}
            </div>
          )}

        </div>

      ) : (

        /* ── FLAT LIST (filtered) ────────────────────────────────────────────── */
        <>
          <div className="flex flex-col gap-2.5">
            {flatList.map((ev) => (
              <FlatCard key={ev.id} event={ev} showLang={showLangChip} />
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-[var(--ink-muted)]">
            {filtered.length} {filtered.length === 1 ? "story" : "stories"} matching your filter
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
