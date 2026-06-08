"use client";

/**
 * PwaInstallBanner
 *
 * Shows a bottom banner prompting mobile users to add InkBytes to their home
 * screen.  Two paths:
 *
 *  Android / Chrome  — intercepts `beforeinstallprompt`, shows an Install button
 *                      that triggers the native prompt.
 *
 *  iOS / Safari      — `beforeinstallprompt` never fires; detects iOS + non-
 *                      standalone and shows manual Share → "Add to Home Screen"
 *                      instructions.
 *
 * Rules:
 *  • Never shown if already running in standalone (PWA already installed).
 *  • Dismissed state persisted in localStorage — never shown again after close.
 *  • Appears after a 3 s delay so it doesn't interrupt page load.
 *  • Hidden on md+ (desktop handles its own install via browser chrome).
 */

import { useEffect, useState } from "react";
import Image from "next/image";

const STORAGE_KEY = "inkbytes-pwa-dismissed";

type Platform = "android" | "ios" | null;

// Safari on iOS exposes navigator.standalone; cast to avoid TS error.
declare global {
  interface Navigator {
    standalone?: boolean;
  }
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

function detectPlatform(): Platform {
  if (typeof window === "undefined") return null;
  const ua = navigator.userAgent;
  if (/iPhone|iPad|iPod/.test(ua) && !/Windows Phone/.test(ua)) return "ios";
  // Android / Chrome triggers beforeinstallprompt — handled separately.
  return null;
}

// Share icon — same shape as iOS Share button
function ShareIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" className="inline w-4 h-4 mx-0.5 translate-y-[-1px]">
      <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>
      <polyline points="16 6 12 2 8 6"/>
      <line x1="12" y1="2" x2="12" y2="15"/>
    </svg>
  );
}

export default function PwaInstallBanner() {
  const [platform, setPlatform] = useState<Platform>(null);
  const [visible, setVisible] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);

  useEffect(() => {
    // Already installed or user previously dismissed → bail out
    if (isStandalone()) return;
    if (localStorage.getItem(STORAGE_KEY)) return;

    // Android: capture the browser install prompt
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handler = (e: any) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setPlatform("android");
      setTimeout(() => setVisible(true), 3000);
    };
    window.addEventListener("beforeinstallprompt", handler);

    // iOS: show manual instructions after a short delay
    const ios = detectPlatform();
    if (ios === "ios") {
      setPlatform("ios");
      setTimeout(() => setVisible(true), 3000);
    }

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  function dismiss() {
    setVisible(false);
    localStorage.setItem(STORAGE_KEY, "1");
  }

  async function install() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setVisible(false);
    }
    setDeferredPrompt(null);
  }

  if (!visible || !platform) return null;

  return (
    /* Positioned above the bottom nav (58px) + iOS safe-area-inset-bottom.
       Only shown on mobile screens (hidden md+). */
    <div
      className="
        fixed left-0 right-0 z-50
        md:hidden
        animate-slide-up
      "
      style={{ bottom: "calc(58px + env(safe-area-inset-bottom, 0px))" }}
      role="banner"
      aria-label="Add to home screen"
    >
      <div className="mx-3 mb-2 rounded-2xl bg-[var(--accent)] text-white shadow-xl border border-white/10 px-4 py-3.5">
        <div className="flex items-start gap-3">
          {/* App icon */}
          <Image
            src="/icon-192.png"
            alt="InkBytes"
            width={44}
            height={44}
            className="rounded-xl shrink-0 mt-0.5"
          />

          {/* Text + actions */}
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-sm leading-tight">
              Add InkBytes to your home screen
            </p>

            {platform === "ios" ? (
              <p className="text-xs text-white/70 mt-1 leading-snug">
                Tap <ShareIcon /> then{" "}
                <span className="text-white font-medium">"Add to Home Screen"</span>{" "}
                for the full app experience.
              </p>
            ) : (
              <p className="text-xs text-white/70 mt-1">
                Fast, offline-ready, no browser chrome.
              </p>
            )}

            {platform === "android" && (
              <button
                onClick={install}
                className="mt-2.5 bg-white text-[var(--accent)] text-xs font-semibold rounded-full px-4 py-1.5 hover:bg-white/90 transition-colors"
              >
                Install
              </button>
            )}
          </div>

          {/* Dismiss */}
          <button
            onClick={dismiss}
            aria-label="Dismiss"
            className="shrink-0 text-white/50 hover:text-white/90 transition-colors p-1 -mr-1 -mt-1"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
              strokeLinecap="round" className="w-4 h-4">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
