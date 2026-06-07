"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

// ── SVG icons ──────────────────────────────────────────────────────────────────
// All drawn on a 24×24 viewBox, 2px stroke, no fill — keeps them sharp at small sizes.

function IconHome({ active }: { active: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill={active ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={active ? 0 : 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-6 h-6"
    >
      {active ? (
        <>
          <path d="M3 12L12 4l9 8v9a1 1 0 0 1-1 1H15v-5h-6v5H4a1 1 0 0 1-1-1z" />
        </>
      ) : (
        <>
          <path d="M3 12L12 4l9 8v9a1 1 0 0 1-1 1H15v-5h-6v5H4a1 1 0 0 1-1-1z" />
        </>
      )}
    </svg>
  );
}

function IconSearch({ active }: { active: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={active ? 2.5 : 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-6 h-6"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

function IconEntities({ active }: { active: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={active ? 2.5 : 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-6 h-6"
    >
      <circle cx="5" cy="6" r="2.4" />
      <circle cx="19" cy="7" r="2.4" />
      <circle cx="12" cy="18" r="2.4" />
      <path d="M7 7 17 7M6.5 8 11 16M17.5 9 13 16" />
    </svg>
  );
}

function IconAbout({ active }: { active: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={active ? 2.5 : 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-6 h-6"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="8" strokeWidth="3" strokeLinecap="round" />
      <path d="M12 11v5" />
    </svg>
  );
}

// ── Nav item ───────────────────────────────────────────────────────────────────

interface NavItem {
  href: string;
  label: string;
  icon: (a: { active: boolean }) => React.ReactNode;
  /** If set, tap triggers this action instead of navigating (when already on the target path) */
  onActiveTap?: () => void;
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
    { href: "/",          label: "News",     icon: IconHome },
    { href: "/?search=1", label: "Search",   icon: IconSearch },
    { href: "/entities",  label: "Entities", icon: IconEntities },
    { href: "/about",     label: "About",    icon: IconAbout },
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
              <Icon active={active} />
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
