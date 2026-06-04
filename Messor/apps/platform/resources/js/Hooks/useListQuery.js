import { router } from '@inertiajs/react';
import { useCallback } from 'react';

/**
 * Shared client-side mechanics for a server-paginated list (B7).
 *
 * Mirrors the AuditLog page's Inertia navigation pattern and factors out the
 * query-param plumbing every server list needs: search, sort toggle, page, and
 * page-size changes all issue a `router.get` to the SAME route, preserving the
 * other params so the back-end trait (PaginatesQueries) can read them.
 *
 * @param {string} routeName  Ziggy route name for the list page (e.g. 'outlets.index')
 * @param {object} state      current { q, sort, dir, per_page } echoed by the server
 * @param {object} extra      any additional params to always carry (e.g. a status filter)
 */
export function useListQuery(routeName, state = {}, extra = {}) {
    const base = {
        q: state.q ?? '',
        sort: state.sort ?? '',
        dir: state.dir ?? 'asc',
        per_page: state.per_page ?? 25,
        ...extra,
    };

    const go = useCallback(
        (overrides) => {
            const params = { ...base, ...overrides };
            // Drop empty values so URLs stay clean.
            Object.keys(params).forEach((k) => {
                if (params[k] === '' || params[k] === null || params[k] === undefined) {
                    delete params[k];
                }
            });
            router.get(route(routeName), params, {
                preserveState: true,
                preserveScroll: true,
                replace: true,
            });
        },
        // base is derived from props each render; routeName is stable.
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [routeName, JSON.stringify(base)],
    );

    // Search resets to page 1.
    const search = useCallback((q) => go({ q, page: 1 }), [go]);

    // Toggle sort on a column: same column flips dir, new column starts asc.
    const toggleSort = useCallback(
        (column) => {
            const sameColumn = base.sort === column;
            const nextDir = sameColumn && base.dir === 'asc' ? 'desc' : 'asc';
            go({ sort: column, dir: nextDir, page: 1 });
        },
        [go, base.sort, base.dir],
    );

    // MUI page is 0-based; Laravel is 1-based.
    const changePage = useCallback((zeroBasedPage) => go({ page: zeroBasedPage + 1 }), [go]);

    const changePerPage = useCallback((perPage) => go({ per_page: perPage, page: 1 }), [go]);

    const setExtra = useCallback((overrides) => go({ ...overrides, page: 1 }), [go]);

    return { go, search, toggleSort, changePage, changePerPage, setExtra };
}
