import GuestLayout from '@/Layouts/GuestLayout';
import { Head, Link, useForm } from '@inertiajs/react';
import { Alert, Button, Stack, Typography } from '@mui/material';

export default function VerifyEmail({ status }) {
    const { post, processing } = useForm({});

    const submit = (event) => {
        event.preventDefault();

        post(route('verification.send'));
    };

    return (
        <GuestLayout>
            <Head title="Email Verification" />

            <Stack component="form" spacing={2} onSubmit={submit}>
                <Typography variant="body2" color="text.secondary">
                    Before getting started, verify your email address by clicking the
                    link we emailed you. If you did not receive one, we can send another.
                </Typography>

                {status === 'verification-link-sent' ? (
                    <Alert severity="success">
                        A new verification link has been sent to your email address.
                    </Alert>
                ) : null}

                <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Button type="submit" variant="contained" disabled={processing}>
                        Resend Verification Email
                    </Button>

                    <Button
                        component={Link}
                        href={route('logout')}
                        method="post"
                        as="button"
                        variant="text"
                    >
                        Log Out
                    </Button>
                </Stack>
            </Stack>
        </GuestLayout>
    );
}
