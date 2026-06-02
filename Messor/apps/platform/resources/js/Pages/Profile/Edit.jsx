import AppLayout from '@/Layouts/AppLayout';
import { Head } from '@inertiajs/react';
import { Paper, Stack } from '@mui/material';
import DeleteUserForm from './Partials/DeleteUserForm';
import UpdatePasswordForm from './Partials/UpdatePasswordForm';
import UpdateProfileInformationForm from './Partials/UpdateProfileInformationForm';

export default function Edit({ mustVerifyEmail, status }) {
    return (
        <AppLayout
            title="Profile"
            subtitle="Manage account identity, credentials, and account lifecycle."
        >
            <Head title="Profile" />

            <Stack spacing={2.5}>
                <Paper sx={{ p: { xs: 2, sm: 3 } }}>
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
