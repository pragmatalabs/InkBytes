import { NextRequest, NextResponse } from "next/server";

const CURATOR = process.env.CURATOR_API_URL ?? "http://localhost:8060";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ path: string }> }
) {
  const { path } = await params;
  try {
    const res = await fetch(`${CURATOR}/${path}`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "Curator unreachable" }, { status: 502 });
  }
}
