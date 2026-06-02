import GuestLayout from '@/Layouts/GuestLayout';
import { Head, Link, useForm } from '@inertiajs/react';
import { Button, Stack, TextField } from '@mui/material';

export default function Register() {
    const { data, setData, post, processing, errors, reset } = useForm({
        name: '',
        email: '',
        password: '',
        password_confirmation: '',
    });

    const submit = (event) => {
        event.preventDefault();

        post(route('register'), {
            onFinish: () => reset('password', 'password_confirmation'),
        });
    };

    return (
        <GuestLayout>
            <Head title="Register" />

            <Stack component="form" spacing={2} onSubmit={submit}>
                <TextField
                    label="Name"
                    name="name"
                    value={data.name}
                    onChange={(event) => setData('name', event.target.value)}
                    autoComplete="name"
                    required
                    autoFocus
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
                    autoComplete="username"
                    required
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
                    autoComplete="new-password"
                    required
                    fullWidth
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
                    required
                    fullWidth
                    error={Boolean(errors.password_confirmation)}
                    helperText={errors.password_confirmation}
                />

                <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Button component={Link} href={route('login')} variant="text" size="small">
                        Already registered?
                    </Button>

                    <Button type="submit" variant="contained" disabled={processing}>
                        Register
                    </Button>
                </Stack>
            </Stack>
        </GuestLayout>
    );
}
