import { TablePagination } from '@mui/material';

/**
 * Server-paginator footer for a list (B7). Adapts a Laravel LengthAwarePaginator
 * payload ({ data, total, per_page, current_page }) to MUI's 0-based
 * TablePagination and wires page / page-size changes to useListQuery callbacks.
 *
 * @param {object} paginator     Laravel paginator shape
 * @param {(zeroBasedPage: number) => void} onChangePage
 * @param {(perPage: number) => void} onChangePerPage
 * @param {number[]} rowsPerPageOptions
 */
export default function ListPagination({
    paginator,
    onChangePage,
    onChangePerPage,
    rowsPerPageOptions = [10, 25, 50, 100],
}) {
    const perPage = paginator?.per_page ?? 25;
    // MUI errors if the active rowsPerPage is not among the options.
    const options = rowsPerPageOptions.includes(perPage)
        ? rowsPerPageOptions
        : [...rowsPerPageOptions, perPage].sort((a, b) => a - b);

    return (
        <TablePagination
            component="div"
            count={paginator?.total ?? 0}
            page={(paginator?.current_page ?? 1) - 1}
            onPageChange={(_event, page) => onChangePage(page)}
            rowsPerPage={perPage}
            rowsPerPageOptions={options}
            onRowsPerPageChange={(event) =>
                onChangePerPage(Number(event.target.value))
            }
        />
    );
}
