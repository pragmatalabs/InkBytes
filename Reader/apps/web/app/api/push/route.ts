import { NextRequest, NextResponse } from "next/server";

/**
 * Push proxy (ADR-R-0012) — the browser can't reach the internal Curator host,
 * so this forwards subscribe / unsubscribe / vapid-key requests server-side.
 *   GET  /api/push            → { publicKey }         (VAPID applicationServerKey)
 *   POST /api/push?op=subscribe   { subscription, topics?, lang?, userAgent? }
 *   POST /api/push?op=unsubscribe { endpoint }
 * One route keeps the surface tiny; Curator owns the store + VAPID + sender.
 */
export const runtime = "nodejs";

const CURATOR = process.env.CURATOR_API_URL ?? "http://localhost:8060";

export async function GET() {
  try {
    const r = await fetch(`${CURATOR}/push/vapid`, { cache: "no-store" });
    if (!r.ok) throw new Error(String(r.status));
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({ publicKey: "" }, { status: 200 });
  }
}

export async function POST(req: NextRequest) {
  const op = req.nextUrl.searchParams.get("op");
  if (op !== "subscribe" && op !== "unsubscribe") {
    return NextResponse.json({ error: "unknown op" }, { status: 400 });
  }
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad body" }, { status: 400 });
  }
  try {
    const r = await fetch(`${CURATOR}/push/${op}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    return NextResponse.json(await r.json().catch(() => ({})), { status: r.status });
  } catch {
    return NextResponse.json({ error: "upstream unreachable" }, { status: 502 });
  }
}
