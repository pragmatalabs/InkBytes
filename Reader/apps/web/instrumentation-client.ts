// Global client instrumentation (Next.js 16 `instrumentation-client` hook).
// Runs after the HTML loads, before React hydration — see
// node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/instrumentation-client.md
//
// Purpose: recover from post-deploy "dead navigation". After a Reader deploy,
// a browser still holding the PREVIOUS build references chunk hashes that no
// longer exist on the new server. Next's client navigation (`<Link>`) then
// fails to load its route chunk — the dynamic import() rejects and the click
// silently does nothing. We detect that specific failure and do a ONE-TIME hard
// reload, which fetches the fresh HTML + new chunk hashes. Guarded by a short
// cooldown so a genuinely-unavailable chunk (offline/CDN) can't cause a loop.

const RELOAD_FLAG = "ink:chunk-reload-at";
const RELOAD_COOLDOWN_MS = 10_000;

function isChunkLoadError(err: unknown): boolean {
  if (!err) return false;
  const e = err as { name?: string; message?: string };
  const name = e.name ?? "";
  const msg = e.message ?? String(err);
  return (
    name === "ChunkLoadError" ||
    /Loading chunk [\w-]+ failed/i.test(msg) ||
    /Loading CSS chunk/i.test(msg) ||
    /Failed to fetch dynamically imported module/i.test(msg) ||
    /error loading dynamically imported module/i.test(msg) ||
    /Importing a module script failed/i.test(msg)
  );
}

function recover(): void {
  try {
    const last = Number(sessionStorage.getItem(RELOAD_FLAG) ?? "0");
    const now = Date.now();
    if (now - last < RELOAD_COOLDOWN_MS) return; // just tried — don't loop
    sessionStorage.setItem(RELOAD_FLAG, String(now));
  } catch {
    // sessionStorage unavailable (private mode / quota) — still attempt one reload.
  }
  window.location.reload();
}

if (typeof window !== "undefined") {
  // Dynamic-import failures surface as unhandled promise rejections.
  window.addEventListener("unhandledrejection", (event) => {
    if (isChunkLoadError(event.reason)) recover();
  });
  // Belt-and-suspenders: some browsers/bundlers raise a window error instead.
  window.addEventListener("error", (event) => {
    if (isChunkLoadError(event.error)) recover();
  });
}
