import AppLayout from '@/Layouts/AppLayout';
import { EmptyState } from '@/Components/ListStates';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { Head, router, usePage } from '@inertiajs/react';
import {
    Box,
    Chip,
    FormControl,
    MenuItem,
    Paper,
    Select,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
} from '@mui/material';
import { useState } from 'react';

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
    const { auth } = usePage().props;
    const { isAdmin } = useAuthRole();
    const currentUserId = auth?.user?.id;
    const [savingId, setSavingId] = useState(null);

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
                                        <EmptyState title="No users." />
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
        </AppLayout>
    );
}
