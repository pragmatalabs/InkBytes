import GuestLayout from '@/Layouts/GuestLayout';
import { Head, useForm } from '@inertiajs/react';
import { Alert, Button, Stack, TextField, Typography } from '@mui/material';

export default function ForgotPassword({ status }) {
    const { data, setData, post, processing, errors } = useForm({
        email: '',
    });

    const submit = (event) => {
        event.preventDefault();

        post(route('password.email'));
    };

    return (
        <GuestLayout>
            <Head title="Forgot Password" />

            <Stack component="form" spacing={2} onSubmit={submit}>
                <Typography variant="body2" color="text.secondary">
                    Forgot your password? Enter your email and we will send you a reset
                    link.
                </Typography>

                {status ? <Alert severity="success">{status}</Alert> : null}

                <TextField
                    label="Email"
                    type="email"
                    name="email"
                    value={data.email}
                    onChange={(event) => setData('email', event.target.value)}
                    required
                    autoFocus
                    fullWidth
                    error={Boolean(errors.email)}
                    helperText={errors.email}
                />

                <Stack direction="row" justifyContent="flex-end">
                    <Button type="submit" variant="contained" disabled={processing}>
                        Email Password Reset Link
                    </Button>
                </Stack>
            </Stack>
        </GuestLayout>
    );
}
