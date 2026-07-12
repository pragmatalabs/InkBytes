/** Outlook index loading skeleton — date-grouped edition cards. */
export default function Loading() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8" role="status" aria-label="Loading outlooks">
      <div className="skel h-7 w-56 mb-2" />
      <div className="skel h-3 w-72 mb-8" />
      {[...Array(2)].map((_, g) => (
        <div key={g} className="mb-8">
          <div className="skel h-4 w-40 mb-4" />
          <div className="grid gap-3 sm:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="skel h-24 rounded-xl" />
            ))}
          </div>
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}
