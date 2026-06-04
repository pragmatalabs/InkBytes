import AppLayout from '@/Layouts/AppLayout';
import { Head, router, useForm, usePage } from '@inertiajs/react';
import RestartAltRoundedIcon from '@mui/icons-material/RestartAltRounded';
import SaveRoundedIcon from '@mui/icons-material/SaveRounded';
import {
    Alert,
    Box,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    Divider,
    Grid,
    MenuItem,
    Paper,
    Snackbar,
    Stack,
    TextField,
    Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';

export default function SettingsIndex({
    settings = {},
    enrichModels = [],
    synthesizeModels = [],
}) {
    const { flash } = usePage().props;
    const [snack, setSnack] = useState(null);
    const [resetOpen, setResetOpen] = useState(false);

    useEffect(() => {
        if (flash?.success) {
            setSnack({ severity: 'success', message: flash.success });
        } else if (flash?.error) {
            setSnack({ severity: 'error', message: flash.error });
        }
    }, [flash]);

    const form = useForm({
        enrich_model: settings.enrich_model ?? 'claude-haiku-4-5',
        synthesize_model: settings.synthesize_model ?? 'claude-haiku-4-5',
        max_tokens_enrich: settings.max_tokens_enrich ?? 1500,
        max_tokens_synth: settings.max_tokens_synth ?? 2500,
        temperature: settings.temperature ?? 0.2,
        similarity_threshold: settings.similarity_threshold ?? 0.62,
        entity_overlap_min: settings.entity_overlap_min ?? 1,
        min_sources_to_publish: settings.min_sources_to_publish ?? 2,
        recent_window_hours: settings.recent_window_hours ?? 48,
        // B5: monthly LLM-spend budget (USD). Empty string = unset (sent as null).
        monthly_budget_usd:
            settings.monthly_budget_usd === null ||
            settings.monthly_budget_usd === undefined
                ? ''
                : settings.monthly_budget_usd,
    });

    const num = (field) => (event) =>
        form.setData(field, event.target.value === '' ? '' : Number(event.target.value));

    const submit = (event) => {
        event.preventDefault();
        // Send an empty budget as null (unset) rather than '' so the
        // `nullable|numeric` rule passes and the widget hides.
        form.transform((data) => ({
            ...data,
            monthly_budget_usd:
                data.monthly_budget_usd === '' ? null : data.monthly_budget_usd,
        })).put(route('settings.update'));
    };

    const doReset = () => {
        setResetOpen(false);
        router.post(route('settings.reset'));
    };

    const modelField = (field, label, options, helper) => (
        <TextField
            select
            label={label}
            value={form.data[field]}
            onChange={(event) => form.setData(field, event.target.value)}
            error={Boolean(form.errors[field])}
            helperText={form.errors[field] ?? helper}
            fullWidth
        >
            {options.map((id) => (
                <MenuItem key={id} value={id}>
                    {id}
                </MenuItem>
            ))}
        </TextField>
    );

    const numberField = (field, label, helper, step = 1) => (
        <TextField
            label={label}
            type="number"
            value={form.data[field]}
            onChange={num(field)}
            error={Boolean(form.errors[field])}
            helperText={form.errors[field] ?? helper}
            inputProps={{ step }}
            fullWidth
        />
    );

    return (
        <AppLayout
            title="Curator Settings"
            subtitle="LLM models, token caps, and clustering thresholds. Curator polls this row and applies changes without a redeploy."
        >
            <Head title="Curator Settings" />

            <Paper component="form" onSubmit={submit} sx={{ p: 3 }}>
                <Stack spacing={3}>
                    <Box>
                        <Typography variant="h6" gutterBottom>
                            Models
                        </Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {modelField(
                                    'enrich_model',
                                    'Enrich model',
                                    enrichModels,
                                    'Anthropic model used to enrich each article'
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {modelField(
                                    'synthesize_model',
                                    'Synthesize model',
                                    synthesizeModels,
                                    'Anthropic model used to synthesize each page'
                                )}
                            </Grid>
                        </Grid>
                    </Box>

                    <Divider />

                    <Box>
                        <Typography variant="h6" gutterBottom>
                            Generation
                        </Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 4 }}>
                                {numberField(
                                    'max_tokens_enrich',
                                    'Max tokens (enrich)',
                                    'Per-article enrichment cap'
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 4 }}>
                                {numberField(
                                    'max_tokens_synth',
                                    'Max tokens (synthesize)',
                                    'Per-page synthesis cap'
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 4 }}>
                                {numberField(
                                    'temperature',
                                    'Temperature',
                                    '0 = deterministic, low for news',
                                    0.05
                                )}
                            </Grid>
                        </Grid>
                    </Box>

                    <Divider />

                    <Box>
                        <Typography variant="h6" gutterBottom>
                            Clustering
                        </Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {numberField(
                                    'similarity_threshold',
                                    'Similarity threshold',
                                    'Cosine; lower = more merging',
                                    0.01
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {numberField(
                                    'entity_overlap_min',
                                    'Entity overlap min',
                                    'Shared entities to join'
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {numberField(
                                    'min_sources_to_publish',
                                    'Min sources to publish',
                                    "Don't publish single-source"
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {numberField(
                                    'recent_window_hours',
                                    'Recent window (hours)',
                                    'Cluster lookback window'
                                )}
                            </Grid>
                        </Grid>
                    </Box>

                    <Divider />

                    <Box>
                        <Typography variant="h6" gutterBottom>
                            Cost
                        </Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 4 }}>
                                {numberField(
                                    'monthly_budget_usd',
                                    'Monthly budget (USD)',
                                    'Month-to-date spend is checked against this on the Cost & Usage page. Leave blank for no budget.',
                                    0.01
                                )}
                            </Grid>
                        </Grid>
                    </Box>

                    <Stack
                        direction="row"
                        justifyContent="space-between"
                        alignItems="center"
                    >
                        <Typography variant="caption" color="text.secondary">
                            {settings.updated_at
                                ? `Last saved ${new Date(settings.updated_at).toLocaleString()}`
                                : 'Not yet saved'}
                        </Typography>
                        <Stack direction="row" spacing={1.5}>
                            <Button
                                type="button"
                                variant="outlined"
                                color="warning"
                                startIcon={<RestartAltRoundedIcon />}
                                onClick={() => setResetOpen(true)}
                                disabled={form.processing}
                            >
                                Reset to defaults
                            </Button>
                            <Button
                                type="submit"
                                variant="contained"
                                startIcon={<SaveRoundedIcon />}
                                disabled={form.processing}
                            >
                                Save settings
                            </Button>
                        </Stack>
                    </Stack>
                </Stack>
            </Paper>

            <Dialog open={resetOpen} onClose={() => setResetOpen(false)}>
                <DialogTitle>Reset Curator settings to defaults?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        This restores the canonical defaults (Haiku models, token
                        caps, temperature 0.2, clustering thresholds) and clears the
                        monthly budget. Curator polls this row, so the change reaches
                        the live pipeline within its refresh interval. This action is
                        recorded in the audit log.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setResetOpen(false)}>Cancel</Button>
                    <Button onClick={doReset} color="warning" variant="contained">
                        Reset to defaults
                    </Button>
                </DialogActions>
            </Dialog>

            <Snackbar
                open={Boolean(snack)}
                autoHideDuration={5000}
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
