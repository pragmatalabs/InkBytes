import type { Metadata, Viewport } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import BottomNav from "./bottom-nav";
import { LogoMark } from "@/components/logo";
import PwaInstallBanner from "@/components/pwa-install-banner";
import ChatAssistant from "@/components/chat-assistant";
import Analytics from "@/components/analytics";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

// Event synthesis body (prototype): Source Serif 4 for long reading, paired with
// the Inter drop cap. Same next/font/google setup as Inter.
const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
  display: "swap",
});

// Fallback must be the LIVE domain: metadataBase makes og:image/twitter:image
// absolute, and unfurlers fetch that URL — inkbytes.app does not resolve, so
// the old fallback pointed every share card at a dead host (2026-07-12).
const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL ?? "https://inkbytes.org";

// viewport-fit=cover lets the content reach the edges of the screen on iPhones
// with notch/home indicator — critical for the bottom nav safe-area treatment.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#1a1a2e",
};

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
    // summary_large_image: unfurls show the branded card (app/opengraph-image.png),
    // not a favicon fallback — icons/OG were create-next-app defaults until
    // 2026-07-12 (shares rendered the Vercel mark).
    card: "summary_large_image",
    site: "@inkbytes",
  },
  robots: { index: true, follow: true },
  // iOS PWA — makes "Add to Home Screen" work as a proper full-screen app
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "InkBytes",
  },
  applicationName: "InkBytes",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`h-full ${inter.variable} ${sourceSerif.variable}`}>
      <body className="min-h-full flex flex-col">
        <header className="bg-[var(--accent)] sticky top-0 z-40 border-b border-white/10 safe-top">
          <div className="max-w-4xl mx-auto px-4 h-13 flex items-center justify-between gap-4">
            <Link
              href="/"
              className="flex items-center gap-2.5 shrink-0 hover:opacity-90 transition-opacity"
              aria-label="InkBytes — home"
            >
              <LogoMark className="h-6 w-auto text-white" />
              <span className="text-white font-bold tracking-tight text-lg leading-none">
                InkBytes<span className="text-[var(--accent-dot)]">.</span>
              </span>
            </Link>

            {/* Search moved into the content top row (one search, not two —
                the header pill duplicated it). Header stays brand + nav. */}

            <div className="flex items-center gap-4 shrink-0">
              {/* Top nav is DESKTOP-only: on mobile the bottom tab bar is the nav,
                  so a second copy here is pure redundancy (Rams — remove it). */}
              <nav className="hidden sm:flex items-center gap-4 text-sm text-white/70">
                <Link href="/" className="hover:text-white transition-colors font-medium">Briefing</Link>
                <Link href="/browse" className="hover:text-white transition-colors">Browse</Link>
                <Link href="/outlook" className="hover:text-white transition-colors">Outlook</Link>
                <Link href="/entities" className="hover:text-white transition-colors">Entities</Link>
              </nav>

              {/* Saved + You — entry points for the Slice B screens. Always
                  visible (the bottom nav has no room until the Slice C rework). */}
              <div className="flex items-center gap-0.5">
                <Link href="/saved" aria-label="Saved" className="p-1.5 text-white/70 hover:text-white transition-colors">
                  <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                  </svg>
                </Link>
                <Link href="/you" aria-label="You" className="p-1.5 text-white/70 hover:text-white transition-colors">
                  <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="8" r="3.5" /><path d="M5 20c0-3.5 3.1-6 7-6s7 2.5 7 6" />
                  </svg>
                </Link>
              </div>
            </div>
          </div>
        </header>

        {/*
          On mobile the bottom nav (58px) + iOS safe-area-inset-bottom sits at
          the base of the viewport. We push the main content up by that same
          amount so the last line of text is never hidden under the nav bar.
          The bottom-nav-spacer class (defined in globals.css) is md:hidden so
          on desktop nothing extra is added.
        */}
        <main className="flex-1">
          {children}
          {/* Mobile-only spacer — height matches the bottom nav + safe area */}
          <div className="bottom-nav-spacer md:hidden" aria-hidden="true" />
        </main>

        {/* Corpus chat assistant — floating button + overlay (ADR-0022) */}
        <ChatAssistant />

        {/* PWA install prompt — Android (beforeinstallprompt) + iOS (manual) */}
        <PwaInstallBanner />

        {/* Bottom nav — only visible on mobile (md:hidden inside component) */}
        <BottomNav />

        {/* Self-hosted Umami analytics (privacy-first, cookieless). Inert until
            UMAMI_SRC + UMAMI_WEBSITE_ID are set in the Reader's runtime env. */}
        <Analytics />

        <footer className="hidden md:block border-t border-[var(--border)] py-6 text-center text-xs text-[var(--ink-muted)]">
          InkBytes · paid, ad-free · one page per event
        </footer>
      </body>
    </html>
  );
}
