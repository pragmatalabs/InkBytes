"use client";

import { useState } from "react";

/** Copy / export / print controls for an outlook column. Builds a clean markdown
 *  document (headline + body + attribution) for the clipboard and the .md export;
 *  Print → the browser's print-to-PDF. Hidden when printing. */
export default function OutlookActions({
  headline, bodyMd, theme, editionDate,
}: { headline: string; bodyMd: string; theme: string; editionDate: string }) {
  const [copied, setCopied] = useState(false);
  const doc = `# ${headline}\n\n${bodyMd}\n\n— InkBytes · Today's ${theme} Outlook · ${editionDate}\n`;

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

  const btn = "text-xs px-3 py-1.5 rounded-full border border-[var(--border)] bg-white hover:bg-gray-50 transition-colors";
  return (
    <div className="flex flex-wrap items-center gap-2 print:hidden">
      <button onClick={copy} className={btn}>{copied ? "Copied ✓" : "Copy"}</button>
      <button onClick={download} className={btn}>Export .md</button>
      <button onClick={() => window.print()} className={btn}>Print / PDF</button>
    </div>
  );
}
