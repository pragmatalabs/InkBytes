import { TableCell, TableSortLabel } from '@mui/material';

/**
 * A TableCell whose header is a clickable sort control (B7). Wraps MUI's
 * TableSortLabel and wires it to the useListQuery `toggleSort` callback, so the
 * three server-paginated lists sort identically.
 *
 * @param {string} column   the server-side sort key (must be in the controller allowlist)
 * @param {string} sort     the currently-active sort column from server state
 * @param {string} dir      'asc' | 'desc'
 * @param {(c: string) => void} onSort  toggleSort from useListQuery
 */
export default function SortableTableCell({
    column,
    sort,
    dir,
    onSort,
    children,
    ...cellProps
}) {
    const active = sort === column;

    return (
        <TableCell sortDirection={active ? dir : false} {...cellProps}>
            <TableSortLabel
                active={active}
                direction={active ? dir : 'asc'}
                onClick={() => onSort(column)}
            >
                {children}
            </TableSortLabel>
        </TableCell>
    );
}
