import type { Metadata } from "next";
import Link from "next/link";
import { getGraph } from "@/lib/api";
import EntitiesView from "./entities-view";

// Force SSR — the graph data comes from an internal service (inkbytes-curator-api)
// that is only resolvable at runtime inside the Docker network, not at build time.
// ISR would bake in the "could not reach" error state during docker build.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Entity Graph",
  description:
    "Navigate the news by who and what — places, people, organisations, and topics linked across events.",
  openGraph: { title: "Entity Graph — InkBytes", type: "website" },
};

// Per-node coverage cap. /graph ships every node's COMPLETE pages array —
// on prod that's 1,000+ entries for a top entity, ~5.5 MB of HTML once
// serialized twice (SSR + RSC payload). A phone chokes on the transfer and
// on rendering a thousand-row sheet ("entities aren't working on mobile",
// 2026-07-12). Trim to the freshest N per node BEFORE anything is serialized
// to the client; `event_count` still carries the true total for display.
const PAGES_PER_NODE = 15;

export default async function EntitiesPage() {
  let data;
  try {
    data = await getGraph();
    data = {
      ...data,
      nodes: data.nodes.map((n) => ({
        ...n,
        pages: [...n.pages]
          .sort((a, b) => new Date(b.freshness_at).getTime() - new Date(a.freshness_at).getTime())
          .slice(0, PAGES_PER_NODE),
      })),
    };
  } catch {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h1 className="text-xl font-bold tracking-tight mb-2">Entity Graph</h1>
        <p className="text-sm text-[var(--ink-muted)] max-w-xs mx-auto">
          Could not reach the Curator service. Make sure it is running on port 8060.
        </p>
        <Link href="/" className="inline-block mt-8 text-sm text-[var(--accent)] underline hover:no-underline">
          ← Back to events
        </Link>
      </div>
    );
  }

  if (!data.nodes.length) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h1 className="text-xl font-bold tracking-tight mb-2">Entity Graph</h1>
        <p className="text-sm text-[var(--ink-muted)] max-w-xs mx-auto">
          No entities yet — publish some events first and they will appear here.
        </p>
        <Link href="/" className="inline-block mt-8 text-sm text-[var(--accent)] underline hover:no-underline">
          ← Back to events
        </Link>
      </div>
    );
  }

  return <EntitiesView data={data} />;
}
