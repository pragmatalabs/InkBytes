import { usePage } from '@inertiajs/react';

/**
 * RBAC role helpers for the React layer (B2 — ADR-0005).
 *
 * Reads `auth.user.role` shared by HandleInertiaRequests and exposes boolean
 * gates. This is COSMETIC only — hiding/disabling controls is a UX nicety; the
 * server-side `role` middleware is the real gate. Never rely on these for
 * security.
 */
export function useAuthRole() {
    const { auth } = usePage().props;
    const role = auth?.user?.role ?? null;

    const isAdmin = role === 'admin';
    const isOperator = role === 'operator' || isAdmin;

    return {
        role,
        isAdmin,
        // operator OR admin — may run outlet/scraping/moderation mutations
        isOperator,
        isViewer: role === 'viewer',
        // sensitive sections (keys, settings, audit log, users) are admin-only
        canManage: isAdmin,
    };
}
