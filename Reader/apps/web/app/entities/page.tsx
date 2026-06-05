import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Entity Graph",
  description:
    "Navigate the news by who and what — places, people, organisations, and topics linked across events.",
  openGraph: { title: "Entity Graph — InkBytes", type: "website" },
};

export default function EntitiesPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-16 text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gray-100 mb-6">
        <svg className="w-6 h-6 text-[var(--ink-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="5" cy="6" r="2.4"/><circle cx="19" cy="7" r="2.4"/><circle cx="12" cy="18" r="2.4"/>
          <path d="M7 7 17 7M6.5 8 11 16M17.5 9 13 16"/>
        </svg>
      </div>
      <h1 className="text-xl font-bold tracking-tight mb-2">Entity Graph</h1>
      <p className="text-sm text-[var(--ink-muted)] max-w-xs mx-auto">
        Navigate the news by who &amp; what — places, people, orgs, and topics linked across events.
        Coming in R3.
      </p>
      <Link
        href="/"
        className="inline-block mt-8 text-sm text-[var(--accent)] underline hover:no-underline"
      >
        ← Back to events
      </Link>
    </div>
  );
}
