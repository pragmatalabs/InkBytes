"use client";

import { useState } from "react";

/** Share / copy / export / print controls for an outlook column. Share uses the
 *  Web Share API (native sheet on mobile/Safari) with a copy-link fallback; Copy
 *  and Export build a clean markdown document (headline + body + attribution);
 *  Print → the browser's print-to-PDF. Hidden when printing. */
export default function OutlookActions({
  headline, bodyMd, theme, editionDate,
}: { headline: string; bodyMd: string; theme: string; editionDate: string }) {
  const [copied, setCopied] = useState(false);
  const [shared, setShared] = useState(false);
  const doc = `# ${headline}\n\n${bodyMd}\n\n— InkBytes · Today's ${theme} Outlook · ${editionDate}\n`;

  const share = async () => {
    const url = typeof window !== "undefined" ? window.location.href : "";
    const title = `Today's ${theme.charAt(0).toUpperCase() + theme.slice(1)} Outlook`;
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title, text: headline, url });
        return;
      } catch { /* user cancelled — fall through to clipboard */ }
    }
    try {
      await navigator.clipboard.writeText(url);
      setShared(true);
      setTimeout(() => setShared(false), 1800);
    } catch { /* clipboard blocked — no-op */ }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(doc);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch { /* clipboard blocked — no-op */ }
  };

  const download = () => {
    const blob = new Blob([doc], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `inkbytes-${theme}-outlook-${editionDate}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const btn = "inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border border-[var(--border)] bg-white hover:bg-gray-50 transition-colors";
  return (
    <div className="flex flex-wrap items-center gap-2 print:hidden">
      <button onClick={share} className={btn} aria-label="Share this outlook">
        {shared ? (
          <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
        )}
        {shared ? "Link copied ✓" : "Share"}
      </button>
      <button onClick={copy} className={btn}>{copied ? "Copied ✓" : "Copy"}</button>
      <button onClick={download} className={btn}>Export .md</button>
      <button onClick={() => window.print()} className={btn}>Print / PDF</button>
    </div>
  );
}
