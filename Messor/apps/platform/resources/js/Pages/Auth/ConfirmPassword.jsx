import GuestLayout from '@/Layouts/GuestLayout';
import { Head, useForm } from '@inertiajs/react';
import { Button, Stack, TextField, Typography } from '@mui/material';

export default function ConfirmPassword() {
    const { data, setData, post, processing, errors, reset } = useForm({
        password: '',
    });

    const submit = (event) => {
        event.preventDefault();

        post(route('password.confirm'), {
            onFinish: () => reset('password'),
        });
    };

    return (
        <GuestLayout>
            <Head title="Confirm Password" />

            <Stack component="form" spacing={2} onSubmit={submit}>
                <Typography variant="body2" color="text.secondary">
                    This is a secure area of the application. Confirm your password
                    before continuing.
                </Typography>

                <TextField
                    label="Password"
                    type="password"
                    name="password"
                    value={data.password}
                    onChange={(event) => setData('password', event.target.value)}
                    required
                    autoFocus
                    fullWidth
                    error={Boolean(errors.password)}
                    helperText={errors.password}
                />

                <Stack direction="row" justifyContent="flex-end">
                    <Button type="submit" variant="contained" disabled={processing}>
                        Confirm
                    </Button>
                </Stack>
            </Stack>
        </GuestLayout>
    );
}
