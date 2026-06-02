import { Link, useForm, usePage } from '@inertiajs/react';
import { Alert, Box, Button, Stack, TextField, Typography } from '@mui/material';

export default function UpdateProfileInformation({
    mustVerifyEmail,
    status,
    className = '',
}) {
    const user = usePage().props.auth.user;

    const { data, setData, patch, errors, processing, recentlySuccessful } =
        useForm({
            name: user.name,
            email: user.email,
        });

    const submit = (event) => {
        event.preventDefault();
        patch(route('profile.update'));
    };

    return (
        <Box component="section" className={className}>
            <Stack spacing={2.5}>
                <Box>
                    <Typography variant="h6">Profile Information</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        Update your account profile information and email address.
                    </Typography>
                </Box>

                <Stack component="form" spacing={2} onSubmit={submit}>
                    <TextField
                        label="Name"
                        name="name"
                        value={data.name}
                        onChange={(event) => setData('name', event.target.value)}
                        required
                        autoComplete="name"
                        fullWidth
                        error={Boolean(errors.name)}
                        helperText={errors.name}
                    />

                    <TextField
                        label="Email"
                        type="email"
                        name="email"
                        value={data.email}
                        onChange={(event) => setData('email', event.target.value)}
                        required
                        autoComplete="username"
                        fullWidth
                        error={Boolean(errors.email)}
                        helperText={errors.email}
                    />

                    {mustVerifyEmail && user.email_verified_at === null ? (
                        <Stack spacing={1}>
                            <Alert severity="warning" variant="outlined">
                                Your email address is unverified.
                            </Alert>

                            <Button
                                component={Link}
                                href={route('verification.send')}
                                method="post"
                                as="button"
                                variant="text"
                                size="small"
                                sx={{ alignSelf: 'flex-start' }}
                            >
                                Re-send verification email
                            </Button>

                            {status === 'verification-link-sent' ? (
                                <Alert severity="success">
                                    A new verification link has been sent to your email
                                    address.
                                </Alert>
                            ) : null}
                        </Stack>
                    ) : null}

                    <Stack direction="row" spacing={1.5} alignItems="center">
                        <Button type="submit" variant="contained" disabled={processing}>
                            Save
                        </Button>

                        {recentlySuccessful ? (
                            <Typography variant="body2" color="text.secondary">
                                Saved.
                            </Typography>
                        ) : null}
                    </Stack>
                </Stack>
            </Stack>
        </Box>
    );
}
