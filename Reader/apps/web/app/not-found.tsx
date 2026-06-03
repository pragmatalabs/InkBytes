import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4 text-center px-4">
      <h1 className="text-4xl font-bold text-[var(--accent)]">404</h1>
      <p className="text-[var(--ink-muted)]">This page doesn&apos;t exist.</p>
      <Link href="/" className="text-sm underline text-[var(--accent)]">
        Back to events
      </Link>
    </div>
  );
}
