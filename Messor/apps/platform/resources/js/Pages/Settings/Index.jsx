import AppLayout from '@/Layouts/AppLayout';
import { Head, useForm, usePage } from '@inertiajs/react';
import SaveRoundedIcon from '@mui/icons-material/SaveRounded';
import {
    Alert,
    Autocomplete,
    Box,
    Button,
    Divider,
    Grid,
    Paper,
    Snackbar,
    Stack,
    TextField,
    Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';

export default function SettingsIndex({ settings = {}, modelSuggestions = [] }) {
    const { flash } = usePage().props;
    const [snack, setSnack] = useState(null);

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
    });

    const num = (field) => (event) =>
        form.setData(field, event.target.value === '' ? '' : Number(event.target.value));

    const submit = (event) => {
        event.preventDefault();
        form.put(route('settings.update'));
    };

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
                                <Autocomplete
                                    freeSolo
                                    options={modelSuggestions}
                                    value={form.data.enrich_model}
                                    onChange={(_e, v) =>
                                        form.setData('enrich_model', v ?? '')
                                    }
                                    onInputChange={(_e, v) =>
                                        form.setData('enrich_model', v ?? '')
                                    }
                                    renderInput={(params) => (
                                        <TextField
                                            {...params}
                                            label="Enrich model"
                                            error={Boolean(form.errors.enrich_model)}
                                            helperText={form.errors.enrich_model}
                                        />
                                    )}
                                />
                            </Grid>
                            <Grid size={{ xs: 12, md: 6 }}>
                                <Autocomplete
                                    freeSolo
                                    options={modelSuggestions}
                                    value={form.data.synthesize_model}
                                    onChange={(_e, v) =>
                                        form.setData('synthesize_model', v ?? '')
                                    }
                                    onInputChange={(_e, v) =>
                                        form.setData('synthesize_model', v ?? '')
                                    }
                                    renderInput={(params) => (
                                        <TextField
                                            {...params}
                                            label="Synthesize model"
                                            error={Boolean(
                                                form.errors.synthesize_model
                                            )}
                                            helperText={form.errors.synthesize_model}
                                        />
                                    )}
                                />
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
            </Paper>

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
