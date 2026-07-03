"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { NewspaperIcon, SearchIcon, NetworkIcon, InfoIcon, OutlookIcon } from "@/components/icons";

// ── Nav item ───────────────────────────────────────────────────────────────────

interface NavItem {
  href: string;
  label: string;
  /** Icon component — receives a className string with sizing + color */
  icon: React.ComponentType<{ className?: string }>;
}

// ── Bottom Nav ─────────────────────────────────────────────────────────────────

export default function BottomNav() {
  const pathname = usePathname();
  const router   = useRouter();

  // Tapping Search when already on "/" focuses the search input instead of
  // navigating, giving a native "tap-to-search" feel on the home screen.
  function handleSearchTap(e: React.MouseEvent) {
    if (pathname === "/") {
      e.preventDefault();
      const input = document.querySelector<HTMLInputElement>('input[type="text"]');
      if (input) {
        input.focus();
        input.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    } else {
      router.push("/?search=1");
    }
  }

  const items: NavItem[] = [
    { href: "/",          label: "News",     icon: NewspaperIcon },
    { href: "/outlook",   label: "Outlook",  icon: OutlookIcon },
    { href: "/?search=1", label: "Search",   icon: SearchIcon },
    { href: "/entities",  label: "Entities", icon: NetworkIcon },
    { href: "/about",     label: "About",    icon: InfoIcon },
  ];

  // Active detection: "/" matches only the exact root; others match prefix.
  function isActive(href: string) {
    if (href === "/" || href === "/?search=1") return pathname === "/";
    return pathname.startsWith(href);
  }

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
          const isSearch = label === "Search";

          return (
            <Link
              key={label}
              href={href}
              onClick={isSearch ? handleSearchTap : undefined}
              aria-current={active ? "page" : undefined}
              className={`flex flex-col items-center justify-center flex-1 gap-0.5 text-[10px] font-semibold uppercase tracking-widest transition-colors select-none ${
                active
                  ? "text-[var(--accent)]"
                  : "text-[var(--ink-muted)] hover:text-[var(--ink)]"
              }`}
            >
              {/* Icon inherits color via currentColor; size fixed at 24px */}
              <Icon className={`w-6 h-6 transition-opacity ${active ? "opacity-100" : "opacity-60"}`} />
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
