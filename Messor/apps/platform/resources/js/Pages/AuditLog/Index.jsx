import AppLayout from '@/Layouts/AppLayout';
import { EmptyState } from '@/Components/ListStates';
import { Head, router } from '@inertiajs/react';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import {
    Box,
    Chip,
    Collapse,
    FormControl,
    Grid,
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
    TablePagination,
    TableRow,
    TextField,
    Typography,
} from '@mui/material';
import { useState } from 'react';

const formatWhen = (iso) => {
    if (!iso) {
        return '—';
    }

    return new Date(iso).toLocaleString();
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

function LogRow({ log }) {
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
                    <Typography variant="body2" fontWeight={600}>
                        {log.actor_name ?? '—'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        {log.actor_email ?? '—'}
                    </Typography>
                </TableCell>
                <TableCell>
                    <Chip label={log.action} size="small" />
                </TableCell>
                <TableCell>
                    <Typography variant="body2">{log.target_type}</Typography>
                    {log.target_id ? (
                        <Typography variant="caption" color="text.secondary">
                            {log.target_id}
                        </Typography>
                    ) : null}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {log.ip ?? '—'}
                </TableCell>
            </TableRow>
            <TableRow>
                <TableCell colSpan={6} sx={{ py: 0, border: 0 }}>
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

export default function AuditLogIndex({
    logs = { data: [], total: 0, per_page: 25, current_page: 1 },
    filters = { action: '', actor: '' },
    actions = [],
}) {
    const [actor, setActor] = useState(filters.actor ?? '');

    const applyFilters = (next) => {
        router.get(
            route('audit-log.index'),
            {
                action: next.action ?? '',
                actor: next.actor ?? '',
            },
            { preserveState: true, replace: true, preserveScroll: true },
        );
    };

    const handleActionChange = (event) => {
        applyFilters({ action: event.target.value, actor });
    };

    const handleActorSubmit = (event) => {
        event.preventDefault();
        applyFilters({ action: filters.action, actor });
    };

    const handleChangePage = (_event, newPage) => {
        // MUI page is 0-based; Laravel is 1-based.
        router.get(
            route('audit-log.index'),
            {
                action: filters.action ?? '',
                actor: filters.actor ?? '',
                page: newPage + 1,
            },
            { preserveState: true, replace: true, preserveScroll: true },
        );
    };

    const rows = logs.data ?? [];

    return (
        <AppLayout
            title="Audit Log"
            subtitle="Who did what to which target, with before/after. Read-only, newest first (backoffice.audit_logs)."
        >
            <Head title="Audit Log" />

            <Grid container spacing={2} sx={{ mb: 2.5 }}>
                <Grid size={{ xs: 12, sm: 5, md: 4 }}>
                    <FormControl fullWidth size="small">
                        <InputLabel id="audit-action-label">Action</InputLabel>
                        <Select
                            labelId="audit-action-label"
                            label="Action"
                            value={filters.action ?? ''}
                            onChange={handleActionChange}
                        >
                            <MenuItem value="">
                                <em>All actions</em>
                            </MenuItem>
                            {actions.map((action) => (
                                <MenuItem key={action} value={action}>
                                    {action}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Grid>
                <Grid size={{ xs: 12, sm: 7, md: 5 }}>
                    <Box component="form" onSubmit={handleActorSubmit}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Actor (name or email)"
                            value={actor}
                            onChange={(event) => setActor(event.target.value)}
                            placeholder="Press Enter to filter"
                        />
                    </Box>
                </Grid>
            </Grid>

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell />
                            <TableCell>When</TableCell>
                            <TableCell>Actor</TableCell>
                            <TableCell>Action</TableCell>
                            <TableCell>Target</TableCell>
                            <TableCell>IP</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rows.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={6}>
                                    <EmptyState
                                        title="No audit entries match"
                                        description="Rows appear as admins make state-changing actions."
                                    />
                                </TableCell>
                            </TableRow>
                        ) : (
                            rows.map((log) => <LogRow key={log.id} log={log} />)
                        )}
                    </TableBody>
                </Table>
                <TablePagination
                    component="div"
                    count={logs.total ?? 0}
                    page={(logs.current_page ?? 1) - 1}
                    onPageChange={handleChangePage}
                    rowsPerPage={logs.per_page ?? 25}
                    rowsPerPageOptions={[logs.per_page ?? 25]}
                />
            </TableContainer>
        </AppLayout>
    );
}
