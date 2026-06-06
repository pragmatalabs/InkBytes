import { NextRequest, NextResponse } from "next/server";

/** Build the correct external base URL behind Traefik (or any reverse proxy).
 *
 * `request.url` inside a Route Handler reflects the container-internal binding
 * (e.g. http://0.0.0.0:3000/api/auth) — not the public domain.  Traefik adds
 * `x-forwarded-proto` and `x-forwarded-host` so we can reconstruct the real URL.
 * Falls back to NEXT_PUBLIC_SITE_URL, then to request.url (dev / direct access).
 */
function externalBase(request: NextRequest): string {
  const proto = request.headers.get("x-forwarded-proto")?.split(",")[0].trim();
  const host  = request.headers.get("x-forwarded-host")?.split(",")[0].trim()
             ?? request.headers.get("host");
  if (proto && host) return `${proto}://${host}`;
  if (process.env.NEXT_PUBLIC_SITE_URL) return process.env.NEXT_PUBLIC_SITE_URL;
  // dev fallback — use request.url base (localhost:3001 etc.)
  const u = new URL(request.url);
  return `${u.protocol}//${u.host}`;
}

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const password = form.get("password") as string;
  const next = (form.get("next") as string) || "/";
  const base = externalBase(request);

  const correct = process.env.INKBYTES_DEMO_PASSWORD;

  // No password configured → gate is open; auth route is a no-op (proxy.ts already allows through)
  if (correct && password !== correct) {
    const loginUrl = new URL("/login", base);
    loginUrl.searchParams.set("next", next);
    loginUrl.searchParams.set("error", "1");
    return NextResponse.redirect(loginUrl, { status: 303 });
  }

  const response = NextResponse.redirect(new URL(next, base), { status: 303 });
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
