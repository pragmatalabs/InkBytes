/**
 * /entities loading skeleton — the graph fetch can be slow on a cold cache
 * (~20 s Curator query, lib/api.ts getGraph SWR notes), so an instant branded
 * shell matters here more than anywhere: without it, tapping "Entities" looks
 * like the app ignored the tap.
 */
export default function Loading() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-6" role="status" aria-label="Loading entities">
      {/* Header + Full graph pill */}
      <div className="flex items-end justify-between gap-3 mb-4">
        <div>
          <div className="skel h-7 w-32 mb-2" />
          <div className="skel h-3 w-52" />
        </div>
        <div className="skel h-8 w-24 rounded-full" />
      </div>

      {/* Search */}
      <div className="skel h-10 w-full rounded-full mb-4" />

      {/* Type tabs */}
      <div className="flex gap-4 mb-4 border-b border-[var(--border)] pb-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="skel h-5 w-24" />
        ))}
      </div>

      {/* Card row */}
      <div className="flex gap-2.5 overflow-hidden mb-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="skel w-[150px] h-32 rounded-xl shrink-0" />
        ))}
      </div>

      {/* List rows */}
      <div className="flex flex-col gap-3">
        {[...Array(7)].map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="skel w-8 h-8 rounded-full shrink-0" />
            <div className="flex-1">
              <div className="skel h-3.5 w-2/3 mb-1.5" />
              <div className="skel h-2.5 w-1/3" />
            </div>
          </div>
        ))}
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}
