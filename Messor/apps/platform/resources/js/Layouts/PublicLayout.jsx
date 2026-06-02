import { Link, usePage } from '@inertiajs/react';
import {
    AppBar,
    Box,
    Button,
    Container,
    Stack,
    Toolbar,
    Typography,
} from '@mui/material';

export default function PublicLayout({
    children,
    canLogin = true,
    canRegister = true,
}) {
    const { auth } = usePage().props;
    const user = auth?.user;

    return (
        <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
            <AppBar
                position="static"
                color="inherit"
                elevation={0}
                sx={{
                    borderBottom: '1px solid',
                    borderColor: 'divider',
                    backgroundColor: 'background.paper',
                }}
            >
                <Toolbar sx={{ minHeight: '72px !important' }}>
                    <Typography variant="h6" sx={{ flexGrow: 1 }}>
                        Messor Platform
                    </Typography>

                    <Stack direction="row" spacing={1}>
                        {user ? (
                            <Button
                                component={Link}
                                href={route('dashboard')}
                                variant="contained"
                            >
                                Open Dashboard
                            </Button>
                        ) : (
                            <>
                                {canLogin ? (
                                    <Button
                                        component={Link}
                                        href={route('login')}
                                        color="inherit"
                                    >
                                        Log In
                                    </Button>
                                ) : null}
                                {canRegister ? (
                                    <Button
                                        component={Link}
                                        href={route('register')}
                                        variant="contained"
                                    >
                                        Register
                                    </Button>
                                ) : null}
                            </>
                        )}
                    </Stack>
                </Toolbar>
            </AppBar>

            <Container maxWidth="lg" sx={{ py: { xs: 5, md: 8 } }}>
                {children}
            </Container>
        </Box>
    );
}
