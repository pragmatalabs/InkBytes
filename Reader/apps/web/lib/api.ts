import type { EventSummary, EventPage } from "./types";

const BASE = process.env.CURATOR_API_URL ?? "http://localhost:8060";

async function apiFetch<T>(path: string, revalidate = 300): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate } });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export function getEvents(): Promise<EventSummary[]> {
  return apiFetch<EventSummary[]>("/events", 60);
}

export function getEvent(id: string): Promise<EventPage> {
  return apiFetch<EventPage>(`/events/${id}`, 300);
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
