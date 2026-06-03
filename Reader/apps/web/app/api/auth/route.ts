import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const password = form.get("password") as string;
  const next = (form.get("next") as string) || "/";

  const correct = process.env.INKBYTES_DEMO_PASSWORD;

  if (!correct || password !== correct) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", next);
    loginUrl.searchParams.set("error", "1");
    return NextResponse.redirect(loginUrl, { status: 303 });
  }

  const response = NextResponse.redirect(new URL(next, request.url), { status: 303 });
  response.cookies.set("inkbytes_auth", password, {
    httpOnly: true,
    sameSite: "lax",
    // secure in production — omit in dev so localhost works over http
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 24 * 30, // 30 days
    path: "/",
  });
  return response;
}
