import { NextResponse } from "next/server";
import { getEntityDetail } from "@/lib/api";

/**
 * GET /api/entity/[id] — server-side proxy to Curator's /entities/{id}, so the
 * event-page entity sheet can fetch single-entity detail on tap without the
 * browser reaching the internal Curator host (same pattern as /api/ask).
 *
 * 404 when the entity isn't in a published event OR the Curator endpoint isn't
 * deployed yet — the client sheet degrades to a light fallback either way.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const detail = await getEntityDetail(id);
    return NextResponse.json(detail);
  } catch {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
}
