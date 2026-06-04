import AppLayout from '@/Layouts/AppLayout';
import { EmptyState } from '@/Components/ListStates';
import { useToast } from '@/providers/ToastProvider';
import { Head, Link, router, useForm } from '@inertiajs/react';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import HistoryRoundedIcon from '@mui/icons-material/HistoryRounded';
import ScienceRoundedIcon from '@mui/icons-material/ScienceRounded';
import SyncRoundedIcon from '@mui/icons-material/SyncRounded';
import {
    Alert,
    Box,
    Button,
    Chip,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    FormControl,
    FormControlLabel,
    IconButton,
    InputLabel,
    MenuItem,
    Paper,
    Select,
    Stack,
    Switch,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TextField,
    Tooltip,
    Typography,
} from '@mui/material';
import { useState } from 'react';

const emptyKey = {
    provider: 'anthropic',
    label: '',
    value: '',
    active: true,
};

export default function ApiKeysIndex({ keys = [], providers = [], tracking = null }) {
    const { showToast } = useToast();
    const providerOptions = providers.length ? providers : ['anthropic', 'openai'];

    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [confirmDelete, setConfirmDelete] = useState(null);
    const [testing, setTesting] = useState(null);
    const [testResult, setTestResult] = useState(null);

    const form = useForm({ ...emptyKey });
    const isEditing = editingId !== null;

    const openCreate = () => {
        setEditingId(null);
        form.clearErrors();
        form.setData({ ...emptyKey });
        setDialogOpen(true);
    };

    const openRotate = (key) => {
        setEditingId(key.id);
        form.clearErrors();
        form.setData({
            provider: key.provider,
            label: key.label ?? '',
            value: '', // never prefilled — secret is write-only
            active: Boolean(key.active),
        });
        setDialogOpen(true);
    };

    const closeDialog = () => {
        setDialogOpen(false);
        setEditingId(null);
    };

    const submit = (event) => {
        event.preventDefault();
        const onSuccess = () => closeDialog();
        if (isEditing) {
            form.put(route('api-keys.update', editingId), { onSuccess });
        } else {
            form.post(route('api-keys.store'), { onSuccess });
        }
    };

    const doDelete = () => {
        if (!confirmDelete) {
            return;
        }
        router.delete(route('api-keys.destroy', confirmDelete.id), {
            onFinish: () => setConfirmDelete(null),
        });
    };

    const testKey = async (key) => {
        setTesting(key.id);
        setTestResult(null);
        try {
            // window.axios (bootstrap.js) sends the XSRF-TOKEN cookie + the
            // X-Requested-With header Laravel expects, so no CSRF meta tag needed.
            const { data } = await window.axios.post(
                route('api-keys.test', key.id)
            );
            showToast(
                `${key.provider}: ${data.message}`,
                data.ok ? 'success' : 'warning',
            );
            setTestResult({ id: key.id, ok: data.ok });
        } catch (e) {
            showToast(`Test failed: ${e.message}`, 'error');
        } finally {
            setTesting(null);
        }
    };

    return (
        <AppLayout
            title="API Keys"
            subtitle="Provider keys for management (store, rotate, test). Encrypted at rest and masked. Curator itself loads its live keys from env (ADR-0004)."
        >
            <Head title="API Keys" />

            <Alert severity="info" icon={false} sx={{ mb: 2 }}>
                <strong>One active key per provider.</strong> Activating a key
                automatically deactivates the previously-active key of the same
                provider (audited).{' '}
                {tracking?.note ?? 'Not tracked — Curator uses env keys (ADR-0004).'}{' '}
                Last-used timestamps and spend-per-key are N/A by design.
            </Alert>

            <Stack
                direction="row"
                justifyContent="flex-end"
                spacing={1}
                sx={{ mb: 2 }}
            >
                <Button
                    component={Link}
                    href={route('api-keys.history')}
                    variant="outlined"
                    startIcon={<HistoryRoundedIcon />}
                >
                    History
                </Button>
                <Button
                    variant="contained"
                    startIcon={<AddRoundedIcon />}
                    onClick={openCreate}
                >
                    Add Key
                </Button>
            </Stack>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Provider</TableCell>
                            <TableCell>Label</TableCell>
                            <TableCell>Key</TableCell>
                            <TableCell>Active</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {keys.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5}>
                                    <EmptyState
                                        title="No keys stored yet"
                                        description="Add a provider key to store, rotate, and test it."
                                    />
                                </TableCell>
                            </TableRow>
                        ) : (
                            keys.map((key) => (
                                <TableRow key={key.id} hover>
                                    <TableCell>
                                        <Chip
                                            size="small"
                                            label={key.provider}
                                            variant="outlined"
                                        />
                                    </TableCell>
                                    <TableCell>{key.label || '—'}</TableCell>
                                    <TableCell>
                                        <Typography
                                            variant="body2"
                                            sx={{ fontFamily: 'monospace' }}
                                        >
                                            {key.masked}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Chip
                                            size="small"
                                            label={
                                                key.active ? 'active' : 'inactive'
                                            }
                                            color={
                                                key.active ? 'success' : 'default'
                                            }
                                            variant={
                                                key.active ? 'filled' : 'outlined'
                                            }
                                        />
                                    </TableCell>
                                    <TableCell align="right">
                                        <Tooltip title="Test key against provider">
                                            <span>
                                                <IconButton
                                                    size="small"
                                                    onClick={() => testKey(key)}
                                                    disabled={testing === key.id}
                                                >
                                                    {testing === key.id ? (
                                                        <CircularProgress
                                                            size={16}
                                                        />
                                                    ) : testResult?.id ===
                                                          key.id &&
                                                      testResult?.ok ? (
                                                        <CheckCircleRoundedIcon
                                                            fontSize="small"
                                                            color="success"
                                                        />
                                                    ) : (
                                                        <ScienceRoundedIcon fontSize="small" />
                                                    )}
                                                </IconButton>
                                            </span>
                                        </Tooltip>
                                        <Tooltip title="Rotate / edit">
                                            <IconButton
                                                size="small"
                                                onClick={() => openRotate(key)}
                                            >
                                                <SyncRoundedIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                        <Tooltip title="Delete">
                                            <IconButton
                                                size="small"
                                                color="error"
                                                onClick={() =>
                                                    setConfirmDelete(key)
                                                }
                                            >
                                                <DeleteOutlineRoundedIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Create / rotate dialog */}
            <Dialog open={dialogOpen} onClose={closeDialog} fullWidth maxWidth="sm">
                <Box component="form" onSubmit={submit}>
                    <DialogTitle>
                        {isEditing ? 'Rotate / edit key' : 'Add key'}
                    </DialogTitle>
                    <DialogContent dividers>
                        <Stack spacing={2.5} sx={{ mt: 0.5 }}>
                            <FormControl fullWidth disabled={isEditing}>
                                <InputLabel>Provider</InputLabel>
                                <Select
                                    label="Provider"
                                    value={form.data.provider}
                                    onChange={(e) =>
                                        form.setData('provider', e.target.value)
                                    }
                                >
                                    {providerOptions.map((p) => (
                                        <MenuItem key={p} value={p}>
                                            {p}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                            <TextField
                                label="Label"
                                value={form.data.label}
                                onChange={(e) =>
                                    form.setData('label', e.target.value)
                                }
                                error={Boolean(form.errors.label)}
                                helperText={
                                    form.errors.label ?? 'Optional, e.g. "prod"'
                                }
                                fullWidth
                            />
                            <TextField
                                label={isEditing ? 'New secret (leave blank to keep)' : 'Secret'}
                                type="password"
                                value={form.data.value}
                                onChange={(e) =>
                                    form.setData('value', e.target.value)
                                }
                                error={Boolean(form.errors.value)}
                                helperText={
                                    form.errors.value ??
                                    'Stored encrypted; never shown again after save.'
                                }
                                fullWidth
                                required={!isEditing}
                                autoComplete="off"
                            />
                            <FormControlLabel
                                control={
                                    <Switch
                                        checked={Boolean(form.data.active)}
                                        onChange={(e) =>
                                            form.setData(
                                                'active',
                                                e.target.checked
                                            )
                                        }
                                    />
                                }
                                label="Active"
                            />
                        </Stack>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={closeDialog} disabled={form.processing}>
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            variant="contained"
                            disabled={form.processing}
                        >
                            {isEditing ? 'Save' : 'Store'}
                        </Button>
                    </DialogActions>
                </Box>
            </Dialog>

            {/* Delete confirmation */}
            <Dialog
                open={Boolean(confirmDelete)}
                onClose={() => setConfirmDelete(null)}
            >
                <DialogTitle>Delete key?</DialogTitle>
                <DialogContent>
                    <Typography variant="body2">
                        This permanently removes the{' '}
                        <strong>{confirmDelete?.provider}</strong> key
                        {confirmDelete?.label
                            ? ` "${confirmDelete.label}"`
                            : ''}{' '}
                        ({confirmDelete?.masked}).
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setConfirmDelete(null)}>Cancel</Button>
                    <Button color="error" variant="contained" onClick={doDelete}>
                        Delete
                    </Button>
                </DialogActions>
            </Dialog>
        </AppLayout>
    );
}
