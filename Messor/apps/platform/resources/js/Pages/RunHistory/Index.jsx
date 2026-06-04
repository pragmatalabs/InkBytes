import AppLayout from '@/Layouts/AppLayout';
import { Head } from '@inertiajs/react';
import {
    Alert,
    Box,
    Card,
    CardContent,
    Chip,
    Grid,
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

const numberFormatter = new Intl.NumberFormat();

function relativeTime(iso) {
    if (!iso) return '—';
    const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
    if (Number.isNaN(mins)) return '—';
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const h = Math.floor(mins / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
}

function fullTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toLocaleString();
}

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

function SummaryCard({ label, value, detail }) {
    return (
        <Card sx={{ height: '100%' }}>
            <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                    {label}
                </Typography>
                <Typography variant="h5" sx={{ mt: 0.5 }}>
                    {value}
                </Typography>
                {detail ? (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        {detail}
                    </Typography>
                ) : null}
            </CardContent>
        </Card>
    );
}

/**
 * Dependency-free bar chart drawn with inline SVG — no charting library.
 *
 * `runs` arrive newest-first from Messor; we reverse to plot oldest→newest
 * (left→right). Each bar's height is articles scaled to the window max; its
 * colour encodes that run's success rate. A thin polyline overlays the
 * success-rate trend (0..100% mapped to the same plot box). Renders fine with
 * a single data point (one centred bar, no line jitter).
 */
function RunSparkline({ runs }) {
    if (!runs || runs.length === 0) {
        return null;
    }

    const ordered = [...runs].reverse();
    const width = 720;
    const height = 160;
    const padX = 8;
    const padY = 12;
    const plotW = width - padX * 2;
    const plotH = height - padY * 2;

    const maxArticles = Math.max(1, ...ordered.map((r) => r.total_articles ?? 0));
    const n = ordered.length;
    // Bar slot width; cap bar width so a single run doesn't span the whole box.
    const slot = plotW / n;
    const barW = Math.min(slot * 0.6, 48);

    const barColor = (pct) => {
        if (pct == null) return '#9e9e9e';
        if (pct >= 95) return '#2e7d32';
        if (pct >= 80) return '#ed6c02';
        return '#d32f2f';
    };

    // Success-rate trend points (0..100% over the same plot box).
    const linePoints = ordered
        .map((r, i) => {
            if (r.success_rate_pct == null) return null;
            const cx = padX + slot * i + slot / 2;
            const cy = padY + plotH - (r.success_rate_pct / 100) * plotH;
            return `${cx.toFixed(1)},${cy.toFixed(1)}`;
        })
        .filter(Boolean)
        .join(' ');

    return (
        <Box sx={{ width: '100%', overflowX: 'auto' }}>
            <svg
                viewBox={`0 0 ${width} ${height}`}
                width="100%"
                height={height}
                role="img"
                aria-label="Articles per run with success-rate trend"
                style={{ display: 'block' }}
            >
                {/* baseline */}
                <line
                    x1={padX}
                    y1={padY + plotH}
                    x2={width - padX}
                    y2={padY + plotH}
                    stroke="#e0e0e0"
                    strokeWidth="1"
                />

                {ordered.map((r, i) => {
                    const articles = r.total_articles ?? 0;
                    const h = (articles / maxArticles) * plotH;
                    const x = padX + slot * i + (slot - barW) / 2;
                    const y = padY + plotH - h;
                    return (
                        <rect
                            key={r.id || i}
                            x={x}
                            y={y}
                            width={barW}
                            height={Math.max(h, 1)}
                            rx="2"
                            fill={barColor(r.success_rate_pct)}
                            opacity="0.85"
                        >
                            <title>
                                {`${fullTime(r.start_time)} — ${numberFormatter.format(
                                    articles,
                                )} articles · ${
                                    r.success_rate_pct != null
                                        ? `${r.success_rate_pct}% success`
                                        : 'success n/a'
                                }`}
                            </title>
                        </rect>
                    );
                })}

                {/* success-rate trend line (drawn only when ≥2 points) */}
                {linePoints.split(' ').length > 1 ? (
                    <polyline
                        points={linePoints}
                        fill="none"
                        stroke="#0f5fd7"
                        strokeWidth="1.5"
                        opacity="0.7"
                    />
                ) : null}
            </svg>
            <Stack direction="row" spacing={2} sx={{ mt: 1, flexWrap: 'wrap' }}>
                <Typography variant="caption" color="text.secondary">
                    Bars: articles per run (height scaled to window max)
                </Typography>
                <Typography variant="caption" color="text.secondary">
                    Colour: success rate (green ≥95% · amber ≥80% · red &lt;80%)
                </Typography>
                <Typography variant="caption" color="text.secondary">
                    Blue line: success-rate trend
                </Typography>
            </Stack>
        </Box>
    );
}

export default function RunHistoryIndex({ runHistory = {} }) {
    const runs = runHistory.runs ?? [];
    const summary = runHistory.summary ?? {};
    const reachable = runHistory.reachable ?? false;

    return (
        <AppLayout
            title="Run History"
            subtitle="Recent scraping runs from Messor: articles, success rate, outlets and duration."
        >
            <Head title="Run History" />

            {!reachable ? (
                <Alert severity="warning" sx={{ mb: 2.5 }}>
                    {runHistory.error || 'Messor API unreachable'} — showing no run
                    history. This view live-reads Messor&apos;s recent scrape
                    sessions; nothing is cached here.
                </Alert>
            ) : null}

            <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <SummaryCard
                        label="Runs in window"
                        value={numberFormatter.format(summary.total_runs ?? 0)}
                        detail={`latest ~${runHistory.window ?? 50}`}
                    />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <SummaryCard
                        label="Total articles"
                        value={numberFormatter.format(summary.total_articles ?? 0)}
                        detail="across these runs"
                    />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <SummaryCard
                        label="Avg success rate"
                        value={
                            summary.avg_success_rate_pct != null
                                ? `${summary.avg_success_rate_pct}%`
                                : '—'
                        }
                        detail="mean across runs"
                    />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <SummaryCard
                        label="Last run"
                        value={relativeTime(summary.last_run_at)}
                        detail={
                            summary.last_run_at ? fullTime(summary.last_run_at) : 'no runs yet'
                        }
                    />
                </Grid>
            </Grid>

            <Card sx={{ mt: 2.5 }}>
                <CardContent>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
                        Articles per run &amp; success-rate trend
                    </Typography>
                    {runs.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">
                            No runs to chart.
                        </Typography>
                    ) : (
                        <RunSparkline runs={runs} />
                    )}
                </CardContent>
            </Card>

            <Card sx={{ mt: 2.5 }}>
                <CardContent>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
                        Recent runs
                    </Typography>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Started</TableCell>
                                    <TableCell>Outlets</TableCell>
                                    <TableCell align="right">Articles</TableCell>
                                    <TableCell align="right">Success</TableCell>
                                    <TableCell align="right">Failed</TableCell>
                                    <TableCell align="right">Success rate</TableCell>
                                    <TableCell align="right">Duration</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {runs.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={7}>
                                            <Typography
                                                variant="body2"
                                                color="text.secondary"
                                            >
                                                {reachable
                                                    ? 'Messor reported no scrape sessions yet.'
                                                    : 'Messor API unreachable — no run data.'}
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    runs.map((run) => {
                                        const outletNames = (run.outlets ?? [])
                                            .map((o) => o.name)
                                            .filter(Boolean)
                                            .join(', ');
                                        return (
                                            <TableRow key={run.id}>
                                                <TableCell>
                                                    <Tooltip title={fullTime(run.start_time)}>
                                                        <span>
                                                            {relativeTime(run.start_time)}
                                                        </span>
                                                    </Tooltip>
                                                </TableCell>
                                                <TableCell>
                                                    <Tooltip
                                                        title={
                                                            outletNames ||
                                                            run.outlet_summary ||
                                                            'no outlets'
                                                        }
                                                    >
                                                        <span>
                                                            {run.total_outlets}{' '}
                                                            {run.total_outlets === 1
                                                                ? 'outlet'
                                                                : 'outlets'}
                                                        </span>
                                                    </Tooltip>
                                                </TableCell>
                                                <TableCell align="right">
                                                    {numberFormatter.format(
                                                        run.total_articles ?? 0,
                                                    )}
                                                </TableCell>
                                                <TableCell align="right">
                                                    {numberFormatter.format(
                                                        run.successful_articles ?? 0,
                                                    )}
                                                </TableCell>
                                                <TableCell align="right">
                                                    {numberFormatter.format(
                                                        run.failed_articles ?? 0,
                                                    )}
                                                </TableCell>
                                                <TableCell align="right">
                                                    {run.success_rate_pct != null ? (
                                                        <Chip
                                                            size="small"
                                                            color={successColor(
                                                                run.success_rate_pct,
                                                            )}
                                                            label={`${run.success_rate_pct}%`}
                                                        />
                                                    ) : (
                                                        '—'
                                                    )}
                                                </TableCell>
                                                <TableCell align="right">
                                                    {formatDuration(run.duration)}
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </CardContent>
            </Card>

            <Box sx={{ mt: 2.5 }}>
                <Typography variant="body2" color="text.secondary">
                    Live-read from Messor (recent sessions, bounded by staging
                    retention). Durable long-range history and a dedup ratio are
                    future Messor-side enhancements.
                    {runHistory.checked_at
                        ? ` · checked ${relativeTime(runHistory.checked_at)}`
                        : ''}
                </Typography>
            </Box>
        </AppLayout>
    );
}
