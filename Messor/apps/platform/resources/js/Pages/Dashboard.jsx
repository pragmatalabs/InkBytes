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

export default function Dashboard({ metrics = {} }) {
    const regions = metrics.regions ?? [];

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
            subtitle="Monitor the outlet catalogue feeding the ingestion pipeline."
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
