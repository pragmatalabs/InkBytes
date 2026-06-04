import AppLayout from '@/Layouts/AppLayout';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { Head, router, useForm, usePage } from '@inertiajs/react';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import EditRoundedIcon from '@mui/icons-material/EditRounded';
import UploadRoundedIcon from '@mui/icons-material/UploadRounded';
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
import { useEffect, useMemo, useRef, useState } from 'react';

const PRIORITY_LABELS = { 1: 'High', 2: 'Medium', 3: 'Low' };
const PRIORITY_COLORS = { 1: 'error', 2: 'warning', 3: 'default' };

const DAY_MS = 24 * 60 * 60 * 1000;
const WEEK_MS = 7 * DAY_MS;

// Relative "time ago" for a last-scraped ISO timestamp (or "—" when never).
function relativeTime(iso) {
    if (!iso) {
        return '—';
    }
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) {
        return '—';
    }
    const diff = Date.now() - then;
    const mins = Math.round(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.round(hours / 24);
    if (days < 7) return `${days}d ago`;
    const weeks = Math.round(days / 7);
    return `${weeks}w ago`;
}

// Health is derived from the active flag + recency of the last scrape. We do
// NOT show a success rate: Curator's public.articles only holds successful
// scrapes, so attempts/failures (a true rate) live in Messor's run history (B4).
function outletHealth(outlet) {
    if (!outlet.active) {
        return { label: 'Inactive', color: 'default' };
    }
    if (!outlet.last_scraped || (outlet.article_count ?? 0) === 0) {
        return { label: 'Never', color: 'warning' };
    }
    const age = Date.now() - new Date(outlet.last_scraped).getTime();
    if (age < DAY_MS) {
        return { label: 'Healthy', color: 'success' };
    }
    if (age < WEEK_MS) {
        return { label: 'Stale', color: 'warning' };
    }
    return { label: 'Old', color: 'error' };
}

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

    // Import (B10): file picker → preview dialog → apply.
    const fileInputRef = useRef(null);
    const [preview, setPreview] = useState(null);
    const [importing, setImporting] = useState(false);

    useEffect(() => {
        if (flash?.success) {
            setSnack({ severity: 'success', message: flash.success });
        } else if (flash?.error) {
            setSnack({ severity: 'error', message: flash.error });
        }
        // The server flashes the diff preview on the redirect after an upload.
        if (flash?.importPreview) {
            setPreview(flash.importPreview);
        }
    }, [flash]);

    const onPickFile = (event) => {
        const file = event.target.files?.[0];
        // Reset the input so picking the same file again re-fires onChange.
        event.target.value = '';
        if (!file) {
            return;
        }
        router.post(
            route('outlets.import.preview'),
            { file },
            { forceFormData: true, preserveScroll: true },
        );
    };

    const applyImport = () => {
        if (!preview) {
            return;
        }
        const outlets = preview.rows.map((r) => r.data);
        router.post(
            route('outlets.import.apply'),
            { outlets },
            {
                preserveScroll: true,
                onStart: () => setImporting(true),
                onFinish: () => {
                    setImporting(false);
                    setPreview(null);
                },
            },
        );
    };

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

            <Stack
                direction="row"
                spacing={1.5}
                justifyContent="flex-end"
                alignItems="center"
                sx={{ mb: 2 }}
            >
                {/* Export is read-only — available to every authenticated role.
                    Plain anchor so the browser handles the streamed download. */}
                <Button
                    variant="outlined"
                    startIcon={<DownloadRoundedIcon />}
                    component="a"
                    href={route('outlets.export')}
                >
                    Export JSON
                </Button>

                {isOperator ? (
                    <>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="application/json,.json"
                            style={{ display: 'none' }}
                            onChange={onPickFile}
                        />
                        <Button
                            variant="outlined"
                            startIcon={<UploadRoundedIcon />}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            Import JSON
                        </Button>
                        <Button
                            variant="contained"
                            startIcon={<AddRoundedIcon />}
                            onClick={openCreate}
                        >
                            Add Outlet
                        </Button>
                    </>
                ) : null}
            </Stack>

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
                            <TableCell align="right">Articles</TableCell>
                            <TableCell align="right">Events</TableCell>
                            <TableCell>Last scraped</TableCell>
                            <TableCell>Health</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {sortedOutlets.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={12}>
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
                                        <Typography variant="body2">
                                            {outlet.article_count ?? 0}
                                        </Typography>
                                    </TableCell>
                                    <TableCell align="right">
                                        <Typography variant="body2">
                                            {outlet.events_contributed ?? 0}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Tooltip
                                            title={
                                                outlet.last_scraped ??
                                                'Never scraped'
                                            }
                                        >
                                            <Typography
                                                variant="body2"
                                                color="text.secondary"
                                            >
                                                {relativeTime(
                                                    outlet.last_scraped,
                                                )}
                                            </Typography>
                                        </Tooltip>
                                    </TableCell>
                                    <TableCell>
                                        {(() => {
                                            const health =
                                                outletHealth(outlet);
                                            return (
                                                <Chip
                                                    size="small"
                                                    label={health.label}
                                                    color={health.color}
                                                    variant={
                                                        health.color ===
                                                        'default'
                                                            ? 'outlined'
                                                            : 'filled'
                                                    }
                                                />
                                            );
                                        })()}
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

            {/* Import diff preview → Apply (B10) */}
            <Dialog
                open={Boolean(preview)}
                onClose={() => (importing ? null : setPreview(null))}
                fullWidth
                maxWidth="md"
            >
                <DialogTitle>Import preview</DialogTitle>
                <DialogContent dividers>
                    {preview ? (
                        <Stack spacing={2}>
                            <Stack direction="row" spacing={1}>
                                <Chip
                                    color="success"
                                    label={`${preview.summary.create} to create`}
                                />
                                <Chip
                                    color="info"
                                    label={`${preview.summary.update} to update`}
                                />
                                <Chip
                                    color={
                                        preview.summary.error > 0
                                            ? 'error'
                                            : 'default'
                                    }
                                    variant={
                                        preview.summary.error > 0
                                            ? 'filled'
                                            : 'outlined'
                                    }
                                    label={`${preview.summary.error} invalid`}
                                />
                            </Stack>

                            {preview.summary.error > 0 ? (
                                <Alert severity="error">
                                    Fix the invalid rows below and re-upload —
                                    nothing can be applied while any row is
                                    invalid.
                                </Alert>
                            ) : null}

                            {preview.errors.length > 0 ? (
                                <TableContainer
                                    component={Paper}
                                    variant="outlined"
                                >
                                    <Table size="small">
                                        <TableHead>
                                            <TableRow>
                                                <TableCell>Row</TableCell>
                                                <TableCell>Slug</TableCell>
                                                <TableCell>Errors</TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {preview.errors.map((e) => (
                                                <TableRow
                                                    key={`err-${e.index}`}
                                                >
                                                    <TableCell>
                                                        {e.index + 1}
                                                    </TableCell>
                                                    <TableCell>
                                                        {e.id ?? '—'}
                                                    </TableCell>
                                                    <TableCell>
                                                        <Typography
                                                            variant="caption"
                                                            color="error"
                                                        >
                                                            {e.messages.join(
                                                                '; ',
                                                            )}
                                                        </Typography>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </TableContainer>
                            ) : null}

                            {preview.rows.length > 0 ? (
                                <TableContainer
                                    component={Paper}
                                    variant="outlined"
                                    sx={{ maxHeight: 340 }}
                                >
                                    <Table size="small" stickyHeader>
                                        <TableHead>
                                            <TableRow>
                                                <TableCell>Action</TableCell>
                                                <TableCell>Slug</TableCell>
                                                <TableCell>Name</TableCell>
                                                <TableCell>Region</TableCell>
                                                <TableCell>Active</TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {preview.rows.map((r) => (
                                                <TableRow key={r.data.id}>
                                                    <TableCell>
                                                        <Chip
                                                            size="small"
                                                            label={r.action}
                                                            color={
                                                                r.action ===
                                                                'create'
                                                                    ? 'success'
                                                                    : 'info'
                                                            }
                                                            variant="outlined"
                                                        />
                                                    </TableCell>
                                                    <TableCell>
                                                        <Typography
                                                            variant="body2"
                                                            sx={{
                                                                fontFamily:
                                                                    'monospace',
                                                            }}
                                                        >
                                                            {r.data.id}
                                                        </Typography>
                                                    </TableCell>
                                                    <TableCell>
                                                        {r.data.display_name}
                                                    </TableCell>
                                                    <TableCell>
                                                        {r.data.region}
                                                    </TableCell>
                                                    <TableCell>
                                                        {r.data.active
                                                            ? 'yes'
                                                            : 'no'}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </TableContainer>
                            ) : null}
                        </Stack>
                    ) : null}
                </DialogContent>
                <DialogActions>
                    <Button
                        onClick={() => setPreview(null)}
                        disabled={importing}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="contained"
                        onClick={applyImport}
                        disabled={
                            importing ||
                            !preview ||
                            preview.summary.error > 0 ||
                            preview.rows.length === 0
                        }
                    >
                        Apply ({preview ? preview.rows.length : 0})
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
