import type { Metadata } from "next";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage(
  { searchParams }: { searchParams: Promise<{ next?: string; error?: string }> }
) {
  const { next = "/", error } = await searchParams;

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-[var(--accent)]">InkBytes</h1>
          <p className="text-sm text-[var(--ink-muted)] mt-1">Enter your access password</p>
        </div>
        <form action="/api/auth" method="POST" className="space-y-4">
          <input type="hidden" name="next" value={next} />
          <div>
            <input
              type="password"
              name="password"
              placeholder="Password"
              autoFocus
              required
              className="w-full px-4 py-2.5 rounded-lg border border-[var(--border)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)] bg-white"
            />
          </div>
          {error && (
            <p className="text-xs text-red-600">Incorrect password. Try again.</p>
          )}
          <button
            type="submit"
            className="w-full py-2.5 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
