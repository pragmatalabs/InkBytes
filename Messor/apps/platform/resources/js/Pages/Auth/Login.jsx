import GuestLayout from '@/Layouts/GuestLayout';
import { Head, Link, useForm } from '@inertiajs/react';
import {
    Alert,
    Button,
    Checkbox,
    FormControlLabel,
    Stack,
    TextField,
} from '@mui/material';

export default function Login({ status, canResetPassword }) {
    const { data, setData, post, processing, errors, reset } = useForm({
        email: '',
        password: '',
        remember: false,
    });

    const submit = (event) => {
        event.preventDefault();

        post(route('login'), {
            onFinish: () => reset('password'),
        });
    };

    return (
        <GuestLayout>
            <Head title="Log in" />

            <Stack component="form" spacing={2} onSubmit={submit}>
                {status ? <Alert severity="success">{status}</Alert> : null}

                <TextField
                    label="Email"
                    type="email"
                    name="email"
                    value={data.email}
                    onChange={(event) => setData('email', event.target.value)}
                    autoComplete="username"
                    required
                    autoFocus
                    fullWidth
                    error={Boolean(errors.email)}
                    helperText={errors.email}
                />

                <TextField
                    label="Password"
                    type="password"
                    name="password"
                    value={data.password}
                    onChange={(event) => setData('password', event.target.value)}
                    autoComplete="current-password"
                    required
                    fullWidth
                    error={Boolean(errors.password)}
                    helperText={errors.password}
                />

                <FormControlLabel
                    control={
                        <Checkbox
                            name="remember"
                            checked={data.remember}
                            onChange={(event) =>
                                setData('remember', event.target.checked)
                            }
                        />
                    }
                    label="Remember me"
                />

                <Stack direction="row" justifyContent="space-between" alignItems="center">
                    {canResetPassword ? (
                        <Button
                            component={Link}
                            href={route('password.request')}
                            variant="text"
                            size="small"
                        >
                            Forgot your password?
                        </Button>
                    ) : (
                        <span />
                    )}

                    <Button type="submit" variant="contained" disabled={processing}>
                        Log In
                    </Button>
                </Stack>
            </Stack>
        </GuestLayout>
    );
}
