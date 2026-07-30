import { NextResponse } from "next/server";
import { getEntityDetail } from "@/lib/api";

/**
 * GET /api/entity/[id] — server-side proxy to Curator's /entities/{id}, so the
 * event-page entity sheet can fetch single-entity detail on tap without the
 * browser reaching the internal Curator host (same pattern as /api/ask).
 *
 * Returns 200 `{ available: false }` (NOT 404) when the entity isn't in a
 * published event OR the Curator endpoint isn't deployed yet (it's currently
 * deferred — Curator ADR-0042). The client sheet renders its light fallback on
 * that marker. Using 200 keeps a red 404 off every entity tap in the console;
 * once the endpoint ships this route transparently returns the real detail.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const detail = await getEntityDetail(id);
    return NextResponse.json(detail);
  } catch {
    return NextResponse.json({ available: false }, { status: 200 });
  }
}
