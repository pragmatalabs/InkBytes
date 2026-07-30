"use client";

import Link from "next/link";
import { useState, useMemo, useRef, useEffect, useTransition, Fragment } from "react";
import { useRouter } from "next/navigation";
import { relativeTime, isDeveloping, outletInitials } from "@/lib/api";
import { useLang } from "@/lib/prefs";
import { t, categoryLabel } from "@/lib/i18n";
import type { EventSummary, OutlookArchiveEntry } from "@/lib/types";
import { themeAccent } from "@/lib/theme-colors";
import { ColumnMast, titleCase } from "@/components/column-mast";
import { getRead } from "@/lib/read-state";
import { reconcileBriefing } from "@/lib/briefing-set";
import { DailySplash } from "@/components/daily-splash";
import RetryButton from "@/components/retry-button";

// ── Types ────────────────────────────────────────────────────────────────────

type Lang     = "all" | "en" | "es";
// 15 enrichment themes (Curator ADR-0032). Original 8 first, then the 7 added
// by ADR-0032 item 1. Backend `_VALID_THEMES` is the source of truth.
type Category = "all" | "politics" | "business" | "technology" | "sports"
              | "health" | "environment" | "culture" | "world"
              | "science" | "entertainment" | "crime" | "education"
              | "lifestyle" | "religion" | "disaster";

// ── Constants ─────────────────────────────────────────────────────────────────

// "A briefing, not a feed" (Slice C1a): the top N ranked events are today's
// briefing — a finite set the read-progress bar tracks. The rest of the feed
// stays browsable below (the full finite/Browse split is Slice C-B).
const BRIEFING_SIZE = 12;

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
  // ADR-0032 item 1 — 7 added themes.
  { key: "science",       label: "Science"       },
  { key: "entertainment", label: "Entertainment" },
  { key: "crime",         label: "Crime"         },
  { key: "education",     label: "Education"     },
  { key: "lifestyle",     label: "Lifestyle"     },
  { key: "religion",      label: "Religion"      },
  { key: "disaster",      label: "Disaster"      },
];

// ── Sort: global-first, freshness_at DESC within each tier (ADR-0017) ──────────
// Mirrors the API's ORDER BY so the client never undoes the server ranking.
// Global events (has_global_outlet=true) receive a +6 h freshness bonus —
// identical to the INTERVAL '6 hours' applied in the SQL ORDER BY.

const GLOBAL_BONUS_MS = 6 * 60 * 60 * 1000; // 6 hours in milliseconds

// The "last update" clock used for the card timestamp, the DEVELOPING badge, AND
// the sort — so all three agree and the card matches the event page's "Updated".
// We use freshness_at (= newest article scraped, what the event page already shows
// as "Updated") rather than occurred_at (the days-old start — that's the bug: an
// actively-developing story read "5d ago" at the top of "most recent") and rather
// than last_material_update_at (currently processing-contaminated: the post-reset
// pipeline clusters backlogged articles NOW, stamping it ~now even when the newest
// article is 1.5d old). freshness_at is the honest last-news time, and tight
// clustering (ADR-0031) is what now prevents the off-topic float ADR-0033 used the
// material clock to avoid.
function lastUpdate(ev: EventSummary): string {
  return ev.freshness_at;
}

function importance(ev: EventSummary): number {
  const bonus = ev.has_global_outlet ? GLOBAL_BONUS_MS : 0;
  return new Date(lastUpdate(ev)).getTime() + bonus;
}

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


/**
 * Relative timestamp ("29m ago"). relativeTime() uses Date.now(), so the
 * server render and the client hydration straddle different instants and can
 * differ by a minute → hydration mismatch. suppressHydrationWarning lets the
 * client keep the server's value without regenerating the tree; the 20-min
 * feed refresh re-renders it fresh. (Same pattern as the date header + the
 * event page's Developing badge.)
 */
function TimeAgo({ iso }: { iso: string }) {
  const lang = useLang();
  return <span suppressHydrationWarning>{relativeTime(iso, lang)}</span>;
}


// ── LEAD card ─────────────────────────────────────────────────────────────────

// ── Section header (Outlook grammar, Stage 2c) ────────────────────────────────
// Quiet 16px title + optional count + flush-right action. Replaces the old
// red-dot / tiny-uppercase feed section labels with the same grammar Outlook uses.

// ── Outlook card (Stage 2c) ───────────────────────────────────────────────────
// Surfaces the day's lead editorial column in the feed — the best content, which
// otherwise sits behind a tab. The persona mark + theme accent carry the column
// identity (same treatment as the /outlook index cards).
function OutlookCard({ entry }: { entry: OutlookArchiveEntry & { lang: string } }) {
  const lang = useLang();
  return (
    <Link
      href={`/outlook/${entry.theme}?lang=${entry.lang}&date=${entry.edition_date}`}
      style={{ borderLeftColor: themeAccent(entry.theme) }}
      className="group block bg-white border border-[var(--border)] border-l-4 rounded-xl p-5 hover:shadow-md hover:border-gray-300 transition-all"
    >
      <div className="flex items-center gap-2 mb-2">
        <ColumnMast persona={entry.persona} theme={entry.theme} sublabel={`${t(lang, "todays_outlook")} · ${titleCase(entry.theme)}`} />
        <svg className="ml-auto w-4 h-4 text-[var(--ink-muted)] opacity-60 shrink-0 group-hover:translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12h14M13 6l6 6-6 6"/>
        </svg>
      </div>
      <div className="text-[15px] font-bold leading-snug line-clamp-2" style={{ textWrap: "balance" } as React.CSSProperties}>
        {entry.headline}
      </div>
    </Link>
  );
}

// ── LEAD card ─────────────────────────────────────────────────────────────────


// ── SECONDARY card ────────────────────────────────────────────────────────────


// ── STREAM row ────────────────────────────────────────────────────────────────


// ── Flat card (filtered view) ─────────────────────────────────────────────────


// ── Feed client ───────────────────────────────────────────────────────────────

interface Props {
  events: EventSummary[];
  /** Active trending topic from ?topic= — the feed `events` are already
   *  server-filtered to it (ADR-0027); we only drive chip state + navigation. */
  activeTopic?: string | null;
  error: string | null;
  focusSearch?: boolean;
  /** The day's lead Outlook column (Stage 2c) — surfaced as a card near the top
   *  of the feed. null when Outlook is unavailable (best-effort; never blanks). */
  outlookLeadEn?: (OutlookArchiveEntry & { lang: string }) | null;
  outlookLeadEs?: (OutlookArchiveEntry & { lang: string }) | null;
  /** Slice C-B: "briefing" (home /) = finite top-N + progress + caught-up, no
   *  filters; "browse" (/browse) = the full searchable/filterable feed. */
  mode?: "briefing" | "browse";
}

const LANG_KEY = "inkbytes-lang";
const CAT_KEY  = "inkbytes-cat";


// ── Brief row (Reader-prototype isBrief style) ────────────────────────────────
// Uniform text card: category rail + heavy headline + mono meta (sources · time,
// or "READ" when read). Optional outlet avatars (Developing rows). Read → dim.
function BriefRow({ event, showAvatars = false, read = false, updated = false }: {
  event: EventSummary; showAvatars?: boolean; read?: boolean; updated?: boolean;
}) {
  const lang = useLang();
  return (
    <Link
      href={`/event/${event.id}`}
      className={`grid grid-cols-[4px_1fr] gap-3.5 py-3.5 border-b border-[var(--border)] group transition-colors hover:bg-[#f4f3f0] -mx-2 px-2 ${read && !updated ? "opacity-50" : ""}`}
    >
      <i className="block rounded-sm" style={{ background: themeAccent(event.category) }} />
      <div className="min-w-0">
        <div className={`${showAvatars ? "text-[17px]" : "text-[16px]"} font-bold leading-[1.25] tracking-[-0.02em] text-balance group-hover:text-[var(--accent)] transition-colors`}>
          {event.headline}
        </div>
        <div className="flex items-center gap-2.5 mt-2">
          {showAvatars && (
            <span className="flex items-center">
              {(event.outlet_names ?? []).slice(0, 4).map((name, i) => (
                <span
                  key={i}
                  title={name}
                  className="inline-flex items-center justify-center rounded-full text-white ring-2 ring-[var(--bg)]"
                  style={{ width: 17, height: 17, fontSize: 6.5, fontWeight: 700, background: colorFor(name), marginLeft: i === 0 ? 0 : -5, zIndex: 4 - i }}
                >
                  {outletInitials(name)}
                </span>
              ))}
            </span>
          )}
          <span suppressHydrationWarning className="text-[11.5px] text-[var(--ink-muted)] tabular-nums">
            {event.source_count} {t(lang, event.source_count === 1 ? "source_one" : "source_many")}
          </span>
          <span suppressHydrationWarning className="ml-auto font-mono text-[11.5px] text-[var(--ink-muted)] tabular-nums">
            {read && !updated ? t(lang, "read_tag") : <TimeAgo iso={event.freshness_at} />}
          </span>
        </div>
      </div>
    </Link>
  );
}

// ── Section rule (mono label + count, strong ink underline) ───────────────────
function BriefSection({ label, count, accent = false }: { label: string; count: React.ReactNode; accent?: boolean }) {
  return (
    <div className="flex items-center gap-2 mt-7 pb-1.5 border-b-2 border-[var(--ink)]">
      {accent && <span className="developing-dot shrink-0" aria-hidden="true" />}
      <span className={`font-mono text-[11px] font-bold uppercase tracking-[0.12em] ${accent ? "text-red-600" : "text-[var(--ink)]"}`}>{label}</span>
      <span className="ml-auto font-mono text-[11px] font-bold text-[var(--ink-muted)] tabular-nums">{count}</span>
    </div>
  );
}

export default function FeedClient({ events, activeTopic = null, error, focusSearch, outlookLeadEn = null, outlookLeadEs = null, mode = "briefing" }: Props) {
  const briefing = mode === "briefing";
  const uiLang = useLang();
  // The day's lead editorial column in the reader's language (fall back to
  // whichever edition exists). Fill-after-mount: EN on first paint, ES swaps in.
  const outlookLead = (uiLang === "es" ? outlookLeadEs : outlookLeadEn) ?? outlookLeadEn ?? outlookLeadEs;
  const [search, setSearch]                 = useState("");
  const [activeCategory, setActiveCategory] = useState<Category>("all");
  const [lang, setLangState]                = useState<Lang>("all");
  const searchRef                           = useRef<HTMLInputElement>(null);

  // Read state (Stage 6) — client-only. Empty on the server + first paint so the
  // SSR markup renders every card UNREAD; populated after mount, then a re-render
  // dims read cards + flags updates. This is the hydration-safe order the brief
  // requires (rendering read state on the server reintroduces React #418).
  const [readMap, setReadMap] = useState<Record<string, string>>({});
  useEffect(() => {
    const sync = () => setReadMap(getRead());
    sync();
    // Re-sync on return from an event page (same tab) so a just-read story dims.
    window.addEventListener("visibilitychange", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener("visibilitychange", sync);
      window.removeEventListener("focus", sync);
    };
  }, []);
  const readState = (ev: EventSummary): { read: boolean; updated: boolean } => {
    const seen = readMap[ev.id];
    if (!seen) return { read: false, updated: false };
    return { read: true, updated: new Date(ev.freshness_at) > new Date(seen) };
  };

  // ── 20-minute auto-refresh ─────────────────────────────────────────────────
  // router.refresh() re-runs the server component tree (re-fetches /events from
  // Curator) and reconciles the diff without a full page reload.  Client state
  // (filters, search, lang preference) is preserved across the refresh.
  const router                      = useRouter();
  const [, startTransition] = useTransition();

  useEffect(() => {
    const MS = 20 * 60 * 1000; // 20 minutes
    const id = setInterval(() => {
      startTransition(() => router.refresh());
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
    // If a server-side topic filter is active, clicking a theme chip drops it
    // (theme is the primary feed facet; topic is the trending drill-down).
    if (activeTopic && c !== "all") startTransition(() => router.push("/browse"));
  }

  useEffect(() => {
    if (focusSearch) {
      searchRef.current?.focus();
      searchRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [focusSearch]);


  const filtered = useMemo(() => {
    let list = events;
    // ADR-0037 cross-language dedup: in the "All" view, collapse same-story
    // EN+ES duplicates to the primary (the richer-source one) so each story
    // appears once. The EN/ES tabs filter by language and show every event of
    // that language (no collapse) — so switching tabs never loses a story.
    if (lang === "all")           list = list.filter((e) => e.primary !== false);
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
    if (activeTopic) startTransition(() => router.push("/browse"));  // drop ?topic=
  }


  // Date rendered only on client to avoid hydration mismatch. `brief` holds the
  // prototype dateline ("TUE · 28 JUL 2026 · 07:10") + weekday for the title.
  const [brief, setBrief] = useState({ dateline: "", weekday: "" });
  useEffect(() => {
    const d = new Date();
    const loc = uiLang === "es" ? "es-ES" : "en-US";
    const wds = d.toLocaleDateString(loc, { weekday: "short" }).toUpperCase();
    const mon = d.toLocaleDateString(loc, { month: "short" }).toUpperCase();
    const day = String(d.getDate()).padStart(2, "0");
    const time = d.toLocaleTimeString(loc, { hour: "2-digit", minute: "2-digit", hour12: false });
    setBrief({
      dateline: `${wds} · ${day} ${mon} ${d.getFullYear()} · ${time}`,
      weekday: d.toLocaleDateString(loc, { weekday: "long" }),
    });
  }, [uiLang]);

  // ── Editorial tiers ──────────────────────────────────────────────────────
  // No-filter view: ONE ranked list — lead + 2 secondary + stream, straight off
  // `sorted`. The former "Latest" 3D coverflow (Stage 2a) pinned the top 20 in a
  // swipe strip that hid 19 of them behind taps; those top stories now flow into
  // the list. Filter active: flat list.

  // ── Briefing set (Slice C-B) ──────────────────────────────────────────────
  // Frozen per-day snapshot of the top-N so the finite briefing stops
  // reshuffling on every live re-fetch. Hydration-safe: null until mount (server
  // + first paint fall back to the live top-N, which equals the snapshot on the
  // day's first load), then the mount effect loads/creates the frozen set.
  const [briefingIds, setBriefingIds] = useState<string[] | null>(null);
  const byId = useMemo(() => new Map(sorted.map((e) => [e.id, e])), [sorted]);
  useEffect(() => {
    // Only freeze once a full set is available — a partial early fetch would
    // otherwise snapshot too few. Below BRIEFING_SIZE we fall back to the live
    // top-N (a genuinely tiny corpus never needs freezing).
    if (!briefing || sorted.length < BRIEFING_SIZE) return;
    const day = new Date().toISOString().slice(0, 10);
    // Heal the frozen set against the live feed: keep stable survivors, backfill
    // fresh top stories so it stays full instead of dwindling as the day's
    // stories age out of the window (which collapsed the sections). Pass the
    // full ranked id list so the backfill pool is the whole feed.
    setBriefingIds(reconcileBriefing(day, sorted.map((e) => e.id), BRIEFING_SIZE));
  }, [briefing, sorted]);

  const briefingSet: EventSummary[] = briefing
    ? (briefingIds
        ? briefingIds.map((id) => byId.get(id)).filter((e): e is EventSummary => Boolean(e))
        : sorted.slice(0, BRIEFING_SIZE))
    : [];


  // ── Briefing progress (Slice C1a) ─────────────────────────────────────────
  // Read-progress over the frozen briefingSet above. readMap is client-only
  // (starts {} on server + first paint), so progress renders 0 then fills after
  // mount — the same hydration-safe order the card dimming uses (no #418).
  const briefingTotal  = briefingSet.length;
  const briefingRead   = briefingSet.filter((ev) => readState(ev).read).length;
  const briefingCaught = briefingTotal > 0 && briefingRead === briefingTotal;

  // Prototype isBrief split: the finite set → a small "Developing now" lead
  // (cap ~3, most-recent breaking) + "The briefing" (everything else). Capping
  // keeps both sections populated even when the freshness gate marks many as
  // developing.
  const briefingMins = Math.max(1, Math.round(briefingTotal * 1.4));
  const briefingLeft = briefingTotal - briefingRead;
  // Only peel a "Developing now" lead off the top when there's still a briefing
  // left underneath — a small set would otherwise land entirely in the lead and
  // "The briefing" section would disappear (the bug on sparse/decayed days).
  const canSplit = briefingTotal > 3;
  const devSet  = canSplit ? briefingSet.filter((ev) => isDeveloping(ev.freshness_at)).slice(0, 3) : [];
  const devIds  = new Set(devSet.map((ev) => ev.id));
  const restSet = briefingSet.filter((ev) => !devIds.has(ev.id));

  // Category tabs: only show categories present in the full events list
  const availableCats = useMemo(() => {
    const seen = new Set(events.map((e) => e.category ?? "world"));
    return CATEGORIES.filter((c) => c.key === "all" || seen.has(c.key));
  }, [events]);

  // Per-category counts for the browse rail-chips (prototype isBrowse: "Politics 127").
  const catCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const e of events) {
      const k = e.category ?? "world";
      m.set(k, (m.get(k) ?? 0) + 1);
    }
    return m;
  }, [events]);
  const catCount = (key: string) => (key === "all" ? events.length : catCounts.get(key) ?? 0);

  // Browse section header: "ALL STORIES" (all) or "POLITICS · 127" (a category).
  const activeCatLabel = CATEGORIES.find((c) => c.key === activeCategory)?.label ?? "";
  const browseHeading =
    activeCategory === "all"
      ? t(uiLang, "all_stories")
      : `${categoryLabel(uiLang, activeCategory, activeCatLabel)} · ${catCount(activeCategory)}`;


  return (
    <div className="max-w-3xl mx-auto px-4 py-8">

      {/* Daily splash — mobile-only "welcome back", once per 24h. Briefing home
          only (not /browse). */}
      {briefing && <DailySplash events={events} />}

      {/* ── Header (briefing only — browse goes straight to search, isBrowse) ── */}
      {briefing && (
        /* Prototype isBrief: mono dateline + big weekday title + stories·min·read
           + a segmented progress strip (one bar per story, filled when read). */
        <div className="mb-1">
          <div suppressHydrationWarning className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--ink-muted)]">
            {brief.dateline || " "}
          </div>
          <h1 suppressHydrationWarning className="mt-2 text-[30px] sm:text-[33px] font-extrabold tracking-[-0.035em] leading-[1.03] text-balance text-[var(--ink)]">
            {brief.weekday ? t(uiLang, "weekday_briefing", { weekday: brief.weekday }) : t(uiLang, "todays_briefing")}
          </h1>
          {events.length > 0 && briefingTotal > 0 && (
            <>
              <div suppressHydrationWarning className="mt-2.5 flex items-baseline gap-2 text-[12px] font-medium text-[var(--ink-muted)] tabular-nums">
                <span>{briefingTotal} {t(uiLang, briefingTotal === 1 ? "story_one" : "story_many")}</span>
                <span aria-hidden>·</span>
                <span>≈{briefingMins} {t(uiLang, "min_unit")}</span>
                <span aria-hidden>·</span>
                <span className="text-[var(--ink)] font-bold">{briefingRead} {t(uiLang, briefingRead === 1 ? "read_one" : "read_many")}</span>
              </div>
              <div className="mt-3.5 grid gap-[3px]" style={{ gridTemplateColumns: `repeat(${briefingTotal}, minmax(0,1fr))` }}>
                {briefingSet.map((ev) => (
                  <i key={ev.id} className="h-[3px]" style={{ background: readState(ev).read ? "var(--accent)" : "var(--border)" }} />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Browse: search (squared) + counted category rail-chips (isBrowse) ── */}
      {!briefing && !error && events.length > 0 && (
        <>
          <div className="flex items-center gap-2 border border-[var(--border)] bg-white px-3.5 py-2.5">
            <svg className="w-[15px] h-[15px] text-[var(--ink-muted)] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
            </svg>
            <input
              ref={searchRef}
              type="text"
              placeholder={t(uiLang, "search_events")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 min-w-0 border-0 outline-none text-[13.5px] font-medium text-[var(--ink)] bg-transparent"
            />
            {!!search.trim() && (
              <button
                onClick={() => setSearch("")}
                className="shrink-0 font-mono text-[10px] font-bold uppercase tracking-wide text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors"
              >
                {t(uiLang, "clear")}
              </button>
            )}
          </div>

          <div className="flex flex-wrap gap-1.5 mt-3.5">
            {availableCats.map((c) => {
              const active = activeCategory === c.key;
              const rail = c.key === "all" ? "transparent" : themeAccent(c.key);
              return (
                <button
                  key={c.key}
                  onClick={() => setCat(c.key)}
                  aria-pressed={active}
                  style={{ borderLeftColor: rail, borderLeftWidth: 3 }}
                  className={`text-[11px] font-bold px-2.5 py-[7px] border transition-colors ${
                    active
                      ? "bg-[var(--ink)] text-white border-[var(--ink)]"
                      : "bg-white text-[var(--ink)] border-[var(--border)] hover:border-gray-400"
                  }`}
                >
                  {categoryLabel(uiLang, c.key, c.label)}{" "}
                  <span className={`font-mono text-[10px] tabular-nums ${active ? "text-white/70" : "text-[var(--ink-muted)]"}`}>{catCount(c.key)}</span>
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* Outlook promo banner removed — the pulsing Outlook icon on the header
          line is the entry point now (Rams: one signal, no repeated card). */}

      {/* ── States ───────────────────────────────────────────────────────────── */}
      {error ? (
        <div className="rounded-xl border border-[var(--border)] bg-white px-6 py-10 text-center">
          <p className="text-2xl mb-3" aria-hidden>📰</p>
          <p className="text-sm font-semibold mb-1">{t(uiLang, "feed_error")}</p>
          <p className="text-xs text-[var(--ink-muted)] mb-5 max-w-xs mx-auto">{error}</p>
          <RetryButton />
        </div>

      ) : events.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border)] px-5 py-10 text-center text-sm text-[var(--ink-muted)]">
          {t(uiLang, "no_events")}
          <span className="block mt-1 text-xs opacity-70">Run Curator with real API keys to generate pages.</span>
        </div>

      ) : filtered.length === 0 ? (
        <div className="py-12 text-center">
          <div className="text-[15px] font-bold tracking-tight">{t(uiLang, "browse_empty_title")}</div>
          <p className="mt-1.5 text-[12.5px] leading-relaxed text-[var(--ink-muted)] max-w-[36ch] mx-auto">{t(uiLang, "browse_empty_body")}</p>
          <button onClick={clearAll} className="mt-3 text-xs underline text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors">
            {t(uiLang, "clear_filters")}
          </button>
        </div>

      ) : briefing ? (

          /* ── BRIEFING (Reader-prototype isBrief) — mono lists, no big cover ── */
          <div>
            {devSet.length > 0 && (
              <>
                <BriefSection label={t(uiLang, "developing_now")} count={devSet.length} accent />
                {devSet.map((ev) => (
                  <BriefRow key={ev.id} event={ev} showAvatars {...readState(ev)} />
                ))}
              </>
            )}

            {restSet.length > 0 && (
              <>
                <BriefSection label={t(uiLang, "the_briefing")} count={`${briefingLeft} ${t(uiLang, "left_count")}`} />
                {restSet.map((ev) => (
                  <BriefRow key={ev.id} event={ev} {...readState(ev)} />
                ))}
              </>
            )}

            {/* Today's Outlook — the day's lead editorial column */}
            {outlookLead && <div className="mt-5"><OutlookCard entry={outlookLead} /></div>}

            {/* Caught-up end-state + Browse-all */}
            <div className="mt-8 flex flex-col items-center gap-3 text-center">
              {briefingCaught && (
                <>
                  <span className="grid place-items-center w-11 h-11 rounded-full bg-[#16a34a] text-white text-xl font-bold" aria-hidden>✓</span>
                  <div className="text-[17px] font-bold tracking-tight">{t(uiLang, "caught_up")}</div>
                  <p className="text-[13px] text-[var(--ink-muted)] max-w-[28ch] leading-relaxed">
                    {t(uiLang, "caught_up_desc")}
                  </p>
                </>
              )}
              {events.length > briefingTotal && (
                <Link
                  href="/browse"
                  className="mt-1 inline-flex items-center gap-2 px-5 py-2.5 border border-[var(--ink)] rounded-full text-[13px] font-semibold hover:bg-[var(--ink)] hover:text-white transition-colors"
                >
                  {t(uiLang, "browse_all")}
                </Link>
              )}
            </div>
          </div>

        ) : (

        /* ── BROWSE LIST (prototype isBrowse): ALL STORIES · NEWEST FIRST +
             a flat rail-card list (BriefRow). Filtered results, freshness order. */
        <>
          <div className="flex items-center gap-2 mt-5 pb-1.5 border-b-2 border-[var(--ink)]">
            <span className="font-mono text-[11px] font-bold uppercase tracking-[0.12em]">{browseHeading}</span>
            <span className="ml-auto font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--ink-muted)]">{t(uiLang, "newest_first")}</span>
          </div>
          {sorted.map((ev) => (
            <BriefRow key={ev.id} event={ev} {...readState(ev)} />
          ))}
        </>
      )}

    </div>
  );
}
