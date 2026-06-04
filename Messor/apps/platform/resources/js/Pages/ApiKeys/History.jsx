import AppLayout from '@/Layouts/AppLayout';
import ListPagination from '@/Components/ListPagination';
import SortableTableCell from '@/Components/SortableTableCell';
import { useListQuery } from '@/Hooks/useListQuery';
import { Head, Link } from '@inertiajs/react';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import {
    Alert,
    Box,
    Button,
    Chip,
    Collapse,
    FormControl,
    IconButton,
    InputLabel,
    MenuItem,
    Paper,
    Select,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography,
} from '@mui/material';
import { useState } from 'react';

const formatWhen = (iso) => (iso ? new Date(iso).toLocaleString() : '—');

const ACTION_COLOR = {
    'apikey.created': 'success',
    'apikey.updated': 'info',
    'apikey.deactivated': 'warning',
    'apikey.deleted': 'error',
};

function JsonBlock({ label, value }) {
    return (
        <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="overline" color="text.secondary">
                {label}
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
                {value === null || value === undefined
                    ? '—'
                    : JSON.stringify(value, null, 2)}
            </Box>
        </Box>
    );
}

function HistoryRow({ log }) {
    const [open, setOpen] = useState(false);
    const hasDetail = log.before !== null || log.after !== null;

    return (
        <>
            <TableRow hover sx={{ '& > *': { borderBottom: 'unset' } }}>
                <TableCell sx={{ width: 48 }}>
                    {hasDetail ? (
                        <IconButton
                            size="small"
                            onClick={() => setOpen((value) => !value)}
                            aria-label="toggle before/after"
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
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {formatWhen(log.created_at)}
                </TableCell>
                <TableCell>
                    <Chip
                        label={log.action}
                        size="small"
                        color={ACTION_COLOR[log.action] ?? 'default'}
                        variant="outlined"
                    />
                </TableCell>
                <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                        {log.actor_name ?? '—'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        {log.actor_email ?? '—'}
                    </Typography>
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {log.target_id ?? '—'}
                </TableCell>
            </TableRow>
            <TableRow>
                <TableCell colSpan={5} sx={{ py: 0, border: 0 }}>
                    <Collapse in={open} timeout="auto" unmountOnExit>
                        <Stack
                            direction={{ xs: 'column', md: 'row' }}
                            spacing={2}
                            sx={{ py: 2 }}
                        >
                            <JsonBlock label="Before" value={log.before} />
                            <JsonBlock label="After" value={log.after} />
                        </Stack>
                    </Collapse>
                </TableCell>
            </TableRow>
        </>
    );
}

export default function ApiKeysHistory({
    logs = { data: [], total: 0, per_page: 25, current_page: 1 },
    state = { q: '', sort: 'created_at', dir: 'desc', per_page: 25 },
    action = '',
    actions = [],
}) {
    const { toggleSort, changePage, changePerPage, setExtra } = useListQuery(
        'api-keys.history',
        state,
        { action },
    );

    const rows = logs.data ?? [];

    return (
        <AppLayout
            title="API Key History"
            subtitle="Rotation / change history — a read-only view of the audit trail for key create / rotate / deactivate / delete. Secret-free by design (only provider, label, masked last-4, active)."
        >
            <Head title="API Key History" />

            <Stack
                direction="row"
                justifyContent="space-between"
                alignItems="center"
                spacing={1}
                sx={{ mb: 2 }}
            >
                <Button
                    component={Link}
                    href={route('api-keys.index')}
                    startIcon={<ArrowBackRoundedIcon />}
                >
                    Back to keys
                </Button>
                <FormControl size="small" sx={{ minWidth: 220 }}>
                    <InputLabel id="history-action-label">Action</InputLabel>
                    <Select
                        labelId="history-action-label"
                        label="Action"
                        value={action ?? ''}
                        onChange={(event) =>
                            setExtra({ action: event.target.value })
                        }
                    >
                        <MenuItem value="">
                            <em>All actions</em>
                        </MenuItem>
                        {actions.map((a) => (
                            <MenuItem key={a} value={a}>
                                {a}
                            </MenuItem>
                        ))}
                    </Select>
                </FormControl>
            </Stack>

            <Alert severity="info" icon={false} sx={{ mb: 2 }}>
                Last-used timestamps and spend-per-key are{' '}
                <strong>N/A by design</strong> — Curator uses env keys
                (ADR-0004), so no DB key is ever read or charged.
            </Alert>

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell />
                            <SortableTableCell
                                column="created_at"
                                sort={state.sort}
                                dir={state.dir}
                                onSort={toggleSort}
                                sx={{ whiteSpace: 'nowrap' }}
                            >
                                When
                            </SortableTableCell>
                            <SortableTableCell
                                column="action"
                                sort={state.sort}
                                dir={state.dir}
                                onSort={toggleSort}
                            >
                                Action
                            </SortableTableCell>
                            <TableCell>Actor</TableCell>
                            <TableCell>Key id</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rows.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5} align="center">
                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                        sx={{ py: 3 }}
                                    >
                                        No key history yet. Rows appear as keys
                                        are created, rotated, deactivated or
                                        deleted.
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            rows.map((log) => (
                                <HistoryRow key={log.id} log={log} />
                            ))
                        )}
                    </TableBody>
                </Table>
                <ListPagination
                    paginator={logs}
                    onChangePage={changePage}
                    onChangePerPage={changePerPage}
                />
            </TableContainer>
        </AppLayout>
    );
}
