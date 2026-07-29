"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NewspaperIcon, SearchIcon } from "@/components/icons";

// ── Nav item ───────────────────────────────────────────────────────────────────

interface NavItem {
  href: string;
  label: string;
  /** Icon component — receives a className string with sizing + color */
  icon: React.ComponentType<{ className?: string }>;
}

// Bookmark + person glyphs (match the header icons in layout.tsx).
function BookmarkIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </svg>
  );
}
function PersonIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="3.5" /><path d="M5 20c0-3.5 3.1-6 7-6s7 2.5 7 6" />
    </svg>
  );
}

// ── Bottom Nav (Slice C-B: Briefing · Browse · Saved · You) ─────────────────────
// Outlook + Entities are reached from Browse; About from You.

export default function BottomNav() {
  const pathname = usePathname();

  const items: NavItem[] = [
    { href: "/",       label: "Briefing", icon: NewspaperIcon },
    { href: "/browse", label: "Browse",   icon: SearchIcon },
    { href: "/saved",  label: "Saved",    icon: BookmarkIcon },
    { href: "/you",    label: "You",      icon: PersonIcon },
  ];

  // Which top-level tab owns the current route. Detail routes map back to a tab
  // so the bar doesn't go dark. Event pages sit under Briefing (where most
  // reading starts); Outlook + Entities are Browse's territory now.
  const SECTION: [RegExp, string][] = [
    [/^\/event\//, "/"],
    [/^\/browse/, "/browse"],
    [/^\/outlook/, "/browse"],
    [/^\/entities/, "/browse"],
    [/^\/saved/, "/saved"],
    [/^\/you/, "/you"],
    [/^\/about/, "/you"],
  ];
  const section = SECTION.find(([re]) => re.test(pathname))?.[1] ?? pathname;

  const isActive = (href: string) => (href === "/" ? section === "/" : section.startsWith(href));

  return (
    /* md:hidden — on desktop the header nav is sufficient */
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-white border-t border-[var(--border)]"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      aria-label="Main navigation"
    >
      <div className="flex items-stretch h-[58px]">
        {items.map(({ href, label, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={label}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex flex-col items-center justify-center flex-1 gap-0.5 text-[10px] font-semibold uppercase tracking-widest transition-colors select-none rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)] ${
                active ? "text-[var(--accent)]" : "text-[var(--ink-muted)] hover:text-[var(--ink)]"
              }`}
            >
              <Icon className={`w-6 h-6 transition-opacity ${active ? "opacity-100" : "opacity-60"}`} />
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
