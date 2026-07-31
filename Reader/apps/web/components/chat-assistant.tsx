"use client";

/**
 * ChatAssistant (ADR-0022) — ChatGPT-style corpus chat.
 *
 * A floating button opens a full-screen conversation with "Ask InkBytes". The
 * assistant answers ONLY from published InkBytes events; answers cite sources as
 * [n] linking to /event/{id}. Multi-turn with a short cap (a briefing tool, not
 * a chatbot to live in), suggested starters, per-message copy, conversation
 * export, and a personal saved-conversations drawer (lib/saved-chats).
 *
 * Talks to POST /api/ask (proxy → Curator /ask), sending the recent turns as
 * `history` so follow-ups keep context.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  listChats, saveChat, getChat, deleteChat, SAVED_CHATS_EVENT,
  type ChatMsg, type ChatSource, type SavedChat,
} from "@/lib/saved-chats";

interface AskResponse { answer_md: string; sources: ChatSource[]; error?: string }
type Mode = "resume" | "top10" | "chat";

/** Cap: a briefing assistant, not an endless chatbot. */
const MAX_USER_TURNS = 6;

const SUGGESTIONS: { label: string; mode: Mode; question: string }[] = [
  { label: "Today’s biggest stories", mode: "resume", question: "" },
  { label: "What’s developing right now?", mode: "chat", question: "What stories are developing right now?" },
  { label: "Top 10 in technology", mode: "top10", question: "Top 10 items to consider in technology today" },
  { label: "World news to know", mode: "top10", question: "Top 10 world news items to consider today" },
  { label: "Business & markets", mode: "top10", question: "Top 10 business and markets items today" },
];

const uid = () =>
  (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);

// ── Markdown-ish answer rendering: [n] citations → event links ────────────────
function renderLine(line: string, sources: ChatSource[], onNavigate: () => void) {
  return line.split(/(\[\d+\])/g).map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (m) {
      const src = sources.find((s) => s.n === parseInt(m[1], 10));
      if (src) {
        return (
          <Link
            key={i} href={src.url} onClick={onNavigate} title={src.title}
            className="text-[var(--accent-dot)] font-semibold hover:underline align-super text-[0.7em]"
          >
            [{m[1]}]
          </Link>
        );
      }
    }
    // inline **bold**
    return part.split(/(\*\*[^*]+\*\*)/g).map((seg, j) => {
      const b = seg.match(/^\*\*([^*]+)\*\*$/);
      return b ? <strong key={`${i}-${j}`} className="font-semibold">{b[1]}</strong> : <span key={`${i}-${j}`}>{seg}</span>;
    });
  });
}

function AnswerBody({ md, sources, onNavigate }: { md: string; sources: ChatSource[]; onNavigate: () => void }) {
  const lines = md.trim().split(/\n+/).filter(Boolean);
  return (
    <>
      {lines.map((line, i) => {
        const listItem = /^\s*([-*]|\d+[.)])\s+/.test(line);
        const heading = /^#{1,3}\s+/.test(line);
        const clean = line.replace(/^\s*([-*]|\d+[.)])\s+/, "").replace(/^#{1,3}\s+/, "");
        if (heading) {
          return <p key={i} className="font-bold text-[15px] mt-3 mb-1 first:mt-0">{renderLine(clean, sources, onNavigate)}</p>;
        }
        if (listItem) {
          return (
            <div key={i} className="flex gap-2 mb-1.5 leading-relaxed">
              <span className="text-[var(--accent-dot)] shrink-0 mt-[1px]">•</span>
              <span>{renderLine(clean, sources, onNavigate)}</span>
            </div>
          );
        }
        return <p key={i} className="mb-2.5 leading-relaxed last:mb-0">{renderLine(line, sources, onNavigate)}</p>;
      })}
    </>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────
const Ico = {
  bot: (c: string) => (
    <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v2.2" /><circle cx="12" cy="2.3" r="1.05" fill="currentColor" stroke="none" />
      <rect x="4.5" y="6.5" width="15" height="11" rx="3.5" /><path d="M2.6 11v2.2M21.4 11v2.2" />
      <circle cx="9.4" cy="11.4" r="1.25" fill="currentColor" stroke="none" />
      <circle cx="14.6" cy="11.4" r="1.25" fill="currentColor" stroke="none" /><path d="M9.5 14.4c.9.8 4.1.8 5 0" />
    </svg>
  ),
  close: (c: string) => <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>,
  copy: (c: string) => <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h8" /></svg>,
  check: (c: string) => <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>,
  send: (c: string) => <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5M5 12l7-7 7 7" /></svg>,
  plus: (c: string) => <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>,
  drawer: (c: string) => <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18M9 14h6" /></svg>,
  download: (c: string) => <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v12M7 11l5 4 5-4M5 21h14" /></svg>,
  trash: (c: string) => <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13" /></svg>,
  back: (c: string) => <svg viewBox="0 0 24 24" className={c} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18 9 12l6-6" /></svg>,
};

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={() => { navigator.clipboard?.writeText(text).then(() => { setDone(true); setTimeout(() => setDone(false), 1400); }); }}
      className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors"
    >
      {done ? Ico.check("w-3.5 h-3.5 text-[#16a34a]") : Ico.copy("w-3.5 h-3.5")}
      {done ? "Copied" : "Copy"}
    </button>
  );
}

export default function ChatAssistant() {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<"chat" | "saved">("chat");
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [chatId, setChatId] = useState<string>(() => uid());
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<SavedChat[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const userTurns = messages.filter((m) => m.role === "user").length;
  const atLimit = userTurns >= MAX_USER_TURNS;

  useEffect(() => {
    if (open) { document.body.style.overflow = "hidden"; return () => { document.body.style.overflow = ""; }; }
  }, [open]);

  // Keep the saved list live (this tab + cross-tab).
  useEffect(() => {
    const sync = () => setSaved(listChats());
    sync();
    window.addEventListener(SAVED_CHATS_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => { window.removeEventListener(SAVED_CHATS_EVENT, sync); window.removeEventListener("storage", sync); };
  }, []);

  // Autoscroll to the newest message.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  // Persist the conversation to the drawer whenever it grows (auto-save).
  const persist = useCallback((msgs: ChatMsg[]) => {
    const firstQ = msgs.find((m) => m.role === "user")?.content ?? "";
    if (!firstQ) return;
    saveChat({ id: chatId, title: firstQ.slice(0, 80), created: new Date().toISOString(), messages: msgs });
  }, [chatId]);

  async function send(mode: Mode, q: string) {
    if (loading || atLimit) return;
    const userMsg: ChatMsg = { id: uid(), role: "user", content: q || "Today’s briefing" };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const history = messages.slice(-6).map((m) => ({ role: m.role, content: m.content }));
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, question: q, history }),
      });
      const data: AskResponse = await res.json();
      if (!res.ok || data.error) {
        setError(data.error ?? "Something went wrong. Try again in a moment.");
      } else {
        const botMsg: ChatMsg = { id: uid(), role: "assistant", content: data.answer_md, sources: data.sources };
        const withBot = [...next, botMsg];
        setMessages(withBot);
        persist(withBot);
      }
    } catch {
      setError("Could not reach the assistant.");
    } finally {
      setLoading(false);
    }
  }

  function submitFreeform(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (q) send("chat", q);
  }

  function newChat() {
    setMessages([]); setChatId(uid()); setInput(""); setError(null); setView("chat");
    setTimeout(() => inputRef.current?.focus(), 60);
  }

  function loadChat(c: SavedChat) {
    setMessages(c.messages); setChatId(c.id); setView("chat"); setError(null);
  }

  function exportChat() {
    const md = messages.map((m) => {
      const who = m.role === "user" ? "**You**" : "**Ask InkBytes**";
      const src = m.sources?.length
        ? "\n\nSources:\n" + m.sources.map((s) => `- [${s.n}] ${s.title} — ${s.url}`).join("\n")
        : "";
      return `${who}:\n\n${m.content}${src}`;
    }).join("\n\n---\n\n");
    const header = `# Ask InkBytes — conversation\n_${new Date().toLocaleString()}_\n\n`;
    const blob = new Blob([header + md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `inkbytes-chat-${new Date().toISOString().slice(0, 10)}.md`;
    a.click(); URL.revokeObjectURL(url);
  }

  const closeOverlay = () => setOpen(false);

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(true)}
        aria-label="Ask InkBytes"
        className="fixed right-4 z-40 md:right-6 h-12 w-12 rounded-full bg-[var(--accent)] text-white shadow-lg shadow-black/20 ring-1 ring-white/10 flex items-center justify-center opacity-90 hover:opacity-100 hover:scale-105 transition-all"
        style={{ bottom: "calc(58px + env(safe-area-inset-bottom, 0px) + 12px)" }}
      >
        {Ico.bot("w-[22px] h-[22px]")}
      </button>

      {open && (
        <div className="fixed inset-0 z-[60] flex flex-col bg-[var(--bg)]" role="dialog" aria-modal="true" aria-label="Ask InkBytes">
          {/* Header */}
          <header className="bg-[var(--accent)] text-white safe-top shrink-0">
            <div className="max-w-2xl mx-auto px-3 h-13 flex items-center gap-1">
              {view === "saved" ? (
                <button onClick={() => setView("chat")} aria-label="Back to chat" className="p-2 -ml-1 text-white/80 hover:text-white">{Ico.back("w-5 h-5")}</button>
              ) : (
                <span className="pl-2 inline-flex items-center gap-2 font-bold tracking-tight">
                  {Ico.bot("w-5 h-5 text-white/90")}
                  Ask InkBytes<span className="text-[var(--accent-dot)]">.</span>
                </span>
              )}
              {view === "saved" && <span className="pl-1 font-bold tracking-tight">Saved chats</span>}
              <div className="ml-auto flex items-center gap-0.5">
                {view === "chat" && messages.length > 0 && (
                  <button onClick={exportChat} aria-label="Export conversation" title="Export" className="p-2 text-white/75 hover:text-white">{Ico.download("w-[18px] h-[18px]")}</button>
                )}
                {view === "chat" && (
                  <button onClick={() => setView("saved")} aria-label="Saved chats" title="Saved chats" className="p-2 text-white/75 hover:text-white relative">
                    {Ico.drawer("w-[18px] h-[18px]")}
                    {saved.length > 0 && <span className="absolute top-1 right-1 min-w-[14px] h-[14px] px-1 rounded-full bg-[var(--accent-dot)] text-[9px] font-bold leading-[14px] text-center">{saved.length}</span>}
                  </button>
                )}
                {view === "chat" && messages.length > 0 && (
                  <button onClick={newChat} aria-label="New chat" title="New chat" className="p-2 text-white/75 hover:text-white">{Ico.plus("w-[18px] h-[18px]")}</button>
                )}
                <button onClick={closeOverlay} aria-label="Close" className="p-2 text-white/75 hover:text-white">{Ico.close("w-5 h-5")}</button>
              </div>
            </div>
          </header>

          {/* ── Saved drawer ─────────────────────────────────────────────── */}
          {view === "saved" ? (
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-2xl mx-auto px-4 py-4">
                {saved.length === 0 ? (
                  <p className="text-[13px] text-[var(--ink-muted)] py-12 text-center">No saved conversations yet. Chats you have are kept here automatically.</p>
                ) : (
                  <div className="flex flex-col divide-y divide-[var(--border)]">
                    {saved.map((c) => (
                      <div key={c.id} className="flex items-center gap-2 py-3">
                        <button onClick={() => loadChat(c)} className="min-w-0 flex-1 text-left group">
                          <div className="text-[14px] font-semibold tracking-tight truncate group-hover:text-[var(--accent)] transition-colors">{c.title}</div>
                          <div suppressHydrationWarning className="text-[11px] text-[var(--ink-muted)] mt-0.5">
                            {c.messages.filter((m) => m.role === "user").length} turn{c.messages.filter((m) => m.role === "user").length === 1 ? "" : "s"} · {new Date(c.created).toLocaleDateString()}
                          </div>
                        </button>
                        <button onClick={() => deleteChat(c.id)} aria-label="Delete conversation" className="p-2 text-[var(--ink-muted)] hover:text-red-600 transition-colors shrink-0">{Ico.trash("w-4 h-4")}</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* ── Conversation ───────────────────────────────────────────── */
            <div ref={scrollRef} className="flex-1 overflow-y-auto">
              <div className="max-w-2xl mx-auto px-4 py-5">
                {messages.length === 0 && !loading && (
                  <div className="pt-6">
                    <div className="w-12 h-12 rounded-2xl bg-[var(--accent)] text-white grid place-items-center mb-4">{Ico.bot("w-7 h-7")}</div>
                    <h2 className="text-[22px] font-extrabold tracking-tight leading-tight">Ask about today’s news.</h2>
                    <p className="text-[13.5px] text-[var(--ink-muted)] mt-1.5 leading-relaxed">
                      Grounded in InkBytes’ published events only — every answer cites sources you can open. Try:
                    </p>
                    <div className="mt-4 flex flex-col gap-2">
                      {SUGGESTIONS.map((s) => (
                        <button
                          key={s.label}
                          onClick={() => send(s.mode, s.question)}
                          className="group flex items-center gap-2.5 text-left px-3.5 py-3 rounded-xl border border-[var(--border)] bg-white hover:border-[var(--ink)] transition-colors"
                        >
                          <span className="text-[var(--accent)] opacity-70 group-hover:opacity-100">{Ico.bot("w-4 h-4")}</span>
                          <span className="text-[13.5px] font-medium">{s.label}</span>
                          <span className="ml-auto text-[var(--ink-muted)] opacity-0 group-hover:opacity-100 transition-opacity">{Ico.send("w-3.5 h-3.5 rotate-90")}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex flex-col gap-4">
                  {messages.map((m) => (
                    m.role === "user" ? (
                      <div key={m.id} className="self-end max-w-[85%]">
                        <div className="rounded-2xl rounded-br-md bg-[var(--accent)] text-white px-3.5 py-2.5 text-[14.5px] leading-relaxed whitespace-pre-wrap">{m.content}</div>
                      </div>
                    ) : (
                      <div key={m.id} className="flex gap-2.5">
                        <span className="mt-0.5 w-7 h-7 rounded-full bg-[var(--accent)] text-white grid place-items-center shrink-0">{Ico.bot("w-4 h-4")}</span>
                        <div className="min-w-0 flex-1">
                          <div className="text-[14.5px] text-[var(--ink)]">
                            <AnswerBody md={m.content} sources={m.sources ?? []} onNavigate={closeOverlay} />
                          </div>
                          {m.sources && m.sources.length > 0 && (
                            <div className="mt-3 flex flex-col gap-1">
                              <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--ink-muted)]">Sources</p>
                              {m.sources.map((s) => (
                                <Link key={s.n} href={s.url} onClick={closeOverlay} className="text-[12.5px] text-[var(--ink)] hover:text-[var(--accent-dot)] transition-colors">
                                  <span className="font-mono text-[10px] text-[var(--ink-muted)] mr-1.5">[{s.n}]</span>{s.title}
                                </Link>
                              ))}
                            </div>
                          )}
                          <div className="mt-2"><CopyButton text={m.content} /></div>
                        </div>
                      </div>
                    )
                  ))}

                  {loading && (
                    <div className="flex gap-2.5">
                      <span className="mt-0.5 w-7 h-7 rounded-full bg-[var(--accent)] text-white grid place-items-center shrink-0">{Ico.bot("w-4 h-4")}</span>
                      <div className="flex items-center gap-1 pt-2.5">
                        {[0, 1, 2].map((i) => <span key={i} className="w-1.5 h-1.5 rounded-full bg-[var(--ink-muted)] animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />)}
                      </div>
                    </div>
                  )}

                  {error && !loading && <p className="text-[13px] text-red-600 pl-9">{error}</p>}
                </div>
              </div>
            </div>
          )}

          {/* ── Composer ─────────────────────────────────────────────────── */}
          {view === "chat" && (
            <div className="border-t border-[var(--border)] bg-white safe-bottom shrink-0">
              <div className="max-w-2xl mx-auto px-3 py-3">
                {atLimit ? (
                  <div className="flex items-center justify-between gap-3 rounded-xl bg-[var(--bg)] border border-[var(--border)] px-3.5 py-3">
                    <span className="text-[12.5px] text-[var(--ink-muted)] leading-snug">You’ve reached this conversation’s limit — start a fresh one to keep the briefing sharp.</span>
                    <button onClick={newChat} className="shrink-0 inline-flex items-center gap-1.5 rounded-full bg-[var(--accent)] text-white text-[12.5px] font-semibold px-3.5 py-2 hover:opacity-90 transition-opacity">{Ico.plus("w-3.5 h-3.5")}New</button>
                  </div>
                ) : (
                  <form onSubmit={submitFreeform} className="flex items-end gap-2">
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitFreeform(e); } }}
                      rows={1}
                      maxLength={500}
                      placeholder="Ask about the news…"
                      className="flex-1 resize-none max-h-32 rounded-2xl border border-[var(--border)] px-4 py-2.5 text-[14.5px] leading-relaxed focus:outline-none focus:border-[var(--accent)] transition-colors"
                    />
                    <button
                      type="submit"
                      disabled={loading || !input.trim()}
                      aria-label="Send"
                      className="shrink-0 h-10 w-10 rounded-full bg-[var(--accent)] text-white grid place-items-center disabled:opacity-30 hover:opacity-90 transition-opacity"
                    >
                      {Ico.send("w-[18px] h-[18px]")}
                    </button>
                  </form>
                )}
                <p className="mt-2 text-center text-[10.5px] text-[var(--ink-muted)]">
                  Answers come only from InkBytes published events. {!atLimit && `${MAX_USER_TURNS - userTurns} question${MAX_USER_TURNS - userTurns === 1 ? "" : "s"} left in this chat.`}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
