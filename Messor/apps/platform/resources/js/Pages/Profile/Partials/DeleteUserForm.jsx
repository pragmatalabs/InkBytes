import { useForm } from '@inertiajs/react';
import {
    Alert,
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Stack,
    TextField,
    Typography,
} from '@mui/material';
import { useRef, useState } from 'react';

export default function DeleteUserForm({ className = '' }) {
    const [open, setOpen] = useState(false);
    const passwordInput = useRef(null);

    const {
        data,
        setData,
        delete: destroy,
        processing,
        reset,
        errors,
        clearErrors,
    } = useForm({
        password: '',
    });

    const closeModal = () => {
        setOpen(false);
        clearErrors();
        reset();
    };

    const deleteUser = (event) => {
        event.preventDefault();

        destroy(route('profile.destroy'), {
            preserveScroll: true,
            onSuccess: () => closeModal(),
            onError: () => passwordInput.current?.focus(),
            onFinish: () => reset(),
        });
    };

    return (
        <Box component="section" className={className}>
            <Stack spacing={2.5}>
                <Box>
                    <Typography variant="h6">Delete Account</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        This action permanently deletes your account and all related
                        resources.
                    </Typography>
                </Box>

                <Alert severity="warning" variant="outlined">
                    This operation cannot be undone.
                </Alert>

                <Stack direction="row">
                    <Button color="error" variant="contained" onClick={() => setOpen(true)}>
                        Delete Account
                    </Button>
                </Stack>
            </Stack>

            <Dialog open={open} onClose={closeModal} fullWidth maxWidth="sm">
                <Box component="form" onSubmit={deleteUser}>
                    <DialogTitle>Delete account permanently?</DialogTitle>
                    <DialogContent>
                        <Stack spacing={2} sx={{ pt: 1 }}>
                            <Typography variant="body2" color="text.secondary">
                                Enter your password to confirm this deletion.
                            </Typography>

                            <TextField
                                label="Password"
                                type="password"
                                name="password"
                                value={data.password}
                                onChange={(event) =>
                                    setData('password', event.target.value)
                                }
                                inputRef={passwordInput}
                                required
                                autoFocus
                                fullWidth
                                error={Boolean(errors.password)}
                                helperText={errors.password}
                            />
                        </Stack>
                    </DialogContent>
                    <DialogActions sx={{ px: 3, pb: 2.5 }}>
                        <Button onClick={closeModal}>Cancel</Button>
                        <Button type="submit" color="error" variant="contained" disabled={processing}>
                            Delete Account
                        </Button>
                    </DialogActions>
                </Box>
            </Dialog>
        </Box>
    );
}
