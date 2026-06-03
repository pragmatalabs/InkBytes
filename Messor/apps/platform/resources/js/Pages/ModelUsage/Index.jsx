import AppLayout from '@/Layouts/AppLayout';
import { Head } from '@inertiajs/react';
import {
    Box,
    Grid,
    Paper,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography,
} from '@mui/material';

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

export default function ModelUsageIndex({
    summary = {},
    byModel = [],
    byLabel = [],
    byDay = [],
}) {
    return (
        <AppLayout
            title="Cost & Usage"
            subtitle="LLM spend persisted by Curator (backoffice.model_usage). Read-only — one row per completed call."
        >
            <Head title="Cost & Usage" />

            <Grid container spacing={2.5} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={6} md={3}>
                    <StatCard
                        label="Total spend"
                        value={usd(summary.total_cost_usd, 4)}
                        hint={`${int(summary.total_calls)} calls`}
                    />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <StatCard
                        label="Per 1000 articles"
                        value={usd(summary.cost_per_1000_articles, 4)}
                        hint={`${int(summary.article_count)} articles enriched`}
                    />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <StatCard
                        label="Per published page"
                        value={usd(summary.cost_per_page, 4)}
                        hint={`${int(summary.page_count)} pages published`}
                    />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <StatCard
                        label="Tokens (in / out)"
                        value={`${int(summary.total_input_tokens)} / ${int(
                            summary.total_output_tokens
                        )}`}
                        hint="across all calls"
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
                                                No usage recorded yet. Rows appear
                                                as Curator runs LLM calls.
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
                                                No usage recorded yet.
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
                        Spend by day (last 30)
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
                                                No usage recorded yet.
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
