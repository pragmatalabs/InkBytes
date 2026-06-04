import AppLayout from '@/Layouts/AppLayout';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { Head } from '@inertiajs/react';
import { Box, Chip, Paper, Stack, Typography } from '@mui/material';
import DeleteUserForm from './Partials/DeleteUserForm';
import UpdatePasswordForm from './Partials/UpdatePasswordForm';
import UpdateProfileInformationForm from './Partials/UpdateProfileInformationForm';

const roleLabel = (role) =>
    role ? role.charAt(0).toUpperCase() + role.slice(1) : 'Unknown';

export default function Edit({ mustVerifyEmail, status }) {
    const { role, isAdmin } = useAuthRole();

    return (
        <AppLayout
            title="Profile"
            subtitle="Manage account identity, credentials, and account lifecycle."
        >
            <Head title="Profile" />

            <Stack spacing={2.5}>
                <Paper sx={{ p: { xs: 2, sm: 3 } }}>
                    <Box
                        sx={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            flexWrap: 'wrap',
                            gap: 1,
                            mb: 1,
                        }}
                    >
                        <Typography variant="overline" color="text.secondary">
                            Access role
                        </Typography>
                        <Chip
                            label={roleLabel(role)}
                            color={isAdmin ? 'primary' : 'default'}
                            variant={isAdmin ? 'filled' : 'outlined'}
                        />
                    </Box>
                    <UpdateProfileInformationForm
                        mustVerifyEmail={mustVerifyEmail}
                        status={status}
                    />
                </Paper>

                <Paper sx={{ p: { xs: 2, sm: 3 } }}>
                    <UpdatePasswordForm />
                </Paper>

                <Paper sx={{ p: { xs: 2, sm: 3 } }}>
                    <DeleteUserForm />
                </Paper>
            </Stack>
        </AppLayout>
    );
}
