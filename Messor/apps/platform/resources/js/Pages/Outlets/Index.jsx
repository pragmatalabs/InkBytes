import AppLayout from '@/Layouts/AppLayout';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { Head, router, useForm, usePage } from '@inertiajs/react';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import EditRoundedIcon from '@mui/icons-material/EditRounded';
import {
    Alert,
    Box,
    Button,
    Chip,
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
    Snackbar,
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
import { useEffect, useMemo, useState } from 'react';

const PRIORITY_LABELS = { 1: 'High', 2: 'Medium', 3: 'Low' };
const PRIORITY_COLORS = { 1: 'error', 2: 'warning', 3: 'default' };

const emptyOutlet = {
    id: '',
    name: '',
    display_name: '',
    url: '',
    region: 'global',
    language: 'en',
    vertical: 'general',
    priority: 2,
    active: true,
};

export default function OutletsIndex({ outlets = [], options = {} }) {
    const { flash } = usePage().props;
    const { isOperator } = useAuthRole();
    const regions = options.regions ?? ['global'];
    const verticals = options.verticals ?? ['general'];

    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [confirmDelete, setConfirmDelete] = useState(null);
    const [snack, setSnack] = useState(null);

    useEffect(() => {
        if (flash?.success) {
            setSnack({ severity: 'success', message: flash.success });
        } else if (flash?.error) {
            setSnack({ severity: 'error', message: flash.error });
        }
    }, [flash]);

    const form = useForm({ ...emptyOutlet });
    const isEditing = editingId !== null;

    const openCreate = () => {
        setEditingId(null);
        form.clearErrors();
        form.setData({ ...emptyOutlet });
        setDialogOpen(true);
    };

    const openEdit = (outlet) => {
        setEditingId(outlet.id);
        form.clearErrors();
        form.setData({
            id: outlet.id,
            name: outlet.name,
            display_name: outlet.display_name,
            url: outlet.url,
            region: outlet.region,
            language: outlet.language,
            vertical: outlet.vertical,
            priority: outlet.priority,
            active: Boolean(outlet.active),
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
            form.put(route('outlets.update', editingId), { onSuccess });
        } else {
            form.post(route('outlets.store'), { onSuccess });
        }
    };

    const doDelete = () => {
        if (!confirmDelete) {
            return;
        }
        router.delete(route('outlets.destroy', confirmDelete.id), {
            onFinish: () => setConfirmDelete(null),
        });
    };

    const set = (field) => (event) => form.setData(field, event.target.value);

    const sortedOutlets = useMemo(() => outlets, [outlets]);

    return (
        <AppLayout
            title="Outlets"
            subtitle="The canonical news-outlet catalogue. Curator and Messor read from this list."
        >
            <Head title="Outlets" />

            {isOperator ? (
                <Stack
                    direction="row"
                    justifyContent="flex-end"
                    sx={{ mb: 2 }}
                >
                    <Button
                        variant="contained"
                        startIcon={<AddRoundedIcon />}
                        onClick={openCreate}
                    >
                        Add Outlet
                    </Button>
                </Stack>
            ) : null}

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Outlet</TableCell>
                            <TableCell>Slug</TableCell>
                            <TableCell>Region</TableCell>
                            <TableCell>Lang</TableCell>
                            <TableCell>Vertical</TableCell>
                            <TableCell>Priority</TableCell>
                            <TableCell>Active</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {sortedOutlets.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={8}>
                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                        sx={{ py: 2, textAlign: 'center' }}
                                    >
                                        No outlets yet. Add one to get started.
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            sortedOutlets.map((outlet) => (
                                <TableRow key={outlet.id} hover>
                                    <TableCell>
                                        <Typography
                                            variant="body2"
                                            sx={{ fontWeight: 600 }}
                                        >
                                            {outlet.display_name}
                                        </Typography>
                                        <Typography
                                            variant="caption"
                                            color="text.secondary"
                                        >
                                            {outlet.url}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Typography
                                            variant="body2"
                                            sx={{ fontFamily: 'monospace' }}
                                        >
                                            {outlet.id}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>{outlet.region}</TableCell>
                                    <TableCell>{outlet.language}</TableCell>
                                    <TableCell>{outlet.vertical}</TableCell>
                                    <TableCell>
                                        <Chip
                                            size="small"
                                            label={
                                                PRIORITY_LABELS[
                                                    outlet.priority
                                                ] ?? outlet.priority
                                            }
                                            color={
                                                PRIORITY_COLORS[
                                                    outlet.priority
                                                ] ?? 'default'
                                            }
                                            variant="outlined"
                                        />
                                    </TableCell>
                                    <TableCell>
                                        <Chip
                                            size="small"
                                            label={
                                                outlet.active
                                                    ? 'active'
                                                    : 'inactive'
                                            }
                                            color={
                                                outlet.active
                                                    ? 'success'
                                                    : 'default'
                                            }
                                            variant={
                                                outlet.active
                                                    ? 'filled'
                                                    : 'outlined'
                                            }
                                        />
                                    </TableCell>
                                    <TableCell align="right">
                                        {isOperator ? (
                                            <>
                                                <Tooltip title="Edit">
                                                    <IconButton
                                                        size="small"
                                                        onClick={() =>
                                                            openEdit(outlet)
                                                        }
                                                    >
                                                        <EditRoundedIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                                <Tooltip title="Delete">
                                                    <IconButton
                                                        size="small"
                                                        color="error"
                                                        onClick={() =>
                                                            setConfirmDelete(
                                                                outlet,
                                                            )
                                                        }
                                                    >
                                                        <DeleteOutlineRoundedIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                            </>
                                        ) : (
                                            <Typography
                                                variant="caption"
                                                color="text.secondary"
                                            >
                                                —
                                            </Typography>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Create / Edit dialog */}
            <Dialog
                open={dialogOpen}
                onClose={closeDialog}
                fullWidth
                maxWidth="sm"
            >
                <Box component="form" onSubmit={submit}>
                    <DialogTitle>
                        {isEditing ? 'Edit Outlet' : 'Add Outlet'}
                    </DialogTitle>
                    <DialogContent dividers>
                        <Stack spacing={2.5} sx={{ mt: 0.5 }}>
                            <TextField
                                label="Slug (id)"
                                value={form.data.id}
                                onChange={set('id')}
                                error={Boolean(form.errors.id)}
                                helperText={
                                    form.errors.id ??
                                    'Lowercase identifier, e.g. "bbc". Cannot be changed after creation.'
                                }
                                disabled={isEditing}
                                fullWidth
                                required={!isEditing}
                            />
                            <TextField
                                label="Display name"
                                value={form.data.display_name}
                                onChange={set('display_name')}
                                error={Boolean(form.errors.display_name)}
                                helperText={form.errors.display_name}
                                fullWidth
                                required
                            />
                            <TextField
                                label="Scraper key (name)"
                                value={form.data.name}
                                onChange={set('name')}
                                error={Boolean(form.errors.name)}
                                helperText={
                                    form.errors.name ??
                                    'Must match the Messor outlet name.'
                                }
                                fullWidth
                                required
                            />
                            <TextField
                                label="URL"
                                value={form.data.url}
                                onChange={set('url')}
                                error={Boolean(form.errors.url)}
                                helperText={form.errors.url}
                                fullWidth
                                required
                            />
                            <Stack direction="row" spacing={2}>
                                <FormControl fullWidth>
                                    <InputLabel>Region</InputLabel>
                                    <Select
                                        label="Region"
                                        value={form.data.region}
                                        onChange={set('region')}
                                    >
                                        {regions.map((r) => (
                                            <MenuItem key={r} value={r}>
                                                {r}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                                <TextField
                                    label="Language"
                                    value={form.data.language}
                                    onChange={set('language')}
                                    error={Boolean(form.errors.language)}
                                    helperText={form.errors.language ?? 'e.g. en, es'}
                                    sx={{ width: 160 }}
                                    required
                                />
                            </Stack>
                            <Stack direction="row" spacing={2}>
                                <FormControl fullWidth>
                                    <InputLabel>Vertical</InputLabel>
                                    <Select
                                        label="Vertical"
                                        value={form.data.vertical}
                                        onChange={set('vertical')}
                                    >
                                        {verticals.map((v) => (
                                            <MenuItem key={v} value={v}>
                                                {v}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                                <FormControl sx={{ width: 160 }}>
                                    <InputLabel>Priority</InputLabel>
                                    <Select
                                        label="Priority"
                                        value={form.data.priority}
                                        onChange={(e) =>
                                            form.setData(
                                                'priority',
                                                Number(e.target.value)
                                            )
                                        }
                                    >
                                        <MenuItem value={1}>1 — High</MenuItem>
                                        <MenuItem value={2}>2 — Medium</MenuItem>
                                        <MenuItem value={3}>3 — Low</MenuItem>
                                    </Select>
                                </FormControl>
                            </Stack>
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
                            {isEditing ? 'Save' : 'Create'}
                        </Button>
                    </DialogActions>
                </Box>
            </Dialog>

            {/* Delete confirmation */}
            <Dialog
                open={Boolean(confirmDelete)}
                onClose={() => setConfirmDelete(null)}
            >
                <DialogTitle>Delete outlet?</DialogTitle>
                <DialogContent>
                    <Typography variant="body2">
                        This removes{' '}
                        <strong>{confirmDelete?.display_name}</strong> (
                        {confirmDelete?.id}) from the catalogue. Curator and
                        Messor will stop harvesting it.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setConfirmDelete(null)}>Cancel</Button>
                    <Button color="error" variant="contained" onClick={doDelete}>
                        Delete
                    </Button>
                </DialogActions>
            </Dialog>

            <Snackbar
                open={Boolean(snack)}
                autoHideDuration={4000}
                onClose={() => setSnack(null)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
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
