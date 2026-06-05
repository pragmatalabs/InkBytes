import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL ?? "https://inkbytes.app";

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  title: { default: "InkBytes", template: "%s — InkBytes" },
  description:
    "One elegant page per event. Multi-source, ad-free news — synthesized from dozens of outlets, cited and noise-free.",
  openGraph: {
    siteName: "InkBytes",
    type: "website",
    locale: "en_US",
    url: BASE_URL,
  },
  twitter: {
    card: "summary",
    site: "@inkbytes",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`h-full ${inter.variable}`}>
      <body className="min-h-full flex flex-col">
        <header className="bg-[var(--accent)] sticky top-0 z-40 border-b border-white/10">
          <div className="max-w-4xl mx-auto px-4 h-13 flex items-center justify-between gap-4">
            <Link
              href="/"
              className="text-white font-bold tracking-tight text-lg shrink-0 flex items-center gap-0.5"
            >
              InkBytes<span className="text-[var(--accent-dot)]">.</span>
            </Link>

            <Link
              href="/?search=1"
              className="hidden sm:flex flex-1 max-w-xs items-center gap-2 bg-white/10 hover:bg-white/15 transition-colors rounded-full px-3.5 py-1.5 text-sm text-white/60"
            >
              <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
              </svg>
              Search events
            </Link>

            <nav className="flex items-center gap-4 text-sm text-white/70 shrink-0">
              <Link href="/" className="hover:text-white transition-colors font-medium">News</Link>
              <Link href="/#topics" className="hover:text-white transition-colors">Topics</Link>
              <Link href="/about" className="hover:text-white transition-colors">About</Link>
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-[var(--border)] py-6 text-center text-xs text-[var(--ink-muted)]">
          InkBytes · paid, ad-free · one page per event
        </footer>
      </body>
    </html>
  );
}
