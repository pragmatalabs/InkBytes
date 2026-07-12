/** Event page loading skeleton — cover, chips, headline, synthesis lines. */
export default function Loading() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8" role="status" aria-label="Loading story">
      <div className="skel h-56 sm:h-72 w-full rounded-xl mb-6" />
      <div className="flex gap-2 mb-4">
        <div className="skel h-5 w-20 rounded-full" />
        <div className="skel h-5 w-24 rounded-full" />
      </div>
      <div className="skel h-8 w-full mb-2" />
      <div className="skel h-8 w-3/4 mb-6" />
      <div className="skel h-3 w-48 mb-8" />
      <div className="flex flex-col gap-3">
        {[...Array(8)].map((_, i) => (
          <div key={i} className={`skel h-4 ${i % 4 === 3 ? "w-2/3" : "w-full"}`} />
        ))}
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}
