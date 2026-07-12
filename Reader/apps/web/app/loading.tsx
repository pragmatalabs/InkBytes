/**
 * Home feed loading skeleton — streams instantly while the force-dynamic
 * server render fetches /events (visual cue instead of a frozen old page).
 * Mirrors the real layout: header → topic carousel (mobile) / chips (desktop)
 * → banner → Latest strip → story rows.
 */
export default function Loading() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8" role="status" aria-label="Loading today's events">
      {/* Header */}
      <div className="mb-5">
        <div className="skel h-3 w-40 mb-2" />
        <div className="skel h-6 w-48 mb-2" />
        <div className="skel h-3 w-64" />
      </div>

      {/* Topic carousel (mobile) — three folder blocks */}
      <div className="sm:hidden mb-5 flex items-end justify-center gap-3">
        <div className="skel w-[92px] h-[110px] rounded-xl opacity-60" />
        <div className="skel w-[124px] h-[150px] rounded-2xl" />
        <div className="skel w-[92px] h-[110px] rounded-xl opacity-60" />
      </div>

      {/* Category chips (desktop) */}
      <div className="hidden sm:flex gap-2 mb-5">
        {[...Array(7)].map((_, i) => (
          <div key={i} className="skel h-8 w-20 rounded-full" />
        ))}
      </div>

      {/* Outlook banner */}
      <div className="skel h-16 w-full rounded-xl mb-5" />

      {/* Latest strip */}
      <div className="flex gap-3 overflow-hidden mb-7">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="skel w-[270px] h-28 rounded-xl shrink-0" />
        ))}
      </div>

      {/* Lead + rows */}
      <div className="skel h-56 w-full rounded-xl mb-5" />
      <div className="flex flex-col gap-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="skel h-10 w-full" />
        ))}
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}
