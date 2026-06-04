<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/**
 * EnsureUserHasRole — server-side RBAC gate (B2, ADR-0005).
 *
 * Registered as the route alias `role`. Apply with the minimum role tier the
 * route requires, e.g. `->middleware('role:admin')` or `->middleware('role:operator')`.
 *
 * Tiers are inclusive (admin satisfies operator). This middleware is the real
 * source of truth — the React layer's hide/disable is cosmetic only.
 *
 * Returns 403 on insufficient role. Assumes `auth` ran earlier in the stack;
 * an unauthenticated request is treated as forbidden.
 */
class EnsureUserHasRole
{
    /**
     * @param  string  ...$roles  one or more accepted role tiers (any match passes)
     */
    public function handle(Request $request, Closure $next, string ...$roles): Response
    {
        $user = $request->user();

        if ($user === null) {
            abort(403);
        }

        foreach ($roles as $role) {
            if ($user->hasRole($role)) {
                return $next($request);
            }
        }

        abort(403);
    }
}
