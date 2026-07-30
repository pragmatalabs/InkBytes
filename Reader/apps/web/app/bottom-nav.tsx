"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NewspaperIcon, SearchIcon, NetworkIcon, OutlookIcon } from "@/components/icons";
import { useLang } from "@/lib/prefs";
import { t } from "@/lib/i18n";

// ── Nav item ───────────────────────────────────────────────────────────────────

interface NavItem {
  href: string;
  labelKey: "nav_brief" | "nav_outlook" | "nav_browse" | "nav_entities";
  /** Icon component — receives a className string with sizing + color */
  icon: React.ComponentType<{ className?: string }>;
}

// ── Bottom Nav (Reader-prototype model: Brief · Outlook · Browse · Entities) ────
// Saved + Settings + About live in the ☰ hamburger drawer (NavMenu) now, not the
// tab bar — matching InkBytes Reader.dc.html.

export default function BottomNav() {
  const pathname = usePathname();
  const lang = useLang();

  const items: NavItem[] = [
    { href: "/",         labelKey: "nav_brief",    icon: NewspaperIcon },
    { href: "/outlook",  labelKey: "nav_outlook",  icon: OutlookIcon },
    { href: "/browse",   labelKey: "nav_browse",   icon: SearchIcon },
    { href: "/entities", labelKey: "nav_entities", icon: NetworkIcon },
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
        {items.map(({ href, labelKey, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex flex-col items-center justify-center flex-1 gap-0.5 text-[10px] font-semibold uppercase tracking-widest transition-colors select-none rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)] ${
                active ? "text-[var(--accent)]" : "text-[var(--ink-muted)] hover:text-[var(--ink)]"
              }`}
            >
              <Icon className={`w-6 h-6 transition-opacity ${active ? "opacity-100" : "opacity-60"}`} />
              <span>{t(lang, labelKey)}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
