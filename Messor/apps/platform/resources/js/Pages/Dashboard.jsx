import AppLayout from '@/Layouts/AppLayout';
import { Head, Link } from '@inertiajs/react';
import {
    Box,
    Button,
    Card,
    CardContent,
    Grid,
    Stack,
    Typography,
} from '@mui/material';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';

const numberFormatter = new Intl.NumberFormat();

export default function Dashboard({ metrics = {} }) {
    const cards = [
        {
            label: 'Sources',
            value: numberFormatter.format(metrics.total_sources ?? 0),
            description: `${numberFormatter.format(metrics.active_sources ?? 0)} active sources`,
        },
        {
            label: 'Runs',
            value: numberFormatter.format(metrics.total_runs ?? 0),
            description: `${numberFormatter.format(metrics.running_runs ?? 0)} running / ${numberFormatter.format(metrics.failed_runs ?? 0)} failed`,
        },
        {
            label: 'Articles (24h)',
            value: numberFormatter.format(metrics.articles_last_24h ?? 0),
            description: 'Throughput from recent scraper sessions.',
        },
    ];

    return (
        <AppLayout
            title="Control Center"
            subtitle="Monitor ingestion, data sources, and execution runs from one place."
        >
            <Head title="Dashboard" />

            <Grid container spacing={2}>
                {cards.map((card) => (
                    <Grid key={card.label} size={{ xs: 12, md: 4 }}>
                        <Card sx={{ height: '100%' }}>
                            <CardContent>
                                <Typography
                                    variant="subtitle2"
                                    color="text.secondary"
                                    gutterBottom
                                >
                                    {card.label}
                                </Typography>
                                <Typography variant="h6">{card.value}</Typography>
                                <Typography
                                    variant="body2"
                                    color="text.secondary"
                                    sx={{ mt: 1.25 }}
                                >
                                    {card.description}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            <Card sx={{ mt: 2.5 }}>
                <CardContent>
                    <Typography variant="h6">Quick Actions</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
                        Navigate directly to ingestion sources or latest execution runs.
                    </Typography>

                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mt: 2.5 }}>
                        <Button
                            component={Link}
                            href={route('sources.index')}
                            variant="contained"
                            endIcon={<ArrowForwardRoundedIcon />}
                        >
                            View Sources
                        </Button>
                        <Button
                            component={Link}
                            href={route('runs.index')}
                            variant="outlined"
                            endIcon={<ArrowForwardRoundedIcon />}
                        >
                            View Runs
                        </Button>
                    </Stack>
                </CardContent>
            </Card>

            <Box
                sx={{
                    mt: 2.5,
                    borderRadius: 2.5,
                    background:
                        'linear-gradient(130deg, rgba(15,95,215,0.1) 0%, rgba(12,127,111,0.08) 100%)',
                    border: '1px solid',
                    borderColor: 'divider',
                    p: { xs: 2, sm: 2.5 },
                }}
            >
                <Typography variant="subtitle1" fontWeight={700}>
                    Latest Execution Snapshot
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
                    {metrics.latest_run
                        ? `Run ${metrics.latest_run.id} from ${metrics.latest_run.source} is ${metrics.latest_run.status} with ${numberFormatter.format(metrics.latest_run.articles)} articles processed.`
                        : 'No scraper runs found yet. Trigger a scrape to populate execution data.'}
                </Typography>
            </Box>
        </AppLayout>
    );
}
