import type { Metadata } from "next";
import Link from "next/link";
import { getGraph } from "@/lib/api";
import GraphClient from "./graph-client";

export const revalidate = 120; // graph refreshes every 2 minutes

export const metadata: Metadata = {
  title: "Entity Graph",
  description:
    "Navigate the news by who and what — places, people, organisations, and topics linked across events.",
  openGraph: { title: "Entity Graph — InkBytes", type: "website" },
};

export default async function EntitiesPage() {
  let data;
  try {
    data = await getGraph();
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

  return <GraphClient data={data} />;
}
