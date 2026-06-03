import AppLayout from '@/Layouts/AppLayout';
import { Head, Link } from '@inertiajs/react';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import {
    Box,
    Button,
    Card,
    CardContent,
    Grid,
    Stack,
    Typography,
} from '@mui/material';

const numberFormatter = new Intl.NumberFormat();
const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 });

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

export default function Dashboard({ metrics = {} }) {
    const regions = metrics.regions ?? [];
    const p = metrics.pipeline ?? {};

    const pipelineCards = [
        { label: 'Articles', value: numberFormatter.format(p.articles ?? 0), description: `${numberFormatter.format(p.enriched ?? 0)} enriched` },
        { label: 'Events', value: numberFormatter.format(p.events ?? 0), description: 'Clustered by Curator' },
        { label: 'Pages', value: numberFormatter.format(p.pages_published ?? 0), description: `${numberFormatter.format(p.pages ?? 0)} total` },
        { label: 'LLM Spend', value: usd.format(p.spend_usd ?? 0), description: 'Across all calls' },
        { label: 'Last Harvest', value: relativeTime(p.last_harvest), description: 'Most recent article scraped' },
    ];

    const cards = [
        {
            label: 'Outlets',
            value: numberFormatter.format(metrics.total_outlets ?? 0),
            description: `${numberFormatter.format(metrics.active_outlets ?? 0)} active`,
        },
        {
            label: 'Active Outlets',
            value: numberFormatter.format(metrics.active_outlets ?? 0),
            description: 'Currently harvested by Messor + Curator.',
        },
        {
            label: 'High Priority',
            value: numberFormatter.format(metrics.high_priority_outlets ?? 0),
            description: 'Priority 1 outlets.',
        },
    ];

    return (
        <AppLayout
            title="Control Center"
            subtitle="Live pipeline health and the outlet catalogue feeding it."
        >
            <Head title="Dashboard" />

            {p.available !== false && (
                <>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
                        Pipeline
                    </Typography>
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        {pipelineCards.map((card) => (
                            <Grid key={card.label} size={{ xs: 6, md: 'grow' }}>
                                <Card sx={{ height: '100%' }}>
                                    <CardContent>
                                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                                            {card.label}
                                        </Typography>
                                        <Typography variant="h6">{card.value}</Typography>
                                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1.25 }}>
                                            {card.description}
                                        </Typography>
                                    </CardContent>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
                        Outlets
                    </Typography>
                </>
            )}

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
                    <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mt: 0.75 }}
                    >
                        Manage the canonical outlet catalogue that Curator and
                        Messor read from.
                    </Typography>

                    <Stack
                        direction={{ xs: 'column', sm: 'row' }}
                        spacing={1.5}
                        sx={{ mt: 2.5 }}
                    >
                        <Button
                            component={Link}
                            href={route('outlets.index')}
                            variant="contained"
                            endIcon={<ArrowForwardRoundedIcon />}
                        >
                            Manage Outlets
                        </Button>
                        <Button
                            component={Link}
                            href={route('scraping.index')}
                            variant="outlined"
                            endIcon={<ArrowForwardRoundedIcon />}
                        >
                            Scraping
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
                    Coverage by Region
                </Typography>
                {regions.length === 0 ? (
                    <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mt: 0.75 }}
                    >
                        No outlets configured yet. Add one to populate coverage.
                    </Typography>
                ) : (
                    <Stack
                        direction="row"
                        flexWrap="wrap"
                        spacing={2}
                        sx={{ mt: 1.5 }}
                    >
                        {regions.map((row) => (
                            <Box key={row.region}>
                                <Typography variant="h6">
                                    {numberFormatter.format(row.count)}
                                </Typography>
                                <Typography
                                    variant="caption"
                                    color="text.secondary"
                                >
                                    {row.region}
                                </Typography>
                            </Box>
                        ))}
                    </Stack>
                )}
            </Box>
        </AppLayout>
    );
}
