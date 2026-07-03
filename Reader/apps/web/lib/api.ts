import type { EventSummary, EventPage, RelatedEvent, GraphData, TrendingTopic,
  Outlook, OutlookTopic, OutlookArchiveEntry } from "./types";

const BASE = process.env.CURATOR_API_URL ?? "http://localhost:8060";

async function apiFetch<T>(path: string, revalidate = 300): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate } });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

/** Today's [Topic] Outlook — the daily editorial (ADR-0008). Returns an empty
 *  object when no edition exists yet (editorial service not run for that day). */
export function getOutlook(theme: string, lang = "es", date?: string): Promise<Outlook | Record<string, never>> {
  const q = new URLSearchParams({ theme, lang });
  if (date) q.set("date", date);
  return apiFetch<Outlook | Record<string, never>>(`/outlook?${q.toString()}`, 120);
}

/** Topics that have a published outlook edition — the /outlook index + nav. */
export function getOutlookAvailable(lang = "es"): Promise<{ topics: OutlookTopic[] }> {
  return apiFetch<{ topics: OutlookTopic[] }>(`/outlook/available?lang=${lang}`, 300);
}

/** Every edition over the last `days` days (newest first) — the date-grouped
 *  Outlook archive/timeline. The index page groups these by edition_date. */
export function getOutlookArchive(lang = "es", days = 14): Promise<{ editions: OutlookArchiveEntry[] }> {
  return apiFetch<{ editions: OutlookArchiveEntry[] }>(`/outlook/archive?lang=${lang}&days=${days}`, 300);
}

/** Entity co-occurrence graph data for /entities (ADR-0005 Approach A). */
export function getGraph(
  minEventCount = 2,
  limitNodes = 80,
  minEdgeWeight = 2,
  limitEdges = 250,
): Promise<GraphData> {
  return apiFetch<GraphData>(
    `/graph?min_event_count=${minEventCount}&limit_nodes=${limitNodes}&min_edge_weight=${minEdgeWeight}&limit_edges=${limitEdges}`,
    120, // revalidate every 2 min — graph changes as new events are published
  );
}

/** Related events by entity + topic overlap (ADR-0005, Approach A). */
export function getRelatedEvents(
  id: string,
  minScore = 0.4,
  limit = 5,
): Promise<RelatedEvent[]> {
  return apiFetch<RelatedEvent[]>(
    `/events/${id}/related?min_score=${minScore}&limit=${limit}`,
    300,
  );
}

export function getEvents(
  limit = 500,
  filters?: { theme?: string; topic?: string; category?: string },
): Promise<EventSummary[]> {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (filters?.theme)    qs.set("theme", filters.theme);
  if (filters?.topic)    qs.set("topic", filters.topic);
  if (filters?.category) qs.set("category", filters.category);
  return apiFetch<EventSummary[]>(`/events?${qs.toString()}`, 60);
}

export function getEvent(id: string): Promise<EventPage> {
  return apiFetch<EventPage>(`/events/${id}`, 300);
}

/** Trending story topics over the last `windowHours` (ADR-0027). */
export function getTrendingTopics(
  limit = 12,
  windowHours = 48,
): Promise<TrendingTopic[]> {
  return apiFetch<TrendingTopic[]>(
    `/topics/trending?limit=${limit}&window_hours=${windowHours}`,
    120, // revalidate every 2 min — trending shifts as new events publish
  );
}

export function getStatus(): Promise<{
  articles_total: number;
  articles_enriched: number;
  events_total: number;
  pages_published: number;
}> {
  return apiFetch("/status", 30);
}

export function getOutlets(): Promise<import("./types").Outlet[]> {
  return apiFetch("/outlets", 60);
}

export function parseJson<T>(value: T | string): T {
  if (typeof value === "string") return JSON.parse(value) as T;
  return value;
}

export function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 2) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/** Returns a Tailwind border-left color class based on content age. */
export function freshnessClass(iso: string): string {
  const h = (Date.now() - new Date(iso).getTime()) / 3_600_000;
  if (h < 1)  return "border-l-green-500";
  if (h < 6)  return "border-l-amber-400";
  if (h < 24) return "border-l-sky-400";
  return "border-l-gray-200";
}

/** Returns a small label for the freshness dot. */
export function freshnessLabel(iso: string): { label: string; color: string } {
  const h = (Date.now() - new Date(iso).getTime()) / 3_600_000;
  if (h < 1)  return { label: "NEW",  color: "text-green-600" };
  if (h < 6)  return { label: "LIVE", color: "text-amber-600" };
  return      { label: "",    color: "" };
}

/**
 * Event is "Developing" when its freshness is recent (within ~24h).
 * Tolerates small clock skew / freshness stamped at-or-slightly-ahead of now
 * (an event refreshed "now" should read as developing, not be excluded).
 */
export function isDeveloping(iso: string, withinHours = 24): boolean {
  const h = (Date.now() - new Date(iso).getTime()) / 3_600_000;
  return h > -24 && h < withinHours;
}

/** Builds a short outlet initials token from a source name (e.g. "AP News" → "AP"). */
export function outletInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}
