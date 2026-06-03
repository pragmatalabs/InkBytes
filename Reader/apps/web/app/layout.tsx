import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "InkBytes", template: "%s — InkBytes" },
  description: "One elegant page per event. Multi-source, ad-free.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col">
        <header className="border-b border-[var(--border)] bg-[var(--accent)]">
          <div className="max-w-4xl mx-auto px-4 h-12 flex items-center justify-between">
            <Link href="/" className="text-white font-semibold tracking-tight text-lg">
              InkBytes
            </Link>
            <nav className="flex gap-5 text-sm text-white/70">
              <Link href="/" className="hover:text-white transition-colors">News</Link>
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
