<?php

namespace App\Http\Controllers\Concerns;

use Illuminate\Contracts\Pagination\LengthAwarePaginator;
use Illuminate\Database\Eloquent\Builder as EloquentBuilder;
use Illuminate\Database\Query\Builder as QueryBuilder;
use Illuminate\Http\Request;

/**
 * Shared server-side list mechanics for B7 (pagination + search + sort).
 *
 * Mirrors the pattern AuditLogController already uses (paginate +
 * withQueryString) and factors out the bits every growth-prone list needs:
 *
 *   page      — 1-based page number (Laravel default)
 *   per_page  — clamped to an allowlist so a client can't ask for everything
 *   q         — case-insensitive LIKE across caller-declared columns
 *   sort/dir  — ORDER BY a caller-declared column allowlist (dir ∈ asc|desc)
 *
 * Every knob is allowlisted by the caller so an arbitrary `?sort=` or
 * `?per_page=` can never reach raw SQL or blow memory. Query string is
 * preserved on the paginator so links keep the active filters.
 */
trait PaginatesQueries
{
    /**
     * Resolve the requested per-page size against an allowlist.
     *
     * @param  array<int, int>  $allowed
     */
    protected function resolvePerPage(Request $request, int $default = 25, array $allowed = [10, 25, 50, 100]): int
    {
        $requested = (int) $request->query('per_page', $default);

        return in_array($requested, $allowed, true) ? $requested : $default;
    }

    /**
     * Resolve sort column + direction against a column allowlist.
     *
     * @param  array<int, string>  $sortable  permitted sort columns
     * @return array{0: ?string, 1: string}  [column|null, 'asc'|'desc']
     */
    protected function resolveSort(Request $request, array $sortable, ?string $defaultSort = null, string $defaultDir = 'asc'): array
    {
        $sort = (string) $request->query('sort', (string) $defaultSort);
        $dir = strtolower((string) $request->query('dir', $defaultDir));

        if (! in_array($sort, $sortable, true)) {
            $sort = $defaultSort;
        }

        if (! in_array($dir, ['asc', 'desc'], true)) {
            $dir = $defaultDir;
        }

        return [$sort === '' ? null : $sort, $dir];
    }

    /**
     * Apply a case-insensitive LIKE search over the given columns. No-op when
     * the term is blank. Grouped in a single WHERE (...) so it composes with
     * other filters via AND.
     *
     * @param  EloquentBuilder|QueryBuilder  $query
     * @param  array<int, string>  $columns
     */
    protected function applySearch($query, ?string $term, array $columns)
    {
        $term = trim((string) $term);

        if ($term === '' || $columns === []) {
            return $query;
        }

        $needle = '%'.$term.'%';

        return $query->where(function ($q) use ($columns, $needle): void {
            foreach ($columns as $i => $column) {
                $i === 0
                    ? $q->where($column, 'like', $needle)
                    : $q->orWhere($column, 'like', $needle);
            }
        });
    }

    /**
     * Apply an allowlisted ORDER BY. No-op when no column resolved.
     *
     * @param  EloquentBuilder|QueryBuilder  $query
     */
    protected function applySort($query, ?string $sort, string $dir)
    {
        if ($sort === null) {
            return $query;
        }

        return $query->orderBy($sort, $dir === 'desc' ? 'desc' : 'asc');
    }

    /**
     * The common normalised list-state echoed back to the page so the React
     * table can render the active search/sort/page without re-deriving them.
     *
     * @return array{q: string, sort: ?string, dir: string, per_page: int}
     */
    protected function listState(Request $request, ?string $sort, string $dir, int $perPage): array
    {
        return [
            'q' => trim((string) $request->query('q', '')),
            'sort' => $sort,
            'dir' => $dir,
            'per_page' => $perPage,
        ];
    }

    /**
     * Convenience: run page+search+sort over a builder and return the paginator
     * with the query string preserved (so filter links survive pagination).
     *
     * @param  EloquentBuilder|QueryBuilder  $query
     * @param  array<int, string>  $searchColumns
     */
    protected function paginateList(
        Request $request,
        $query,
        array $searchColumns,
        ?string $sort,
        string $dir,
        int $perPage,
    ): LengthAwarePaginator {
        $this->applySearch($query, $request->query('q'), $searchColumns);
        $this->applySort($query, $sort, $dir);

        return $query->paginate($perPage)->withQueryString();
    }
}
