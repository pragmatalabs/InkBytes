import { NextRequest, NextResponse } from "next/server";

/**
 * Auth gate — disabled for v0 (direct access, no password required).
 *
 * The full gate logic lives in proxy.ts.  Wire it back in once we're
 * ready to restrict access:
 *
 *   import { proxy } from "./proxy";
 *   export default proxy;
 *   export { config } from "./proxy";
 */
export function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
