import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/api/auth"];
const AUTH_COOKIE = "inkbytes_auth";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Let public paths through
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Static assets — no gate
  if (pathname.startsWith("/_next") || pathname.startsWith("/favicon")) {
    return NextResponse.next();
  }

  // v0: auth gate disabled — direct access, no login required.
  // To re-enable: set INKBYTES_DEMO_PASSWORD in env and restore the block below.
  return NextResponse.next();

  /* auth gate — restore when gated access is needed
  const password = process.env.INKBYTES_DEMO_PASSWORD;
  if (!password) return NextResponse.next();

  const cookie = request.cookies.get(AUTH_COOKIE)?.value;
  if (cookie === password) return NextResponse.next();

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
  */
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
