import AppLayout from '@/Layouts/AppLayout';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { Head, router, usePage } from '@inertiajs/react';
import {
    Alert,
    Box,
    Chip,
    FormControl,
    MenuItem,
    Paper,
    Select,
    Snackbar,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';

const formatWhen = (iso) => (iso ? new Date(iso).toLocaleDateString() : '—');

const roleChipColor = (role) => {
    if (role === 'admin') {
        return 'primary';
    }
    if (role === 'operator') {
        return 'info';
    }

    return 'default';
};

export default function UsersIndex({ users = [], roles = [] }) {
    const { flash, auth } = usePage().props;
    const { isAdmin } = useAuthRole();
    const currentUserId = auth?.user?.id;
    const [snack, setSnack] = useState(null);
    const [savingId, setSavingId] = useState(null);

    useEffect(() => {
        if (flash?.success) {
            setSnack({ severity: 'success', message: flash.success });
        } else if (flash?.error) {
            setSnack({ severity: 'error', message: flash.error });
        }
    }, [flash]);

    const changeRole = (user, role) => {
        if (role === user.role) {
            return;
        }

        setSavingId(user.id);
        router.put(
            route('users.update-role', user.id),
            { role },
            {
                preserveScroll: true,
                onFinish: () => setSavingId(null),
            },
        );
    };

    return (
        <AppLayout
            title="Users"
            subtitle="Manage Backoffice access. Roles gate dangerous actions (ADR-0005)."
        >
            <Head title="Users" />

            <Paper variant="outlined">
                <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Name</TableCell>
                                <TableCell>Email</TableCell>
                                <TableCell>Created</TableCell>
                                <TableCell sx={{ width: 200 }}>Role</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {users.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={4}>
                                        <Typography
                                            variant="body2"
                                            color="text.secondary"
                                            sx={{ py: 2, textAlign: 'center' }}
                                        >
                                            No users.
                                        </Typography>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                users.map((user) => (
                                    <TableRow key={user.id} hover>
                                        <TableCell>
                                            <Box
                                                sx={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 1,
                                                }}
                                            >
                                                {user.name}
                                                {user.id === currentUserId ? (
                                                    <Chip
                                                        size="small"
                                                        label="You"
                                                        variant="outlined"
                                                    />
                                                ) : null}
                                            </Box>
                                        </TableCell>
                                        <TableCell>{user.email}</TableCell>
                                        <TableCell>
                                            {formatWhen(user.created_at)}
                                        </TableCell>
                                        <TableCell>
                                            {isAdmin ? (
                                                <FormControl
                                                    size="small"
                                                    fullWidth
                                                >
                                                    <Select
                                                        value={user.role}
                                                        disabled={
                                                            savingId === user.id
                                                        }
                                                        onChange={(event) =>
                                                            changeRole(
                                                                user,
                                                                event.target
                                                                    .value,
                                                            )
                                                        }
                                                    >
                                                        {roles.map((role) => (
                                                            <MenuItem
                                                                key={role}
                                                                value={role}
                                                            >
                                                                {role}
                                                            </MenuItem>
                                                        ))}
                                                    </Select>
                                                </FormControl>
                                            ) : (
                                                <Chip
                                                    size="small"
                                                    label={user.role}
                                                    color={roleChipColor(
                                                        user.role,
                                                    )}
                                                />
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            </Paper>

            <Snackbar
                open={Boolean(snack)}
                autoHideDuration={5000}
                onClose={() => setSnack(null)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            >
                {snack ? (
                    <Alert
                        severity={snack.severity}
                        onClose={() => setSnack(null)}
                        variant="filled"
                    >
                        {snack.message}
                    </Alert>
                ) : undefined}
            </Snackbar>
        </AppLayout>
    );
}
