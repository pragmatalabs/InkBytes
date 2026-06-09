"use client";

/**
 * ChatAssistant (ADR-0022)
 *
 * A discrete, always-on floating round button that opens a full-screen overlay.
 * The assistant answers ONLY from published InkBytes events — quick-action chips
 * for daily digests ("Today", "Top 10 Tech", "Top 10 World") plus a free-form
 * box. Answers cite sources as [n]; each citation links to its /event/{id} page.
 *
 * Talks to POST /api/ask (which proxies to the Curator /ask endpoint).
 */

import { useState, useRef, useEffect } from "react";
import Link from "next/link";

interface Source {
  n: number;
  title: string;
  url: string;
  outlet?: string;
}
interface AskResponse {
  answer_md: string;
  sources: Source[];
  error?: string;
}

type Mode = "resume" | "top10" | "chat";

const QUICK_ACTIONS: { label: string; mode: Mode; question: string }[] = [
  { label: "Today", mode: "resume", question: "" },
  { label: "Top 10 Tech", mode: "top10", question: "Top 10 items to consider in technology today" },
  { label: "Top 10 World", mode: "top10", question: "Top 10 world news items to consider today" },
  { label: "Top 10 Business", mode: "top10", question: "Top 10 business and markets items today" },
];

// Render a line of answer text, turning [n] citation markers into links.
function renderLine(line: string, sources: Source[]) {
  const parts = line.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (m) {
      const n = parseInt(m[1], 10);
      const src = sources.find((s) => s.n === n);
      if (src) {
        return (
          <Link
            key={i}
            href={src.url}
            className="text-[var(--accent-dot)] font-medium hover:underline align-super text-[0.7em]"
            title={src.title}
          >
            [{n}]
          </Link>
        );
      }
    }
    return <span key={i}>{part}</span>;
  });
}

function renderAnswer(md: string, sources: Source[]) {
  const lines = md.trim().split(/\n+/).filter(Boolean);
  return lines.map((line, i) => {
    const bullet = /^\s*[-*]\s+/.test(line);
    const numbered = /^\s*\d+[.)]\s+/.test(line);
    const clean = line.replace(/^\s*([-*]|\d+[.)])\s+/, "");
    if (bullet || numbered) {
      return (
        <div key={i} className="flex gap-2 mb-2 leading-relaxed">
          <span className="text-[var(--ink-muted)] shrink-0">•</span>
          <span>{renderLine(clean, sources)}</span>
        </div>
      );
    }
    return (
      <p key={i} className="mb-3 leading-relaxed">
        {renderLine(line, sources)}
      </p>
    );
  });
}

export default function ChatAssistant() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Lock body scroll while the overlay is open.
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      return () => { document.body.style.overflow = ""; };
    }
  }, [open]);

  async function ask(mode: Mode, q: string) {
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, question: q }),
      });
      const data: AskResponse = await res.json();
      if (!res.ok || data.error) {
        setError(data.error ?? "Something went wrong.");
      } else {
        setAnswer(data);
      }
    } catch {
      setError("Could not reach the assistant.");
    } finally {
      setLoading(false);
    }
  }

  function submitFreeform(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (q) ask("chat", q);
  }

  return (
    <>
      {/* Floating round button — always on, discrete. Sits above the mobile
          bottom nav (58px + safe area); bottom-right on desktop. */}
      <button
        onClick={() => setOpen(true)}
        aria-label="Ask InkBytes"
        className="
          fixed right-4 z-40 md:right-6
          h-12 w-12 rounded-full
          bg-[var(--accent)] text-white
          shadow-lg shadow-black/20 ring-1 ring-white/10
          flex items-center justify-center
          opacity-80 hover:opacity-100 hover:scale-105
          transition-all
        "
        style={{ bottom: "calc(58px + env(safe-area-inset-bottom, 0px) + 12px)" }}
      >
        {/* Sparkle / ask glyph */}
        <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3v3M12 18v3M3 12h3M18 12h3" opacity="0.6" />
          <path d="M12 8l1.4 2.6L16 12l-2.6 1.4L12 16l-1.4-2.6L8 12l2.6-1.4z" fill="currentColor" stroke="none" />
        </svg>
      </button>

      {/* Overlay */}
      {open && (
        <div className="fixed inset-0 z-[60] flex flex-col bg-[var(--bg)]" role="dialog" aria-modal="true" aria-label="InkBytes assistant">
          {/* Header */}
          <div className="bg-[var(--accent)] text-white safe-top">
            <div className="max-w-2xl mx-auto px-4 h-13 flex items-center justify-between">
              <span className="font-bold tracking-tight">
                Ask InkBytes<span className="text-[var(--accent-dot)]">.</span>
              </span>
              <button onClick={() => setOpen(false)} aria-label="Close" className="text-white/70 hover:text-white p-1">
                <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>

          {/* Quick actions */}
          <div className="border-b border-[var(--border)] bg-white">
            <div className="max-w-2xl mx-auto px-4 py-3 flex flex-wrap gap-2">
              {QUICK_ACTIONS.map((qa) => (
                <button
                  key={qa.label}
                  onClick={() => ask(qa.mode, qa.question)}
                  disabled={loading}
                  className="text-xs font-medium rounded-full px-3 py-1.5 border border-[var(--border)] text-[var(--ink)] hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  {qa.label}
                </button>
              ))}
            </div>
          </div>

          {/* Answer area */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-2xl mx-auto px-4 py-5 text-[var(--ink)] text-[15px]">
              {loading && (
                <p className="text-[var(--ink-muted)] animate-pulse">Reading the latest events…</p>
              )}
              {error && !loading && (
                <p className="text-red-600">{error}</p>
              )}
              {!loading && !error && !answer && (
                <div className="text-[var(--ink-muted)]">
                  <p className="mb-2">Ask about today&apos;s news, or tap a chip above.</p>
                  <p className="text-xs">Answers come only from InkBytes published events, with sources you can open.</p>
                </div>
              )}
              {answer && !loading && (
                <>
                  <div className="prose-answer">{renderAnswer(answer.answer_md, answer.sources)}</div>
                  {answer.sources.length > 0 && (
                    <div className="mt-6 pt-4 border-t border-[var(--border)]">
                      <p className="text-[11px] uppercase tracking-wide text-[var(--ink-muted)] mb-2">Sources</p>
                      <div className="flex flex-col gap-1.5">
                        {answer.sources.map((s) => (
                          <Link key={s.n} href={s.url} className="text-sm text-[var(--ink)] hover:text-[var(--accent-dot)] transition-colors">
                            <span className="text-[var(--ink-muted)] font-mono text-xs mr-1.5">[{s.n}]</span>
                            {s.title}
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Free-form input */}
          <form onSubmit={submitFreeform} className="border-t border-[var(--border)] bg-white safe-bottom">
            <div className="max-w-2xl mx-auto px-4 py-3 flex gap-2">
              <input
                ref={inputRef}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                maxLength={500}
                placeholder="Ask about the news…"
                className="flex-1 rounded-full border border-[var(--border)] px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
              />
              <button
                type="submit"
                disabled={loading || !question.trim()}
                className="rounded-full bg-[var(--accent)] text-white px-4 py-2 text-sm font-medium disabled:opacity-40 transition-opacity"
              >
                Ask
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
