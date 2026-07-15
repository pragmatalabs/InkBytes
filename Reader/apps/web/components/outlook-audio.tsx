"use client";

import { useEffect, useRef, useState } from "react";

/** Minimal spoken-word player for an editorial column (self-hosted Piper TTS,
 *  ADR-0009). A single accent play/pause control + a thin scrubbable progress
 *  track. `preload="none"` so the MP3 is only fetched once the reader hits play.
 *  The src is already language-correct (the page fetches per-lang). */
export default function OutlookAudio({
  src, lang, accent,
}: { src: string; lang: string; accent: string }) {
  const ref = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [dur, setDur] = useState(0);
  const [cur, setCur] = useState(0);

  const es = lang === "es";
  const pct = dur > 0 ? (cur / dur) * 100 : 0;

  useEffect(() => {
    // Reset when the source changes (language/date switch).
    setPlaying(false); setLoading(false); setDur(0); setCur(0);
  }, [src]);

  const toggle = () => {
    const a = ref.current;
    if (!a) return;
    if (a.paused) {
      if (!a.readyState) setLoading(true);
      a.play().catch(() => setLoading(false));
    } else {
      a.pause();
    }
  };

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    const a = ref.current;
    if (!a || !dur) return;
    const rect = e.currentTarget.getBoundingClientRect();
    a.currentTime = ((e.clientX - rect.left) / rect.width) * dur;
  };

  const fmt = (s: number) =>
    Number.isFinite(s) ? `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}` : "–:--";

  return (
    <div className="flex items-center gap-3 rounded-full border border-[var(--border)] bg-white pl-1.5 pr-4 py-1.5 print:hidden">
      <button
        type="button"
        onClick={toggle}
        aria-label={playing ? (es ? "Pausar" : "Pause") : (es ? "Escuchar la columna" : "Listen to this column")}
        className="grid place-items-center w-9 h-9 rounded-full text-white shrink-0 transition-transform active:scale-95"
        style={{ background: accent }}
      >
        {loading && !playing ? (
          <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M21 12a9 9 0 1 1-6.2-8.5" strokeLinecap="round" />
          </svg>
        ) : playing ? (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
        ) : (
          <svg className="w-4 h-4 translate-x-[1px]" viewBox="0 0 24 24" fill="currentColor"><path d="M7 5.5v13a1 1 0 0 0 1.5.87l11-6.5a1 1 0 0 0 0-1.74l-11-6.5A1 1 0 0 0 7 5.5Z" /></svg>
        )}
      </button>

      <div className="min-w-0 flex-1">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--ink-muted)] mb-1">
          {es ? "Escuchar" : "Listen"}
          {dur > 0 && <span className="ml-2 tabular-nums font-normal normal-case tracking-normal">{fmt(cur)} / {fmt(dur)}</span>}
        </div>
        <div
          onClick={seek}
          className="h-1 rounded-full bg-[var(--border)] cursor-pointer overflow-hidden"
          role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}
        >
          <div className="h-full rounded-full transition-[width] duration-150" style={{ width: `${pct}%`, background: accent }} />
        </div>
      </div>

      <audio
        ref={ref}
        src={src}
        preload="none"
        onPlaying={() => { setPlaying(true); setLoading(false); }}
        onPause={() => setPlaying(false)}
        onWaiting={() => setLoading(true)}
        onLoadedMetadata={(e) => setDur(e.currentTarget.duration)}
        onTimeUpdate={(e) => setCur(e.currentTarget.currentTime)}
        onEnded={() => { setPlaying(false); setCur(0); }}
      />
    </div>
  );
}
