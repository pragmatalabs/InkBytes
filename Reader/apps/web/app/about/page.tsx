import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About",
  description:
    "InkBytes is a paid, ad-free news reader. Each event — a real-world development covered by multiple outlets — gets one elegant, source-cited page.",
  openGraph: { title: "About InkBytes", type: "website" },
};

export default function AboutPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <Link href="/" className="text-sm text-[var(--ink-muted)] hover:text-[var(--ink)] mb-8 inline-block">
        ← Back
      </Link>
      <h1 className="text-2xl font-bold tracking-tight mb-6">About InkBytes</h1>
      <div className="space-y-5 text-[15px] leading-relaxed text-[var(--ink)]">
        <p>
          InkBytes is a paid, ad-free news reader. Each <em>event</em> — a real-world
          development covered by multiple outlets — gets one elegant page.
        </p>
        <p>
          We scrape dozens of sources, group articles about the same story, and
          synthesize them into a short, cited brief. You get the substance without
          the noise.
        </p>
        <p>
          No ads. No tracking. No sponsored content. One flat monthly fee.
        </p>
        <div className="border-t border-[var(--border)] pt-5">
          <h2 className="font-semibold mb-2 text-sm uppercase tracking-wider text-[var(--ink-muted)]">
            How it works
          </h2>
          <ol className="list-decimal list-inside space-y-2 text-sm text-[var(--ink-muted)]">
            <li><strong className="text-[var(--ink)]">Messor</strong> harvests articles from 25+ outlets every 60 minutes.</li>
            <li><strong className="text-[var(--ink)]">Curator</strong> groups same-event articles using embeddings, then synthesizes a 200-word brief with inline source citations.</li>
            <li><strong className="text-[var(--ink)]">Reader</strong> (you&apos;re here) shows the top events, freshest first.</li>
          </ol>
        </div>
        <p className="text-sm text-[var(--ink-muted)]">
          Built in the Dominican Republic. LATAM + global English coverage.
        </p>

        {/* Founder signature */}
        <div className="border-t border-[var(--border)] pt-8">
          <Image
            src="/signature.png"
            alt="Julian De La Rosa"
            width={260}
            height={87}
            className="select-none"
            priority
          />
          <p className="text-xs text-[var(--ink-muted)] -mt-1">
            Julian De La Rosa &mdash; Founder
          </p>
        </div>
      </div>
    </div>
  );
}
