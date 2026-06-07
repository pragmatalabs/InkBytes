"use client";

import { useState } from "react";

interface ShareButtonProps {
  title: string;
  text?: string;
}

export default function ShareButton({ title, text }: ShareButtonProps) {
  const [state, setState] = useState<"idle" | "copied" | "shared">("idle");

  async function handleShare() {
    const url = window.location.href;

    // Web Share API — available in most modern mobile browsers + Safari on desktop
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title, text: text ?? title, url });
        setState("shared");
        setTimeout(() => setState("idle"), 2000);
        return;
      } catch {
        // User cancelled or share failed — fall through to clipboard
      }
    }

    // Fallback: copy URL to clipboard
    try {
      await navigator.clipboard.writeText(url);
      setState("copied");
      setTimeout(() => setState("idle"), 2000);
    } catch {
      // Clipboard blocked (e.g. file:// protocol) — silent fail
    }
  }

  const label =
    state === "copied" ? "Copied!" :
    state === "shared" ? "Shared!" :
    "Share";

  return (
    <button
      onClick={handleShare}
      aria-label="Share this story"
      className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border transition-all ${
        state !== "idle"
          ? "border-green-300 bg-green-50 text-green-700"
          : "border-[var(--border)] text-[var(--ink-muted)] hover:border-gray-400 hover:text-[var(--ink)] hover:bg-gray-50"
      }`}
    >
      {state !== "idle" ? (
        /* Checkmark when done */
        <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        /* Share icon */
        <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="18" cy="5" r="3" />
          <circle cx="6" cy="12" r="3" />
          <circle cx="18" cy="19" r="3" />
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
        </svg>
      )}
      {label}
    </button>
  );
}
