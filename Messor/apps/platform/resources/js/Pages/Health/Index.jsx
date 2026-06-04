import AppLayout from '@/Layouts/AppLayout';
import { EmptyState } from '@/Components/ListStates';
import { Head } from '@inertiajs/react';
import {
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

// Map a component status to a MUI colour + label. Unknown/missing -> grey.
function statusChip(status) {
    switch (status) {
        case 'up':
            return { color: 'success', label: 'Up' };
        case 'down':
            return { color: 'error', label: 'Down' };
        case 'unreachable':
            return { color: 'error', label: 'Unreachable' };
        default:
            return { color: 'default', label: 'Unknown' };
    }
}

function ServiceCard({ title, status, metric, detail, latency, error }) {
    const chip = statusChip(status);

    return (
        <Card sx={{ height: '100%' }}>
            <CardContent>
                <Stack
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    sx={{ mb: 1 }}
                >
                    <Typography variant="subtitle2" color="text.secondary">
                        {title}
                    </Typography>
                    <Chip size="small" color={chip.color} label={chip.label} />
                </Stack>

                <Typography variant="h6">{metric ?? '—'}</Typography>

                {detail ? (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        {detail}
                    </Typography>
                ) : null}

                {error ? (
                    <Typography variant="caption" color="error" sx={{ mt: 1, display: 'block' }}>
                        {error}
                    </Typography>
                ) : null}

                <Typography variant="caption" color="text.secondary" sx={{ mt: 1.25, display: 'block' }}>
                    {Number.isFinite(latency) ? `${latency} ms` : '—'}
                </Typography>
            </CardContent>
        </Card>
    );
}

export default function HealthIndex({ health = {} }) {
    const pg = health.postgres ?? {};
    const curator = health.curator ?? {};
    const messor = health.messor ?? {};
    const rabbit = health.rabbitmq ?? {};

    const pgCounts = pg.counts ?? {};
    const curatorMetrics = curator.metrics ?? {};
    const queues = rabbit.queues ?? [];

    return (
        <AppLayout
            title="System Health"
            subtitle="At-a-glance pipeline liveness: Postgres, Curator, Messor and RabbitMQ."
        >
            <Head title="System Health" />

            <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <ServiceCard
                        title="Postgres"
                        status={pg.status}
                        metric={
                            pg.status === 'up'
                                ? `${numberFormatter.format(pgCounts.articles ?? 0)} articles`
                                : null
                        }
                        detail={
                            pg.status === 'up'
                                ? `${numberFormatter.format(pgCounts.enriched ?? 0)} enriched · ${numberFormatter.format(
                                      pgCounts.events ?? 0,
                                  )} events · ${numberFormatter.format(
                                      pgCounts.pages_published ?? 0,
                                  )}/${numberFormatter.format(pgCounts.pages ?? 0)} pages`
                                : null
                        }
                        latency={pg.latency_ms}
                        error={pg.error}
                    />
                </Grid>

                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <ServiceCard
                        title="Curator API"
                        status={curator.status}
                        metric={
                            curator.status === 'up' && curatorMetrics.pages_published != null
                                ? `${numberFormatter.format(curatorMetrics.pages_published)} pages published`
                                : null
                        }
                        detail={
                            curator.status === 'up'
                                ? `${
                                      curatorMetrics.articles_total != null
                                          ? numberFormatter.format(curatorMetrics.articles_total)
                                          : '—'
                                  } articles · ${
                                      curatorMetrics.events_total != null
                                          ? numberFormatter.format(curatorMetrics.events_total)
                                          : '—'
                                  } events`
                                : null
                        }
                        latency={curator.latency_ms}
                        error={curator.error}
                    />
                </Grid>

                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <ServiceCard
                        title="Messor API"
                        status={messor.status}
                        metric={messor.status === 'up' ? 'Reachable' : null}
                        detail="Harvester FastAPI (:8050)"
                        latency={messor.latency_ms}
                        error={messor.error}
                    />
                </Grid>

                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                    <ServiceCard
                        title="RabbitMQ"
                        status={rabbit.status}
                        metric={rabbit.status === 'up' ? 'Broker up' : null}
                        detail="Management API"
                        latency={rabbit.latency_ms}
                        error={rabbit.error}
                    />
                </Grid>
            </Grid>

            <Card sx={{ mt: 2.5 }}>
                <CardContent>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
                        Queue Depths
                    </Typography>
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Queue</TableCell>
                                    <TableCell align="right">Messages</TableCell>
                                    <TableCell align="right">Present</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {queues.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={3}>
                                            <EmptyState
                                                title="No queue data"
                                                description="RabbitMQ is unreachable or reported no queues."
                                            />
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    queues.map((q) => (
                                        <TableRow key={q.name}>
                                            <TableCell>
                                                <Typography variant="body2" fontFamily="monospace">
                                                    {q.name}
                                                </Typography>
                                            </TableCell>
                                            <TableCell align="right">
                                                {q.messages != null
                                                    ? numberFormatter.format(q.messages)
                                                    : '—'}
                                            </TableCell>
                                            <TableCell align="right">
                                                <Chip
                                                    size="small"
                                                    variant="outlined"
                                                    color={q.present ? 'success' : 'default'}
                                                    label={q.present ? 'yes' : 'no'}
                                                />
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </CardContent>
            </Card>

            <Box sx={{ mt: 2.5 }}>
                <Typography variant="body2" color="text.secondary">
                    Last harvest: {relativeTime(health.last_harvest)}
                    {health.checked_at ? ` · checked ${relativeTime(health.checked_at)}` : ''}
                </Typography>
            </Box>
        </AppLayout>
    );
}
