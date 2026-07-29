/**
 * Home feed loading skeleton — streams instantly while the force-dynamic server
 * render fetches /events. Mirrors the CURRENT layout (Stage 2+6): header →
 * search → one wrapping chip row → Top story (spine + cover) → story rows
 * (3px spine, two title lines, avatar/meta row). No topic carousel / Latest
 * strip — those were removed in Stage 2a.
 */
export default function Loading() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8" role="status" aria-label="Loading today's events">
      {/* Header */}
      <div className="mb-5">
        <div className="skel h-6 w-52 mb-2" />
        <div className="skel h-3 w-24" />
      </div>

      {/* Search */}
      <div className="skel h-11 w-full rounded-full mb-4" />

      {/* Category chips — one wrapping pill row */}
      <div className="flex flex-wrap gap-1.5 mb-6">
        {[...Array(9)].map((_, i) => (
          <div key={i} className="skel h-8 w-20 rounded-full" />
        ))}
      </div>

      {/* Top story — lead card (spine + cover + title) */}
      <div className="skel h-4 w-24 mb-3" />
      <div className="border border-[var(--border)] border-l-4 rounded-xl overflow-hidden mb-8">
        <div className="skel h-48 w-full rounded-none" />
        <div className="p-6">
          <div className="skel h-5 w-4/5 mb-2" />
          <div className="skel h-5 w-1/2 mb-4" />
          <div className="skel h-4 w-32" />
        </div>
      </div>

      {/* More stories — rows: 3px spine, two title lines, meta row */}
      <div className="skel h-4 w-40 mb-4" />
      <div className="flex flex-col gap-5">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="flex items-stretch gap-3">
            <div className="skel w-[3px] rounded" />
            <div className="flex-1">
              <div className="skel h-4 w-full mb-1.5" />
              <div className="skel h-4 w-2/3 mb-2.5" />
              <div className="skel h-3 w-28" />
            </div>
          </div>
        ))}
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}
