import AppLayout from '@/Layouts/AppLayout';
import ListPagination from '@/Components/ListPagination';
import ListSearchField from '@/Components/ListSearchField';
import SortableTableCell from '@/Components/SortableTableCell';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { useListQuery } from '@/Hooks/useListQuery';
import { Head, router, usePage } from '@inertiajs/react';
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded';
import HubRoundedIcon from '@mui/icons-material/HubRounded';
import {
    Alert,
    Box,
    Button,
    Chip,
    FormControl,
    Grid,
    InputLabel,
    MenuItem,
    Paper,
    Select,
    Snackbar,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Tooltip,
    Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';

const STATUS_COLORS = {
    published: 'success',
    draft: 'warning',
    dropped: 'default',
};

const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : '—');

export default function ModerationIndex({
    events = { data: [], total: 0, per_page: 25, current_page: 1 },
    stats = {},
    filters = { q: '', sort: 'last_updated_at', dir: 'desc', per_page: 25, status: '' },
    statuses = [],
}) {
    const { flash } = usePage().props;
    const { isOperator } = useAuthRole();
    const [snack, setSnack] = useState(null);
    const [busy, setBusy] = useState(null); // `${kind}:${id}` while a command is in-flight

    const list = useListQuery('moderation.index', filters, {
        status: filters.status ?? '',
    });

    const rows = events.data ?? [];

    useEffect(() => {
        if (flash?.success) {
            setSnack({ severity: 'success', message: flash.success });
        } else if (flash?.error) {
            setSnack({ severity: 'error', message: flash.error });
        }
    }, [flash]);

    const send = (key, routeName, id) => {
        setBusy(key);
        router.post(
            route(routeName, id),
            {},
            {
                preserveScroll: true,
                onFinish: () => setBusy(null),
            }
        );
    };

    return (
        <AppLayout
            title="Moderation"
            subtitle="Review Curator events and pages, then publish, unpublish, drop, or trigger a re-synthesize / re-cluster. Actions are sent to Curator as commands — they take effect when Curator applies them."
        >
            <Head title="Moderation" />

            <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                <Chip label={`${stats.event_count ?? 0} events`} variant="outlined" />
                <Chip label={`${stats.page_count ?? 0} pages`} variant="outlined" />
                <Chip
                    label={`${stats.published_count ?? 0} published`}
                    color="success"
                    variant="outlined"
                />
            </Stack>

            <Grid container spacing={2} sx={{ mb: 2.5 }}>
                <Grid size={{ xs: 12, sm: 7, md: 6 }}>
                    <ListSearchField
                        value={filters.q}
                        onSearch={list.search}
                        label="Search headline"
                        placeholder="Headline contains… (press Enter)"
                    />
                </Grid>
                <Grid size={{ xs: 12, sm: 5, md: 4 }}>
                    <FormControl fullWidth size="small">
                        <InputLabel id="mod-status-label">Status</InputLabel>
                        <Select
                            labelId="mod-status-label"
                            label="Status"
                            value={filters.status ?? ''}
                            onChange={(event) =>
                                list.setExtra({ status: event.target.value })
                            }
                        >
                            <MenuItem value="">
                                <em>All statuses</em>
                            </MenuItem>
                            {statuses.map((s) => (
                                <MenuItem key={s} value={s}>
                                    {s}
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
                            <TableCell>Headline / Event</TableCell>
                            <SortableTableCell
                                column="status"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={list.toggleSort}
                            >
                                Status
                            </SortableTableCell>
                            <SortableTableCell
                                column="source_count"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={list.toggleSort}
                                align="right"
                            >
                                Sources
                            </SortableTableCell>
                            <SortableTableCell
                                column="last_updated_at"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={list.toggleSort}
                            >
                                Freshness
                            </SortableTableCell>
                            <TableCell>Published</TableCell>
                            <TableCell align="right">Cost</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rows.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={7}>
                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                        sx={{ py: 2, textAlign: 'center' }}
                                    >
                                        No events match.
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            rows.map((event) => {
                                const page = event.page;
                                const pid = page?.id;
                                const published = Boolean(page?.is_published);

                                return (
                                    <TableRow key={event.id} hover>
                                        <TableCell sx={{ maxWidth: 360 }}>
                                            <Typography
                                                variant="body2"
                                                sx={{ fontWeight: 600 }}
                                            >
                                                {page?.headline ?? (
                                                    <em>(no page synthesized)</em>
                                                )}
                                            </Typography>
                                            <Typography
                                                variant="caption"
                                                color="text.secondary"
                                                sx={{ fontFamily: 'monospace' }}
                                            >
                                                {event.id}
                                                {event.topic ? ` · ${event.topic}` : ''}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                size="small"
                                                label={event.status}
                                                color={
                                                    STATUS_COLORS[event.status] ??
                                                    'default'
                                                }
                                                variant={
                                                    event.status === 'published'
                                                        ? 'filled'
                                                        : 'outlined'
                                                }
                                            />
                                        </TableCell>
                                        <TableCell align="right">
                                            {page
                                                ? page.evidence_count
                                                : event.source_count}
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="caption">
                                                {fmt(page?.freshness_at)}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="caption">
                                                {fmt(page?.published_at)}
                                            </Typography>
                                        </TableCell>
                                        <TableCell align="right">
                                            {page?.cost_cents != null
                                                ? `${(page.cost_cents / 100).toFixed(2)}¢`
                                                : '—'}
                                        </TableCell>
                                        <TableCell align="right">
                                            <Stack
                                                direction="row"
                                                spacing={0.5}
                                                justifyContent="flex-end"
                                                flexWrap="wrap"
                                                useFlexGap
                                            >
                                                {!isOperator && (
                                                    <Typography
                                                        variant="caption"
                                                        color="text.secondary"
                                                    >
                                                        read-only
                                                    </Typography>
                                                )}
                                                {isOperator && page && !published && (
                                                    <Button
                                                        size="small"
                                                        variant="contained"
                                                        color="success"
                                                        disabled={busy != null}
                                                        onClick={() =>
                                                            send(
                                                                `pub:${pid}`,
                                                                'moderation.pages.publish',
                                                                pid
                                                            )
                                                        }
                                                    >
                                                        Publish
                                                    </Button>
                                                )}
                                                {isOperator && page && published && (
                                                    <Button
                                                        size="small"
                                                        variant="outlined"
                                                        disabled={busy != null}
                                                        onClick={() =>
                                                            send(
                                                                `unpub:${pid}`,
                                                                'moderation.pages.unpublish',
                                                                pid
                                                            )
                                                        }
                                                    >
                                                        Unpublish
                                                    </Button>
                                                )}
                                                {isOperator && page && (
                                                    <Button
                                                        size="small"
                                                        variant="outlined"
                                                        color="error"
                                                        disabled={busy != null}
                                                        onClick={() =>
                                                            send(
                                                                `drop:${pid}`,
                                                                'moderation.pages.drop',
                                                                pid
                                                            )
                                                        }
                                                    >
                                                        Drop
                                                    </Button>
                                                )}
                                                {isOperator && (
                                                    <Tooltip title="Re-run synthesis for this event">
                                                        <span>
                                                            <Button
                                                                size="small"
                                                                variant="text"
                                                                startIcon={
                                                                    <AutorenewRoundedIcon fontSize="small" />
                                                                }
                                                                disabled={busy != null}
                                                                onClick={() =>
                                                                    send(
                                                                        `resyn:${event.id}`,
                                                                        'moderation.events.resynthesize',
                                                                        event.id
                                                                    )
                                                                }
                                                            >
                                                                Re-synth
                                                            </Button>
                                                        </span>
                                                    </Tooltip>
                                                )}
                                                {isOperator && (
                                                    <Tooltip title="Re-cluster this event's articles">
                                                        <span>
                                                            <Button
                                                                size="small"
                                                                variant="text"
                                                                startIcon={
                                                                    <HubRoundedIcon fontSize="small" />
                                                                }
                                                                disabled={busy != null}
                                                                onClick={() =>
                                                                    send(
                                                                        `reclus:${event.id}`,
                                                                        'moderation.events.recluster',
                                                                        event.id
                                                                    )
                                                                }
                                                            >
                                                                Re-cluster
                                                            </Button>
                                                        </span>
                                                    </Tooltip>
                                                )}
                                            </Stack>
                                        </TableCell>
                                    </TableRow>
                                );
                            })
                        )}
                    </TableBody>
                </Table>
                <ListPagination
                    paginator={events}
                    onChangePage={list.changePage}
                    onChangePerPage={list.changePerPage}
                />
            </TableContainer>

            <Snackbar
                open={Boolean(snack)}
                autoHideDuration={5000}
                onClose={() => setSnack(null)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                {snack ? (
                    <Alert
                        severity={snack.severity}
                        onClose={() => setSnack(null)}
                        variant="filled"
                    >
                        {snack.message}
                    </Alert>
                ) : undefined}
            </Snackbar>
        </AppLayout>
    );
}
