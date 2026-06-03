"use client";
// Note: this page uses client-side state for filter tabs, but data fetching
// is done via Server Component children. For v0 simplicity, everything is
// a client component here since the data set is tiny (31 outlets).

import { useState, useEffect } from "react";
import Link from "next/link";
import type { Outlet } from "@/lib/types";

const REGION_LABELS: Record<string, string> = {
  all:       "All",
  global:    "🌐 Global",
  "latam-dr":"🇩🇴 DR",
  "latam-mx":"🇲🇽 Mexico",
  "latam-co":"🇨🇴 Colombia",
  "latam-ar":"🇦🇷 Argentina",
};

const VERTICAL_COLORS: Record<string, string> = {
  general:  "bg-gray-100 text-gray-600",
  business: "bg-amber-100 text-amber-700",
  tech:     "bg-blue-100 text-blue-700",
  politics: "bg-purple-100 text-purple-700",
};

function healthDot(outlet: Outlet): { color: string; label: string } {
  if (!outlet.active) return { color: "bg-gray-300", label: "Inactive" };
  if (!outlet.last_seen) return { color: "bg-yellow-400", label: "Never scraped" };
  const hAgo = (Date.now() - new Date(outlet.last_seen).getTime()) / 3_600_000;
  if (hAgo < 2)  return { color: "bg-green-500",  label: "Healthy" };
  if (hAgo < 24) return { color: "bg-amber-400",  label: "Stale" };
  return               { color: "bg-red-400",    label: "Old" };
}

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (m < 2)  return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function AdminPage() {
  const [outlets, setOutlets] = useState<Outlet[]>([]);
  const [status, setStatus] = useState<Record<string, number> | null>(null);
  const [region, setRegion] = useState("all");
  const [lang, setLang] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/api/proxy/status").then(r => r.json()),
      fetch("/api/proxy/outlets").then(r => r.json()),
    ])
      .then(([s, o]) => { setStatus(s); setOutlets(o); setLoading(false); })
      .catch(() => { setError("Curator API unreachable — is it running on port 8060?"); setLoading(false); });
  }, []);

  const regions = ["all", ...Array.from(new Set(outlets.map(o => o.region))).sort()];
  const langs   = ["all", ...Array.from(new Set(outlets.map(o => o.language))).sort()];

  const visible = outlets.filter(o =>
    (region === "all" || o.region === region) &&
    (lang   === "all" || o.language === lang)
  );

  const activeCount   = outlets.filter(o => o.active).length;
  const scrapedCount  = outlets.filter(o => o.article_count > 0).length;
  const latamCount    = outlets.filter(o => o.region.startsWith("latam")).length;

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Admin</h1>
          <p className="text-xs text-[var(--ink-muted)] mt-0.5">Pipeline health &amp; outlet management</p>
        </div>
        <Link href="/" className="text-xs text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors">
          ← Reader
        </Link>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700 mb-8">
          {error}
        </div>
      )}

      {/* Pipeline stats */}
      {status && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {[
            { label: "Articles",  value: status.articles_total },
            { label: "Enriched",  value: status.articles_enriched },
            { label: "Events",    value: status.events_total },
            { label: "Pages",     value: status.pages_published },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white border border-[var(--border)] rounded-lg px-5 py-4">
              <div className="text-2xl font-bold text-[var(--accent)]">{(value ?? 0).toLocaleString()}</div>
              <div className="text-xs text-[var(--ink-muted)] mt-0.5 uppercase tracking-wide">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Outlets section */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-[var(--ink-muted)]">
            Outlets
          </h2>
          {!loading && (
            <p className="text-xs text-[var(--ink-muted)] mt-0.5">
              {activeCount} active &middot; {scrapedCount} scraped &middot; {latamCount} LATAM
            </p>
          )}
        </div>
        {/* Rerun placeholder */}
        <button
          disabled
          title="Coming in v1 — wire to Messor scheduler"
          className="px-3 py-1.5 rounded-lg bg-gray-100 text-gray-400 text-xs font-medium cursor-not-allowed"
        >
          Run cycle (v1)
        </button>
      </div>

      {/* Filter tabs */}
      {!loading && outlets.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {/* Region tabs */}
          <div className="flex gap-1 flex-wrap">
            {regions.map(r => (
              <button
                key={r}
                onClick={() => setRegion(r)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  region === r
                    ? "bg-[var(--accent)] text-white border-[var(--accent)]"
                    : "border-[var(--border)] text-[var(--ink-muted)] hover:border-[var(--accent)] hover:text-[var(--accent)]"
                }`}
              >
                {REGION_LABELS[r] ?? r}
              </button>
            ))}
          </div>
          {/* Language separator + tabs */}
          <div className="flex gap-1">
            {langs.map(l => (
              <button
                key={l}
                onClick={() => setLang(l)}
                className={`text-xs px-2.5 py-1 rounded-full border font-mono transition-colors ${
                  lang === l
                    ? "bg-[var(--ink)] text-white border-[var(--ink)]"
                    : "border-[var(--border)] text-[var(--ink-muted)] hover:border-[var(--ink)] hover:text-[var(--ink)]"
                }`}
              >
                {l === "all" ? "All lang" : l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Outlet table */}
      {loading ? (
        <div className="rounded-lg border border-[var(--border)] px-5 py-10 text-center text-sm text-[var(--ink-muted)]">
          Loading…
        </div>
      ) : visible.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[var(--border)] px-5 py-10 text-center text-sm text-[var(--ink-muted)]">
          No outlets match the current filter.
        </div>
      ) : (
        <div className="bg-white border border-[var(--border)] rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-gray-50 text-left">
                <th className="px-4 py-2.5 text-xs font-medium text-[var(--ink-muted)] uppercase tracking-wide w-4"></th>
                <th className="px-4 py-2.5 text-xs font-medium text-[var(--ink-muted)] uppercase tracking-wide">Outlet</th>
                <th className="px-4 py-2.5 text-xs font-medium text-[var(--ink-muted)] uppercase tracking-wide hidden sm:table-cell">Region</th>
                <th className="px-4 py-2.5 text-xs font-medium text-[var(--ink-muted)] uppercase tracking-wide hidden md:table-cell">Vertical</th>
                <th className="px-4 py-2.5 text-xs font-medium text-[var(--ink-muted)] uppercase tracking-wide text-right">Articles</th>
                <th className="px-4 py-2.5 text-xs font-medium text-[var(--ink-muted)] uppercase tracking-wide text-right hidden sm:table-cell">Events</th>
                <th className="px-4 py-2.5 text-xs font-medium text-[var(--ink-muted)] uppercase tracking-wide text-right hidden md:table-cell">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((outlet, i) => {
                const { color, label } = healthDot(outlet);
                return (
                  <tr
                    key={outlet.id}
                    className={`${i < visible.length - 1 ? "border-b border-[var(--border)]" : ""} ${!outlet.active ? "opacity-40" : ""} hover:bg-gray-50 transition-colors`}
                  >
                    {/* Health dot */}
                    <td className="px-4 py-2.5">
                      <span title={label} className={`inline-block w-2 h-2 rounded-full ${color}`} />
                    </td>
                    {/* Name + URL */}
                    <td className="px-4 py-2.5">
                      <a href={outlet.url} target="_blank" rel="noopener noreferrer"
                         className="font-medium text-[var(--ink)] hover:text-[var(--accent)] transition-colors">
                        {outlet.display_name}
                      </a>
                      <div className="text-[10px] text-[var(--ink-muted)] font-mono">{outlet.language.toUpperCase()}</div>
                    </td>
                    {/* Region */}
                    <td className="px-4 py-2.5 hidden sm:table-cell text-xs text-[var(--ink-muted)]">
                      {REGION_LABELS[outlet.region] ?? outlet.region}
                    </td>
                    {/* Vertical */}
                    <td className="px-4 py-2.5 hidden md:table-cell">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${VERTICAL_COLORS[outlet.vertical] ?? VERTICAL_COLORS.general}`}>
                        {outlet.vertical}
                      </span>
                    </td>
                    {/* Article count */}
                    <td className="px-4 py-2.5 text-right tabular-nums text-[var(--ink-muted)] text-xs">
                      {outlet.article_count > 0 ? outlet.article_count.toLocaleString() : "—"}
                    </td>
                    {/* Events */}
                    <td className="px-4 py-2.5 text-right tabular-nums text-[var(--ink-muted)] text-xs hidden sm:table-cell">
                      {outlet.events_contributed > 0 ? outlet.events_contributed : "—"}
                    </td>
                    {/* Last seen */}
                    <td className="px-4 py-2.5 text-right text-[var(--ink-muted)] text-xs hidden md:table-cell whitespace-nowrap">
                      {relativeTime(outlet.last_seen)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
