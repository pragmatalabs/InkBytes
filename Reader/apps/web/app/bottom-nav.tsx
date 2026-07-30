"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NewspaperIcon, SearchIcon, NetworkIcon, OutlookIcon } from "@/components/icons";

// ── Nav item ───────────────────────────────────────────────────────────────────

interface NavItem {
  href: string;
  label: string;
  /** Icon component — receives a className string with sizing + color */
  icon: React.ComponentType<{ className?: string }>;
}

// ── Bottom Nav (Reader-prototype model: Brief · Outlook · Browse · Entities) ────
// Saved + Settings + About live in the ☰ hamburger drawer (NavMenu) now, not the
// tab bar — matching InkBytes Reader.dc.html.

export default function BottomNav() {
  const pathname = usePathname();

  const items: NavItem[] = [
    { href: "/",         label: "Brief",    icon: NewspaperIcon },
    { href: "/outlook",  label: "Outlook",  icon: OutlookIcon },
    { href: "/browse",   label: "Browse",   icon: SearchIcon },
    { href: "/entities", label: "Entities", icon: NetworkIcon },
  ];

  // Which top-level tab owns the current route. Detail routes map back to a tab
  // so the bar doesn't go dark. Event pages sit under Brief (where most reading
  // starts). Menu pages (Saved / You / About) own no tab — the ☰ menu owns them.
  const SECTION: [RegExp, string][] = [
    [/^\/event\//, "/"],
    [/^\/outlook/, "/outlook"],
    [/^\/browse/, "/browse"],
    [/^\/entities/, "/entities"],
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
