import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/ask — proxy to the Curator assistant endpoint (ADR-0022).
 *
 * The browser can't reach the internal Curator hostname, so this route handler
 * forwards the chat request server-side. Curator answers ONLY from published
 * events and returns { answer_md, sources[] } with citations resolving to
 * /event/{id} pages.
 *
 * SECURITY (flood / cost-amplification guard): /ask is public, unauthenticated,
 * and LLM-backed — every call spends DeepSeek tokens and worker CPU, so an
 * unmetered flood is both a denial-of-service AND a cost attack. We gate each
 * request with an in-memory rate limiter BEFORE touching the LLM:
 *   - per-IP:  PER_IP_MAX requests / WINDOW_MS  (stops a single abuser)
 *   - global:  GLOBAL_MAX requests / WINDOW_MS  (hard ceiling on total LLM
 *              spend even under a distributed flood — degraded chat beats a
 *              runaway bill)
 * State is module-level and relies on the Node.js runtime (pinned below): the
 * Reader self-hosts as a single long-lived `next start` process (one
 * container), so the counters are shared across requests. If the Reader is ever
 * horizontally scaled, move this to a shared store (Redis); the Traefik per-IP
 * rateLimit middleware is the defence-in-depth layer at the edge.
 */
export const runtime = "nodejs"; // module-level limiter state must persist across requests

const CURATOR = process.env.CURATOR_API_URL ?? "http://localhost:8060";

const MODES = new Set(["resume", "top10", "chat"]);

// ── Rate limiting (tunable) ──────────────────────────────────────────────────
const WINDOW_MS = 60_000; // sliding window
const PER_IP_MAX = 8; // requests per IP per window — generous for a human, brutal for a flood
const GLOBAL_MAX = 40; // total requests per window across all IPs — caps LLM spend

const ipHits = new Map<string, number[]>(); // ip → request timestamps (ms)
let globalHits: number[] = []; // timestamps across all IPs

function clientIp(req: NextRequest): string {
  // Traefik sits in front and sets X-Forwarded-For with the real client IP
  // (it is the edge — no upstream proxy — so the left-most hop is the client).
  const xff = req.headers.get("x-forwarded-for");
  if (xff) return xff.split(",")[0].trim();
  return req.headers.get("x-real-ip")?.trim() || "unknown";
}

/** Returns retry-after seconds if the request should be blocked, else null. */
function rateLimited(ip: string): number | null {
  const now = Date.now();
  const cutoff = now - WINDOW_MS;

  globalHits = globalHits.filter((t) => t > cutoff);
  const ipTimes = (ipHits.get(ip) ?? []).filter((t) => t > cutoff);

  if (ipTimes.length >= PER_IP_MAX) {
    return Math.ceil((ipTimes[0] + WINDOW_MS - now) / 1000);
  }
  if (globalHits.length >= GLOBAL_MAX) {
    return Math.ceil((globalHits[0] + WINDOW_MS - now) / 1000);
  }

  // Record the hit.
  ipTimes.push(now);
  ipHits.set(ip, ipTimes);
  globalHits.push(now);

  // Bound memory: a flood from many spoofed X-Forwarded-For values could bloat
  // the map, so prune fully-aged buckets when it grows large.
  if (ipHits.size > 5000) {
    for (const [k, v] of ipHits) {
      if (v.every((t) => t <= cutoff)) ipHits.delete(k);
    }
  }
  return null;
}

export async function POST(request: NextRequest) {
  const retryAfter = rateLimited(clientIp(request));
  if (retryAfter !== null) {
    return NextResponse.json(
      { error: "Too many requests — please slow down." },
      { status: 429, headers: { "Retry-After": String(retryAfter) } },
    );
  }

  let body: { question?: string; mode?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }

  const mode = MODES.has(body.mode ?? "") ? body.mode : "chat";
  const question = (body.question ?? "").toString().slice(0, 500);

  if (mode === "chat" && !question.trim()) {
    return NextResponse.json({ error: "question required" }, { status: 400 });
  }

  try {
    const res = await fetch(`${CURATOR}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, mode }),
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json(
        { error: `assistant unavailable (${res.status})` },
        { status: 502 },
      );
    }
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json(
      { error: "Could not reach the assistant service." },
      { status: 502 },
    );
  }
}
