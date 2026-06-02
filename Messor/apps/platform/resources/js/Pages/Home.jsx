import PublicLayout from '@/Layouts/PublicLayout';
import { Head, Link } from '@inertiajs/react';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import HubRoundedIcon from '@mui/icons-material/HubRounded';
import LayersRoundedIcon from '@mui/icons-material/LayersRounded';
import StorageRoundedIcon from '@mui/icons-material/StorageRounded';
import {
    Box,
    Button,
    Card,
    CardContent,
    Grid,
    Stack,
    Typography,
} from '@mui/material';

const highlights = [
    {
        icon: LayersRoundedIcon,
        title: 'Laravel + Inertia',
        description:
            'Server-side route definitions with SPA-like navigation and fast page transitions.',
    },
    {
        icon: HubRoundedIcon,
        title: 'Monorepo Workflow',
        description:
            'Shared contracts and coordinated services across platform, scraper, and infrastructure.',
    },
    {
        icon: StorageRoundedIcon,
        title: 'PostgreSQL Ready',
        description:
            'Structured storage for ingestion metadata, queue orchestration, and audit trails.',
    },
];

export default function Home({ auth, canLogin, canRegister }) {
    return (
        <PublicLayout canLogin={canLogin} canRegister={canRegister}>
            <Head title="Home" />

            <Box
                sx={{
                    borderRadius: 3,
                    border: '1px solid',
                    borderColor: 'divider',
                    background:
                        'linear-gradient(145deg, rgba(15,95,215,0.10) 0%, rgba(12,127,111,0.10) 100%)',
                    p: { xs: 3, md: 5 },
                }}
            >
                <Typography variant="h3" sx={{ fontSize: { xs: 30, md: 44 } }}>
                    Laravel + Inertia Platform for Messor
                </Typography>
                <Typography
                    variant="body1"
                    color="text.secondary"
                    sx={{ mt: 1.5, maxWidth: 760 }}
                >
                    Route-driven React pages powered by Laravel, themed with MUI, and
                    connected to a Dockerized data stack.
                </Typography>

                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mt: 3 }}>
                    {auth?.user ? (
                        <Button
                            component={Link}
                            href={route('dashboard')}
                            variant="contained"
                            endIcon={<ArrowForwardRoundedIcon />}
                        >
                            Open Dashboard
                        </Button>
                    ) : (
                        <>
                            {canLogin ? (
                                <Button
                                    component={Link}
                                    href={route('login')}
                                    variant="contained"
                                    endIcon={<ArrowForwardRoundedIcon />}
                                >
                                    Sign In
                                </Button>
                            ) : null}
                            {canRegister ? (
                                <Button
                                    component={Link}
                                    href={route('register')}
                                    variant="outlined"
                                >
                                    Create Account
                                </Button>
                            ) : null}
                        </>
                    )}
                </Stack>
            </Box>

            <Grid container spacing={2} sx={{ mt: 1.5 }}>
                {highlights.map((item) => {
                    const Icon = item.icon;

                    return (
                        <Grid key={item.title} size={{ xs: 12, md: 4 }}>
                            <Card sx={{ height: '100%' }}>
                                <CardContent>
                                    <Stack direction="row" spacing={1.25} alignItems="center">
                                        <Icon color="primary" />
                                        <Typography variant="h6">{item.title}</Typography>
                                    </Stack>
                                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1.25 }}>
                                        {item.description}
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>
                    );
                })}
            </Grid>
        </PublicLayout>
    );
}
