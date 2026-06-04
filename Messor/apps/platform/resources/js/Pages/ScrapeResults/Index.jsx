import AppLayout from '@/Layouts/AppLayout';
import ListPagination from '@/Components/ListPagination';
import ListSearchField from '@/Components/ListSearchField';
import SortableTableCell from '@/Components/SortableTableCell';
import { useListQuery } from '@/Hooks/useListQuery';
import { Head } from '@inertiajs/react';
import {
    Alert,
    Box,
    Chip,
    CircularProgress,
    Dialog,
    DialogContent,
    DialogTitle,
    IconButton,
    Paper,
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
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import { useState } from 'react';

const numberFormatter = new Intl.NumberFormat();

const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : '—');

function formatDuration(seconds) {
    if (seconds == null) return '—';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function successColor(pct) {
    if (pct == null) return 'default';
    if (pct >= 95) return 'success';
    if (pct >= 80) return 'warning';
    return 'error';
}

export default function ScrapeResultsIndex({
    sessions = { data: [], total: 0, per_page: 25, current_page: 1 },
    stats = {},
    reachable = true,
    filters = { q: '', sort: 'started_at', dir: 'desc', per_page: 25 },
}) {
    const list = useListQuery('scrape-results.index', filters);
    const rows = sessions.data ?? [];

    // Per-session detail (the outlets[] breakdown), fetched lazily on open.
    const [detail, setDetail] = useState(null); // { loading, session, error }

    const openDetail = (sessionId) => {
        setDetail({ loading: true, session: null, error: null });
        fetch(route('scrape-results.show', sessionId), {
            headers: { Accept: 'application/json' },
        })
            .then((res) => res.json().then((body) => ({ ok: res.ok, body })))
            .then(({ ok, body }) => {
                if (!ok || !body?.session) {
                    setDetail({
                        loading: false,
                        session: null,
                        error: 'Session not found.',
                    });
                    return;
                }
                setDetail({ loading: false, session: body.session, error: null });
            })
            .catch(() => {
                setDetail({
                    loading: false,
                    session: null,
                    error: 'Could not load session detail.',
                });
            });
    };

    const closeDetail = () => setDetail(null);

    return (
        <AppLayout
            title="Scrape Results"
            subtitle="Durable per-session harvest results from Messor (ADR-0006): each run with its per-outlet article counts, duplicates, and success rate. Read-only."
        >
            <Head title="Scrape Results" />

            <Stack direction="row" spacing={2} sx={{ mb: 2 }} alignItems="center">
                <Chip
                    label={`${numberFormatter.format(stats.session_count ?? 0)} sessions`}
                    variant="outlined"
                />
            </Stack>

            {!reachable && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                    The scrape-sessions table is not reachable right now. Showing an
                    empty list.
                </Alert>
            )}

            <Box sx={{ mb: 2.5, maxWidth: 480 }}>
                <ListSearchField
                    value={filters.q}
                    onSearch={list.search}
                    label="Search session id"
                    placeholder="Session id contains… (press Enter)"
                />
            </Box>

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Session</TableCell>
                            <SortableTableCell
                                column="started_at"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={list.toggleSort}
                            >
                                Started
                            </SortableTableCell>
                            <SortableTableCell
                                column="total_articles"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={list.toggleSort}
                                align="right"
                            >
                                Articles
                            </SortableTableCell>
                            <TableCell align="right">Successful</TableCell>
                            <TableCell align="right">Failed</TableCell>
                            <TableCell align="right">Duplicates</TableCell>
                            <SortableTableCell
                                column="success_rate"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={list.toggleSort}
                                align="right"
                            >
                                Success
                            </SortableTableCell>
                            <SortableTableCell
                                column="total_outlets"
                                sort={filters.sort}
                                dir={filters.dir}
                                onSort={list.toggleSort}
                                align="right"
                            >
                                Outlets
                            </SortableTableCell>
                            <TableCell align="right">Duration</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rows.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={9}>
                                    <Box sx={{ py: 4, textAlign: 'center' }}>
                                        <Typography
                                            variant="body1"
                                            color="text.secondary"
                                            sx={{ fontWeight: 600 }}
                                        >
                                            No scrape sessions yet
                                        </Typography>
                                        <Typography
                                            variant="body2"
                                            color="text.secondary"
                                            sx={{ mt: 0.5 }}
                                        >
                                            Sessions appear here once Messor completes a
                                            harvest run and Curator persists it.
                                        </Typography>
                                    </Box>
                                </TableCell>
                            </TableRow>
                        ) : (
                            rows.map((s) => (
                                <TableRow
                                    key={s.session_id}
                                    hover
                                    sx={{ cursor: 'pointer' }}
                                    onClick={() => openDetail(s.session_id)}
                                >
                                    <TableCell sx={{ maxWidth: 220 }}>
                                        <Typography
                                            variant="caption"
                                            sx={{ fontFamily: 'monospace' }}
                                        >
                                            {s.session_id}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Tooltip title={fmt(s.started_at)}>
                                            <Typography variant="caption">
                                                {fmt(s.started_at)}
                                            </Typography>
                                        </Tooltip>
                                    </TableCell>
                                    <TableCell align="right">
                                        {numberFormatter.format(s.total_articles)}
                                    </TableCell>
                                    <TableCell align="right">
                                        {numberFormatter.format(s.successful_articles)}
                                    </TableCell>
                                    <TableCell align="right">
                                        {numberFormatter.format(s.failed_articles)}
                                    </TableCell>
                                    <TableCell align="right">
                                        {numberFormatter.format(s.duplicates_total)}
                                    </TableCell>
                                    <TableCell align="right">
                                        {s.success_rate_pct != null ? (
                                            <Chip
                                                size="small"
                                                label={`${s.success_rate_pct}%`}
                                                color={successColor(
                                                    s.success_rate_pct
                                                )}
                                                variant="outlined"
                                            />
                                        ) : (
                                            '—'
                                        )}
                                    </TableCell>
                                    <TableCell align="right">
                                        {s.total_outlets}
                                    </TableCell>
                                    <TableCell align="right">
                                        {formatDuration(s.duration_seconds)}
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
                <ListPagination
                    paginator={sessions}
                    onChangePage={list.changePage}
                    onChangePerPage={list.changePerPage}
                />
            </TableContainer>

            <Dialog
                open={Boolean(detail)}
                onClose={closeDetail}
                fullWidth
                maxWidth="md"
            >
                <DialogTitle sx={{ pr: 6 }}>
                    Session detail
                    <IconButton
                        onClick={closeDetail}
                        sx={{ position: 'absolute', right: 8, top: 8 }}
                        size="small"
                    >
                        <CloseRoundedIcon fontSize="small" />
                    </IconButton>
                </DialogTitle>
                <DialogContent dividers>
                    {detail?.loading && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                            <CircularProgress size={28} />
                        </Box>
                    )}

                    {detail?.error && (
                        <Alert severity="error">{detail.error}</Alert>
                    )}

                    {detail?.session && (
                        <Stack spacing={2}>
                            <Box>
                                <Typography
                                    variant="caption"
                                    sx={{ fontFamily: 'monospace' }}
                                    color="text.secondary"
                                >
                                    {detail.session.session_id}
                                </Typography>
                                <Stack
                                    direction="row"
                                    spacing={1}
                                    sx={{ mt: 1 }}
                                    flexWrap="wrap"
                                    useFlexGap
                                >
                                    <Chip
                                        size="small"
                                        variant="outlined"
                                        label={`Started ${fmt(detail.session.started_at)}`}
                                    />
                                    <Chip
                                        size="small"
                                        variant="outlined"
                                        label={`Ended ${fmt(detail.session.ended_at)}`}
                                    />
                                    <Chip
                                        size="small"
                                        variant="outlined"
                                        label={`Duration ${formatDuration(detail.session.duration_seconds)}`}
                                    />
                                    {detail.session.success_rate_pct != null && (
                                        <Chip
                                            size="small"
                                            color={successColor(
                                                detail.session.success_rate_pct
                                            )}
                                            label={`${detail.session.success_rate_pct}% success`}
                                        />
                                    )}
                                </Stack>
                            </Box>

                            <Typography variant="subtitle2">
                                Per-outlet breakdown
                            </Typography>

                            {detail.session.outlets?.length ? (
                                <TableContainer component={Paper} variant="outlined">
                                    <Table size="small">
                                        <TableHead>
                                            <TableRow>
                                                <TableCell>Outlet</TableCell>
                                                <TableCell align="right">
                                                    Articles
                                                </TableCell>
                                                <TableCell align="right">
                                                    Successful
                                                </TableCell>
                                                <TableCell align="right">
                                                    Failed
                                                </TableCell>
                                                <TableCell align="right">
                                                    Duplicates
                                                </TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {detail.session.outlets.map((o, i) => (
                                                <TableRow key={o.slug || o.name || i}>
                                                    <TableCell>
                                                        <Typography variant="body2">
                                                            {o.name || o.slug || '—'}
                                                        </Typography>
                                                        {o.slug && o.name && (
                                                            <Typography
                                                                variant="caption"
                                                                color="text.secondary"
                                                                sx={{
                                                                    fontFamily:
                                                                        'monospace',
                                                                }}
                                                            >
                                                                {o.slug}
                                                            </Typography>
                                                        )}
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        {numberFormatter.format(
                                                            o.articles
                                                        )}
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        {numberFormatter.format(
                                                            o.successful
                                                        )}
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        {numberFormatter.format(
                                                            o.failed
                                                        )}
                                                    </TableCell>
                                                    <TableCell align="right">
                                                        {numberFormatter.format(
                                                            o.duplicates
                                                        )}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </TableContainer>
                            ) : (
                                <Typography variant="body2" color="text.secondary">
                                    No per-outlet breakdown recorded for this session.
                                </Typography>
                            )}
                        </Stack>
                    )}
                </DialogContent>
            </Dialog>
        </AppLayout>
    );
}
