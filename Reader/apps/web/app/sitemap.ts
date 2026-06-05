import type { MetadataRoute } from "next";

export const revalidate = 3600;

const BASE = process.env.NEXT_PUBLIC_BASE_URL ?? "https://inkbytes.app";
const CURATOR = process.env.CURATOR_API_URL ?? "http://localhost:8060";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: BASE,               lastModified: now, changeFrequency: "hourly",  priority: 1.0 },
    { url: `${BASE}/about`,    lastModified: now, changeFrequency: "monthly", priority: 0.3 },
    { url: `${BASE}/entities`, lastModified: now, changeFrequency: "daily",   priority: 0.5 },
  ];

  try {
    const events = await fetch(`${CURATOR}/events?limit=200`, {
      next: { revalidate: 3600 },
    }).then((r) => r.json()) as Array<{ id: string; freshness_at: string }>;

    const eventRoutes: MetadataRoute.Sitemap = events.map((e) => ({
      url: `${BASE}/event/${e.id}`,
      lastModified: new Date(e.freshness_at),
      changeFrequency: "daily",
      priority: 0.8,
    }));

    return [...staticRoutes, ...eventRoutes];
  } catch {
    return staticRoutes;
  }
}
