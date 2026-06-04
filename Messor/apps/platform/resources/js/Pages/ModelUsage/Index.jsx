import AppLayout from '@/Layouts/AppLayout';
import ListPagination from '@/Components/ListPagination';
import { Head, router } from '@inertiajs/react';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import {
    Alert,
    Box,
    Button,
    Chip,
    Grid,
    LinearProgress,
    Paper,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TextField,
    Typography,
} from '@mui/material';
import { useState } from 'react';

const usd = (value, digits = 4) =>
    value === null || value === undefined
        ? '—'
        : `$${Number(value).toLocaleString(undefined, {
              minimumFractionDigits: digits,
              maximumFractionDigits: digits,
          })}`;

const int = (value) =>
    value === null || value === undefined
        ? '—'
        : Number(value).toLocaleString();

function StatCard({ label, value, hint }) {
    return (
        <Paper sx={{ p: 2.5, height: '100%' }}>
            <Typography variant="overline" color="text.secondary">
                {label}
            </Typography>
            <Typography variant="h5" sx={{ mt: 0.5, fontWeight: 700 }}>
                {value}
            </Typography>
            {hint ? (
                <Typography variant="caption" color="text.secondary">
                    {hint}
                </Typography>
            ) : null}
        </Paper>
    );
}

function BudgetWidget({ budget }) {
    if (!budget) {
        return null;
    }

    const over = budget.over_budget;
    const pct = Math.min(budget.pct, 100);

    return (
        <Paper sx={{ p: 2.5 }}>
            <Stack
                direction={{ xs: 'column', sm: 'row' }}
                justifyContent="space-between"
                alignItems={{ xs: 'flex-start', sm: 'center' }}
                spacing={1}
                sx={{ mb: 1.5 }}
            >
                <Box>
                    <Typography variant="overline" color="text.secondary">
                        Month-to-date spend vs budget
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        {usd(budget.mtd_spend_usd, 4)} / {usd(budget.budget_usd, 4)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        since {budget.month_start} · {budget.pct}% of budget
                    </Typography>
                </Box>
                <Chip
                    color={over ? 'error' : 'success'}
                    label={over ? 'Over budget' : 'Within budget'}
                    variant={over ? 'filled' : 'outlined'}
                />
            </Stack>
            <LinearProgress
                variant="determinate"
                value={pct}
                color={over ? 'error' : 'primary'}
                sx={{ height: 8, borderRadius: 1 }}
            />
            {over ? (
                <Alert severity="error" sx={{ mt: 2 }}>
                    Month-to-date spend ({usd(budget.mtd_spend_usd, 4)}) has
                    exceeded the configured monthly budget (
                    {usd(budget.budget_usd, 4)}).
                </Alert>
            ) : null}
        </Paper>
    );
}

export default function ModelUsageIndex({
    filters = {},
    summary = {},
    budget = null,
    byModel = [],
    byLabel = [],
    byDay = [],
    byEvent = { events: { data: [], total: 0, per_page: 25, current_page: 1 }, unattributed: {} },
}) {
    const [from, setFrom] = useState(filters.from ?? '');
    const [to, setTo] = useState(filters.to ?? '');

    const applyRange = (event) => {
        event.preventDefault();
        router.get(
            route('model-usage.index'),
            { from, to },
            { preserveState: true, preserveScroll: true, replace: true }
        );
    };

    // The by-event drill-down is server-paginated (B7) under its own
    // `event_page` param. Carry the active date range so paging keeps the scope.
    const eventRows = byEvent.events?.data ?? [];
    const navEvents = (overrides) => {
        router.get(
            route('model-usage.index'),
            { from: filters.from, to: filters.to, ...overrides },
            { preserveState: true, preserveScroll: true, replace: true }
        );
    };
    const onEventPage = (zeroBasedPage) =>
        navEvents({ event_page: zeroBasedPage + 1, per_page: byEvent.events?.per_page });
    const onEventPerPage = (perPage) =>
        navEvents({ event_page: 1, per_page: perPage });

    const exportUrl = route('model-usage.export', { from, to });

    return (
        <AppLayout
            title="Cost & Usage"
            subtitle="LLM spend persisted by Curator (backoffice.model_usage). Read-only — one row per completed call."
        >
            <Head title="Cost & Usage" />

            {/* Date-range filter + CSV export (B5). The range scopes every
                aggregate below; export honours the same range. */}
            <Paper
                component="form"
                onSubmit={applyRange}
                sx={{ p: 2, mb: 3 }}
            >
                <Stack
                    direction={{ xs: 'column', sm: 'row' }}
                    spacing={2}
                    alignItems={{ xs: 'stretch', sm: 'center' }}
                >
                    <TextField
                        label="From"
                        type="date"
                        size="small"
                        value={from}
                        onChange={(e) => setFrom(e.target.value)}
                        InputLabelProps={{ shrink: true }}
                    />
                    <TextField
                        label="To"
                        type="date"
                        size="small"
                        value={to}
                        onChange={(e) => setTo(e.target.value)}
                        InputLabelProps={{ shrink: true }}
                    />
                    <Button type="submit" variant="contained">
                        Apply range
                    </Button>
                    <Box sx={{ flexGrow: 1 }} />
                    <Button
                        component="a"
                        href={exportUrl}
                        variant="outlined"
                        startIcon={<DownloadRoundedIcon />}
                    >
                        Export CSV
                    </Button>
                </Stack>
                <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 1, display: 'block' }}
                >
                    Showing {filters.from} to {filters.to}. Defaults to the last
                    30 days.
                </Typography>
            </Paper>

            {budget ? (
                <Box sx={{ mb: 3 }}>
                    <BudgetWidget budget={budget} />
                </Box>
            ) : null}

            <Grid container spacing={2.5} sx={{ mb: 3 }}>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <StatCard
                        label="Total spend (range)"
                        value={usd(summary.total_cost_usd, 4)}
                        hint={`${int(summary.total_calls)} calls`}
                    />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <StatCard
                        label="Per 1000 articles"
                        value={usd(summary.cost_per_1000_articles, 4)}
                        hint={`${int(summary.article_count)} articles enriched`}
                    />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <StatCard
                        label="Per published page"
                        value={usd(summary.cost_per_page, 4)}
                        hint={`${int(summary.page_count)} pages published`}
                    />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <StatCard
                        label="Tokens (in / out)"
                        value={`${int(summary.total_input_tokens)} / ${int(
                            summary.total_output_tokens
                        )}`}
                        hint="across the range"
                    />
                </Grid>
            </Grid>

            <Stack spacing={3}>
                <Box>
                    <Typography variant="h6" gutterBottom>
                        Spend by model
                    </Typography>
                    <TableContainer component={Paper}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Model</TableCell>
                                    <TableCell align="right">Calls</TableCell>
                                    <TableCell align="right">Input tokens</TableCell>
                                    <TableCell align="right">Output tokens</TableCell>
                                    <TableCell align="right">Cost</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {byModel.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} align="center">
                                            <Typography
                                                variant="body2"
                                                color="text.secondary"
                                                sx={{ py: 2 }}
                                            >
                                                No usage in this range.
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    byModel.map((row) => (
                                        <TableRow key={row.model}>
                                            <TableCell>{row.model}</TableCell>
                                            <TableCell align="right">
                                                {int(row.calls)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {int(row.input_tokens)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {int(row.output_tokens)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {usd(row.cost_usd, 6)}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>

                <Box>
                    <Typography variant="h6" gutterBottom>
                        Spend by skill
                    </Typography>
                    <TableContainer component={Paper}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Skill</TableCell>
                                    <TableCell align="right">Calls</TableCell>
                                    <TableCell align="right">Cost</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {byLabel.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={3} align="center">
                                            <Typography
                                                variant="body2"
                                                color="text.secondary"
                                                sx={{ py: 2 }}
                                            >
                                                No usage in this range.
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    byLabel.map((row) => (
                                        <TableRow key={row.call_label}>
                                            <TableCell>{row.call_label}</TableCell>
                                            <TableCell align="right">
                                                {int(row.calls)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {usd(row.cost_usd, 6)}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>

                <Box>
                    <Typography variant="h6" gutterBottom>
                        Spend by event
                    </Typography>
                    <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mb: 1 }}
                    >
                        Synthesis calls grouped by event (headline from
                        public.pages where available). Enrichment calls run
                        before an event exists (event_id NULL) and are
                        aggregated separately below.
                    </Typography>
                    <TableContainer component={Paper}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Event</TableCell>
                                    <TableCell align="right">Calls</TableCell>
                                    <TableCell align="right">Input tokens</TableCell>
                                    <TableCell align="right">Output tokens</TableCell>
                                    <TableCell align="right">Cost</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {eventRows.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} align="center">
                                            <Typography
                                                variant="body2"
                                                color="text.secondary"
                                                sx={{ py: 2 }}
                                            >
                                                No event-attributed synthesis
                                                calls in this range.
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    eventRows.map((row) => (
                                        <TableRow key={row.event_id}>
                                            <TableCell>
                                                <Typography variant="body2">
                                                    {row.headline ?? (
                                                        <em>
                                                            (no page headline)
                                                        </em>
                                                    )}
                                                </Typography>
                                                <Typography
                                                    variant="caption"
                                                    color="text.secondary"
                                                >
                                                    {row.event_id}
                                                </Typography>
                                            </TableCell>
                                            <TableCell align="right">
                                                {int(row.calls)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {int(row.input_tokens)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {int(row.output_tokens)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {usd(row.cost_usd, 6)}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                                {byEvent.unattributed &&
                                byEvent.unattributed.calls > 0 ? (
                                    <TableRow
                                        sx={{
                                            '& td': {
                                                fontStyle: 'italic',
                                                color: 'text.secondary',
                                            },
                                        }}
                                    >
                                        <TableCell>
                                            Unattributed (enrich, no event)
                                        </TableCell>
                                        <TableCell align="right">
                                            {int(byEvent.unattributed.calls)}
                                        </TableCell>
                                        <TableCell align="right">
                                            {int(
                                                byEvent.unattributed
                                                    .input_tokens
                                            )}
                                        </TableCell>
                                        <TableCell align="right">
                                            {int(
                                                byEvent.unattributed
                                                    .output_tokens
                                            )}
                                        </TableCell>
                                        <TableCell align="right">
                                            {usd(
                                                byEvent.unattributed.cost_usd,
                                                6
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ) : null}
                            </TableBody>
                        </Table>
                        <ListPagination
                            paginator={byEvent.events}
                            onChangePage={onEventPage}
                            onChangePerPage={onEventPerPage}
                        />
                    </TableContainer>
                </Box>

                <Box>
                    <Typography variant="h6" gutterBottom>
                        Spend by day
                    </Typography>
                    <TableContainer component={Paper}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Day</TableCell>
                                    <TableCell align="right">Calls</TableCell>
                                    <TableCell align="right">Input tokens</TableCell>
                                    <TableCell align="right">Output tokens</TableCell>
                                    <TableCell align="right">Cost</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {byDay.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} align="center">
                                            <Typography
                                                variant="body2"
                                                color="text.secondary"
                                                sx={{ py: 2 }}
                                            >
                                                No usage in this range.
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    byDay.map((row) => (
                                        <TableRow key={row.day}>
                                            <TableCell>{row.day}</TableCell>
                                            <TableCell align="right">
                                                {int(row.calls)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {int(row.input_tokens)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {int(row.output_tokens)}
                                            </TableCell>
                                            <TableCell align="right">
                                                {usd(row.cost_usd, 6)}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>
            </Stack>
        </AppLayout>
    );
}
