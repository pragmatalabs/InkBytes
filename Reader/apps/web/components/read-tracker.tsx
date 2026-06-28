"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    umami?: { track?: (name: string, data?: Record<string, unknown>) => void };
  }
}

/**
 * Content-engagement tracking for an event page (Umami custom events):
 *   - "event-read"  fired once on open — which event/category/language was read
 *   - "read-depth"  fired at 25/50/75/100% scroll milestones — how deeply
 *
 * No-ops when Umami isn't loaded (window.umami undefined), so it's safe before
 * analytics is configured and on any ad-blocked client. Renders nothing.
 */
export default function ReadTracker({
  eventId, category, language,
}: { eventId: string; category?: string | null; language?: string | null }) {
  useEffect(() => {
    window.umami?.track?.("event-read", { event_id: eventId, category, language });

    const milestones = [25, 50, 75, 100];
    const fired = new Set<number>();
    const onScroll = () => {
      const el = document.documentElement;
      const max = el.scrollHeight - el.clientHeight;
      if (max <= 0) return;
      const pct = Math.round((el.scrollTop / max) * 100);
      for (const m of milestones) {
        if (pct >= m && !fired.has(m)) {
          fired.add(m);
          window.umami?.track?.("read-depth", { event_id: eventId, depth: m });
        }
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [eventId, category, language]);

  return null;
}
