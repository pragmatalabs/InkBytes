import { NextRequest, NextResponse } from "next/server";

/**
 * POST /api/ask — proxy to the Curator assistant endpoint (ADR-0022).
 *
 * The browser can't reach the internal Curator hostname, so this route handler
 * forwards the chat request server-side. Curator answers ONLY from published
 * events and returns { answer_md, sources[] } with citations resolving to
 * /event/{id} pages.
 */
const CURATOR = process.env.CURATOR_API_URL ?? "http://localhost:8060";

const MODES = new Set(["resume", "top10", "chat"]);

export async function POST(request: NextRequest) {
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
