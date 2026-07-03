import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
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

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL ?? "https://inkbytes.app";

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
    card: "summary",
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
    <html lang="en" className={`h-full ${inter.variable}`}>
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
              <Link href="/outlook" className="hover:text-white transition-colors">Outlook</Link>
              <Link href="/entities" className="hover:text-white transition-colors">Entities</Link>
              <Link href="/about" className="hover:text-white transition-colors">About</Link>
            </nav>
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
