import ListPagination from '@/Components/ListPagination';
import ListSearchField from '@/Components/ListSearchField';
import SortableTableCell from '@/Components/SortableTableCell';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { useListQuery } from '@/Hooks/useListQuery';
import AppLayout from '@/Layouts/AppLayout';
import { Head, router } from '@inertiajs/react';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import {
    Box,
    Button,
    Chip,
    Collapse,
    FormControl,
    Grid,
    IconButton,
    InputLabel,
    MenuItem,
    Paper,
    Select,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography,
} from '@mui/material';
import { useState } from 'react';

const TYPE_LABELS = {
    over_budget: 'Over budget',
    stale_outlet: 'Stale outlet',
    scrape_low_success: 'Low scrape success',
    pipeline_stalled: 'Pipeline stalled',
};

const formatWhen = (iso) => (iso ? new Date(iso).toLocaleString() : '—');

const severityColor = (severity) =>
    severity === 'critical' ? 'error' : 'warning';

function AlertRow({ alert, canAck }) {
    const [open, setOpen] = useState(false);
    const isOpen = alert.status === 'open';

    const acknowledge = () => {
        router.post(
            route('alerts.acknowledge', alert.id),
            {},
            { preserveScroll: true },
        );
    };

    return (
        <>
            <TableRow hover sx={{ '& > *': { borderBottom: 'unset' } }}>
                <TableCell sx={{ width: 48 }}>
                    {alert.context ? (
                        <IconButton
                            size="small"
                            onClick={() => setOpen((value) => !value)}
                            aria-label="toggle context"
                        >
                            <ExpandMoreRoundedIcon
                                fontSize="small"
                                sx={{
                                    transform: open
                                        ? 'rotate(180deg)'
                                        : 'rotate(0deg)',
                                    transition: 'transform 150ms',
                                }}
                            />
                        </IconButton>
                    ) : null}
                </TableCell>
                <TableCell>
                    <Chip
                        label={alert.severity}
                        size="small"
                        color={severityColor(alert.severity)}
                        variant={isOpen ? 'filled' : 'outlined'}
                    />
                </TableCell>
                <TableCell>
                    <Typography variant="body2">
                        {TYPE_LABELS[alert.type] ?? alert.type}
                    </Typography>
                </TableCell>
                <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                        {alert.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        {alert.message}
                    </Typography>
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {formatWhen(alert.created_at)}
                </TableCell>
                <TableCell>
                    <Chip
                        label={alert.status}
                        size="small"
                        color={isOpen ? 'default' : 'success'}
                        variant="outlined"
                    />
                </TableCell>
                <TableCell align="right">
                    {isOpen && canAck ? (
                        <Button size="small" variant="outlined" onClick={acknowledge}>
                            Acknowledge
                        </Button>
                    ) : null}
                </TableCell>
            </TableRow>
            <TableRow>
                <TableCell colSpan={7} sx={{ py: 0, border: 0 }}>
                    <Collapse in={open} timeout="auto" unmountOnExit>
                        <Box sx={{ py: 2 }}>
                            <Typography variant="overline" color="text.secondary">
                                Context
                            </Typography>
                            <Box
                                component="pre"
                                sx={{
                                    m: 0,
                                    p: 1.5,
                                    borderRadius: 1,
                                    backgroundColor: 'action.hover',
                                    fontSize: 12,
                                    overflowX: 'auto',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                }}
                            >
                                {JSON.stringify(alert.context, null, 2)}
                            </Box>
                            {alert.status === 'acknowledged' ? (
                                <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    sx={{ display: 'block', mt: 1 }}
                                >
                                    Acknowledged {formatWhen(alert.acknowledged_at)}
                                </Typography>
                            ) : null}
                        </Box>
                    </Collapse>
                </TableCell>
            </TableRow>
        </>
    );
}

export default function AlertsIndex({
    alerts = { data: [], total: 0, per_page: 25, current_page: 1 },
    filters = { q: '', sort: 'created_at', dir: 'desc', status: '', type: '' },
    options = { types: [], statuses: [] },
}) {
    const { isOperator } = useAuthRole();
    const { search, toggleSort, changePage, changePerPage, setExtra } =
        useListQuery('alerts.index', filters, {
            status: filters.status ?? '',
            type: filters.type ?? '',
        });

    const rows = alerts.data ?? [];

    return (
        <AppLayout
            title="Alerts"
            subtitle="Operational alerts raised by the scheduled evaluator (alerts:evaluate). Acknowledge clears the bell badge (operator+)."
        >
            <Head title="Alerts" />

            <Grid container spacing={2} sx={{ mb: 2.5 }}>
                <Grid size={{ xs: 12, sm: 5, md: 4 }}>
                    <ListSearchField
                        value={filters.q}
                        onSearch={search}
                        placeholder="Search title / message"
                    />
                </Grid>
                <Grid size={{ xs: 6, sm: 3, md: 3 }}>
                    <FormControl fullWidth size="small">
                        <InputLabel id="alert-status-label">Status</InputLabel>
                        <Select
                            labelId="alert-status-label"
                            label="Status"
                            value={filters.status ?? ''}
                            onChange={(e) => setExtra({ status: e.target.value })}
                        >
                            <MenuItem value="">
                                <em>All statuses</em>
                            </MenuItem>
                            {options.statuses.map((s) => (
                                <MenuItem key={s} value={s}>
                                    {s}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Grid>
                <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                    <FormControl fullWidth size="small">
                        <InputLabel id="alert-type-label">Type</InputLabel>
                        <Select
                            labelId="alert-type-label"
                            label="Type"
                            value={filters.type ?? ''}
                            onChange={(e) => setExtra({ type: e.target.value })}
                        >
                            <MenuItem value="">
                                <em>All types</em>
                            </MenuItem>
                            {options.types.map((t) => (
                                <MenuItem key={t} value={t}>
                                    {TYPE_LABELS[t] ?? t}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Grid>
            </Grid>

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell />
                            <SortableTableCell
                                column="severity"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={toggleSort}
                            >
                                Severity
                            </SortableTableCell>
                            <SortableTableCell
                                column="type"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={toggleSort}
                            >
                                Type
                            </SortableTableCell>
                            <TableCell>Alert</TableCell>
                            <SortableTableCell
                                column="created_at"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={toggleSort}
                            >
                                When
                            </SortableTableCell>
                            <SortableTableCell
                                column="status"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={toggleSort}
                            >
                                Status
                            </SortableTableCell>
                            <TableCell align="right">Action</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rows.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={7} align="center">
                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                        sx={{ py: 3 }}
                                    >
                                        No alerts. The evaluator raises rows when
                                        a rule trips (requires the scheduler:
                                        php artisan schedule:work).
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            rows.map((alert) => (
                                <AlertRow
                                    key={alert.id}
                                    alert={alert}
                                    canAck={isOperator}
                                />
                            ))
                        )}
                    </TableBody>
                </Table>
                <ListPagination
                    paginator={alerts}
                    onChangePage={changePage}
                    onChangePerPage={changePerPage}
                />
            </TableContainer>
        </AppLayout>
    );
}
