import ApplicationLogo from '@/Components/ApplicationLogo';
import { Link } from '@inertiajs/react';
import { Box, Paper, Stack, Typography } from '@mui/material';

export default function GuestLayout({ children }) {
    return (
        <Box
            sx={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                px: 2,
                py: 4,
                backgroundColor: 'background.default',
            }}
        >
            <Stack alignItems="center" spacing={2.5} sx={{ width: '100%' }}>
                <Link href="/">
                    <ApplicationLogo
                        style={{ height: 52, width: 52, fill: '#0f5fd7' }}
                    />
                </Link>

                <Typography variant="h5">Messor Platform</Typography>

                <Paper
                    sx={{
                        width: '100%',
                        maxWidth: 420,
                        p: { xs: 2.5, sm: 3 },
                    }}
                >
                    {children}
                </Paper>
            </Stack>
        </Box>
    );
}
