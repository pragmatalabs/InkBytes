/** Outlook column loading skeleton — persona header + editorial body lines. */
export default function Loading() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-8" role="status" aria-label="Loading outlook">
      <div className="skel h-3 w-24 mb-6" />
      <div className="flex items-center gap-3 mb-6">
        <div className="skel w-12 h-12 rounded-full shrink-0" />
        <div className="flex-1">
          <div className="skel h-4 w-40 mb-1.5" />
          <div className="skel h-3 w-28" />
        </div>
      </div>
      <div className="skel h-8 w-full mb-2" />
      <div className="skel h-8 w-2/3 mb-6" />
      <div className="flex flex-col gap-3">
        {[...Array(10)].map((_, i) => (
          <div key={i} className={`skel h-4 ${i % 5 === 4 ? "w-1/2" : "w-full"}`} />
        ))}
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}
