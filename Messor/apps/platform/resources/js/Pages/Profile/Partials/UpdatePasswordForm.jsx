import { useForm } from '@inertiajs/react';
import { Box, Button, Stack, TextField, Typography } from '@mui/material';
import { useRef } from 'react';

export default function UpdatePasswordForm({ className = '' }) {
    const passwordInput = useRef(null);
    const currentPasswordInput = useRef(null);

    const {
        data,
        setData,
        errors,
        put,
        reset,
        processing,
        recentlySuccessful,
    } = useForm({
        current_password: '',
        password: '',
        password_confirmation: '',
    });

    const updatePassword = (event) => {
        event.preventDefault();

        put(route('password.update'), {
            preserveScroll: true,
            onSuccess: () => reset(),
            onError: (formErrors) => {
                if (formErrors.password) {
                    reset('password', 'password_confirmation');
                    passwordInput.current?.focus();
                }

                if (formErrors.current_password) {
                    reset('current_password');
                    currentPasswordInput.current?.focus();
                }
            },
        });
    };

    return (
        <Box component="section" className={className}>
            <Stack spacing={2.5}>
                <Box>
                    <Typography variant="h6">Update Password</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        Use a long, random password to keep your account secure.
                    </Typography>
                </Box>

                <Stack component="form" spacing={2} onSubmit={updatePassword}>
                    <TextField
                        label="Current Password"
                        type="password"
                        name="current_password"
                        value={data.current_password}
                        onChange={(event) =>
                            setData('current_password', event.target.value)
                        }
                        autoComplete="current-password"
                        fullWidth
                        inputRef={currentPasswordInput}
                        error={Boolean(errors.current_password)}
                        helperText={errors.current_password}
                    />

                    <TextField
                        label="New Password"
                        type="password"
                        name="password"
                        value={data.password}
                        onChange={(event) => setData('password', event.target.value)}
                        autoComplete="new-password"
                        fullWidth
                        inputRef={passwordInput}
                        error={Boolean(errors.password)}
                        helperText={errors.password}
                    />

                    <TextField
                        label="Confirm Password"
                        type="password"
                        name="password_confirmation"
                        value={data.password_confirmation}
                        onChange={(event) =>
                            setData('password_confirmation', event.target.value)
                        }
                        autoComplete="new-password"
                        fullWidth
                        error={Boolean(errors.password_confirmation)}
                        helperText={errors.password_confirmation}
                    />

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
