/**
 * Event page loading skeleton — mirrors the Stage 5 order: action bar →
 * eyebrow → HEADLINE → provenance row → synthesis lines → inset cover (below the
 * prose). No cover-first hero.
 */
export default function Loading() {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10" role="status" aria-label="Loading story">
      {/* Action bar */}
      <div className="flex items-center justify-between mb-8">
        <div className="skel h-4 w-24" />
        <div className="skel h-8 w-24 rounded-full" />
      </div>

      {/* Eyebrow (topic) */}
      <div className="skel h-4 w-20 rounded-full mb-3" />

      {/* Headline — first substantial content */}
      <div className="skel h-8 w-full mb-2" />
      <div className="skel h-8 w-4/5 mb-4" />

      {/* Provenance row (avatars · sources · clocks) */}
      <div className="skel h-4 w-64 mb-8" />

      {/* Synthesis lines */}
      <div className="flex flex-col gap-3 mb-10">
        {[...Array(9)].map((_, i) => (
          <div key={i} className={`skel h-4 ${i % 4 === 3 ? "w-2/3" : "w-full"}`} />
        ))}
      </div>

      {/* Inset cover — below the prose */}
      <div className="skel h-40 w-full rounded-xl" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}
