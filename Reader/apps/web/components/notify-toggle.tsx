"use client";

import { useEffect, useState } from "react";

/**
 * "Daily Outlook ready" push opt-in (ADR-R-0012).
 *
 * The iOS constraint drives the UX: Web Push only exists in an INSTALLED PWA on
 * iOS (no PushManager in a Safari tab). So we key off capability —
 * `PushManager`/`Notification`/`serviceWorker` present:
 *   - capable + granted/default → the toggle (subscribe/unsubscribe)
 *   - not capable (iOS Safari tab) → an "install to enable" hint
 *   - denied → a "blocked in settings" note
 * Curator owns VAPID + the store; this only drives the browser subscription and
 * proxies it through /api/push. Permission is requested on the tap, never load.
 */

const b64ToU8 = (b64: string) => {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const s = (b64 + pad).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(s);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
};

type State = "loading" | "unsupported" | "denied" | "off" | "on" | "busy";

export default function NotifyToggle({ lang = "es" }: { lang?: string }) {
  const [state, setState] = useState<State>("loading");
  const t = (es: string, en: string) => (lang === "en" ? en : es);

  useEffect(() => {
    const capable =
      typeof window !== "undefined" &&
      "serviceWorker" in navigator &&
      "PushManager" in window &&
      "Notification" in window;
    if (!capable) { setState("unsupported"); return; }
    if (Notification.permission === "denied") { setState("denied"); return; }
    (async () => {
      try {
        const reg = await navigator.serviceWorker.register("/sw.js");
        const sub = await reg.pushManager.getSubscription();
        setState(sub ? "on" : "off");
      } catch {
        setState("unsupported");
      }
    })();
  }, []);

  async function enable() {
    setState("busy");
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { setState(perm === "denied" ? "denied" : "off"); return; }
      const keyRes = await fetch("/api/push");
      const { publicKey } = await keyRes.json();
      if (!publicKey) { setState("off"); return; }
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: b64ToU8(publicKey),
      });
      await fetch("/api/push?op=subscribe", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          subscription: sub.toJSON(),
          topics: ["outlook-daily"],
          lang,
          userAgent: navigator.userAgent,
        }),
      });
      setState("on");
    } catch {
      setState("off");
    }
  }

  async function disable() {
    setState("busy");
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await fetch("/api/push?op=unsubscribe", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ endpoint: sub.endpoint }),
        });
        await sub.unsubscribe();
      }
      setState("off");
    } catch {
      setState("on");
    }
  }

  if (state === "loading") return null;

  const base = "inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors";

  if (state === "unsupported") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[11px] text-[var(--ink-muted)]">
        <BellIcon />
        {t("Instala InkBytes para recibir avisos", "Install InkBytes to get alerts")}
      </span>
    );
  }
  if (state === "denied") {
    return (
      <span className="inline-flex items-center gap-1.5 text-[11px] text-[var(--ink-muted)]">
        <BellOffIcon />
        {t("Notificaciones bloqueadas en ajustes", "Notifications blocked in settings")}
      </span>
    );
  }

  const on = state === "on";
  return (
    <button
      type="button"
      disabled={state === "busy"}
      onClick={on ? disable : enable}
      aria-pressed={on}
      className={`${base} ${
        on ? "border-[var(--accent)] bg-[var(--accent)] text-white"
           : "border-[var(--border)] bg-white hover:bg-gray-50 text-[var(--ink)]"
      } ${state === "busy" ? "opacity-60" : ""}`}
    >
      {on ? <BellIcon filled /> : <BellIcon />}
      {state === "busy"
        ? t("…", "…")
        : on
        ? t("Avisos activados", "Alerts on")
        : t("Avisarme cada día", "Notify me daily")}
    </button>
  );
}

function BellIcon({ filled = false }: { filled?: boolean }) {
  return (
    <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"}
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}
function BellOffIcon() {
  return (
    <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13.73 21a2 2 0 0 1-3.46 0M18.63 13A17.9 17.9 0 0 1 18 8M6.26 6.26A5.86 5.86 0 0 0 6 8c0 7-3 9-3 9h14M18 8a6 6 0 0 0-9.33-5" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}
