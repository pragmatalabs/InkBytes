import AppLayout from '@/Layouts/AppLayout';
import { Head, router, useForm } from '@inertiajs/react';
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded';
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
    Stack,
    TextField,
    Typography,
} from '@mui/material';
import { useState } from 'react';

export default function SettingsIndex({
    settings = {},
    enrichModels = [],
    synthesizeModels = [],
    embeddingProviders = [],
    embeddingModels = {},
    embeddingDimensions = {},
    // B15: LLM provider/model allowlists. Drive provider + model dropdowns
    // so a typo'd provider or cross-provider model can never reach Curator.
    llmProviders = [],
    llmModels = {},
}) {
    const [resetOpen, setResetOpen] = useState(false);
    const [reembedOpen, setReembedOpen] = useState(false);

    const form = useForm({
        // B15: LLM provider (anthropic | openai). Curator live-polls.
        llm_provider: settings.llm_provider ?? 'anthropic',
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
        // ADR-0004: embedding tier.
        embeddings_provider: settings.embeddings_provider ?? 'ollama',
        embeddings_model: settings.embeddings_model ?? 'bge-m3',
        embeddings_base_url: settings.embeddings_base_url ?? 'http://localhost:11434/v1',
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

    const doReembed = () => {
        setReembedOpen(false);
        router.post(route('settings.reembed'));
    };

    // B15: LLM provider change — keep enrich/synthesize models valid for the
    // newly-selected provider (reset to provider's first model if the current
    // selection isn't in that provider's list).
    const onLlmProviderChange = (provider) => {
        const models = llmModels[provider] ?? {};
        const enrichModelsForProvider = models.enrich ?? [];
        const synthModelsForProvider = models.synthesize ?? [];
        form.setData({
            ...form.data,
            llm_provider: provider,
            enrich_model: enrichModelsForProvider.includes(form.data.enrich_model)
                ? form.data.enrich_model
                : (enrichModelsForProvider[0] ?? ''),
            synthesize_model: synthModelsForProvider.includes(form.data.synthesize_model)
                ? form.data.synthesize_model
                : (synthModelsForProvider[0] ?? ''),
        });
    };

    // Embedding provider change: keep the model valid for the newly-selected provider.
    const onProviderChange = (provider) => {
        const models = embeddingModels[provider] ?? [];
        const model = models.includes(form.data.embeddings_model)
            ? form.data.embeddings_model
            : (models[0] ?? '');
        form.setData({
            ...form.data,
            embeddings_provider: provider,
            embeddings_model: model,
        });
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

    // B15: LLM provider derived state — drive enrich/synthesize dropdowns from
    // the current provider's allowed list (falls back to the prop lists from the
    // controller if llmModels is empty, e.g. during tests).
    const currentLlmModels = llmModels[form.data.llm_provider] ?? {};
    const currentEnrichModels = currentLlmModels.enrich ?? enrichModels;
    const currentSynthModels = currentLlmModels.synthesize ?? synthesizeModels;
    const llmProviderChanged = form.data.llm_provider !== settings.llm_provider;

    // Embedding tier derived state.
    const providerModels = embeddingModels[form.data.embeddings_provider] ?? [];
    const selectedDims = embeddingDimensions[form.data.embeddings_model] ?? null;
    const savedDims = embeddingDimensions[settings.embeddings_model] ?? null;
    const isOllama = form.data.embeddings_provider === 'ollama';
    const embeddingChanged =
        form.data.embeddings_provider !== settings.embeddings_provider ||
        form.data.embeddings_model !== settings.embeddings_model;
    const dimsWouldChange =
        selectedDims !== null && savedDims !== null && selectedDims !== savedDims;

    return (
        <AppLayout
            title="Curator Settings"
            subtitle="LLM provider, models, token caps, clustering thresholds, and the embedding tier. Curator polls this row and applies changes without a redeploy."
        >
            <Head title="Curator Settings" />

            <Paper component="form" onSubmit={submit} sx={{ p: 3 }}>
                <Stack spacing={3}>
                    {/* B15: LLM Provider section — above Models & Tokens */}
                    <Box>
                        <Typography variant="h6" gutterBottom>
                            LLM Provider
                        </Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 4 }}>
                                <TextField
                                    select
                                    label="Provider"
                                    value={form.data.llm_provider}
                                    onChange={(e) => onLlmProviderChange(e.target.value)}
                                    error={Boolean(form.errors.llm_provider)}
                                    helperText={
                                        form.errors.llm_provider ??
                                        'Anthropic or OpenAI — Curator live-applies on next poll'
                                    }
                                    fullWidth
                                >
                                    {llmProviders.map((p) => (
                                        <MenuItem key={p} value={p}>
                                            {p}
                                        </MenuItem>
                                    ))}
                                </TextField>
                            </Grid>
                        </Grid>

                        {form.data.llm_provider === 'openai' && (
                            <Alert severity="info" sx={{ mt: 2 }}>
                                Switching to OpenAI requires{' '}
                                <code>OPENAI_API_KEY</code> in Curator's environment —
                                LLM keys are not managed here (ADR-0004).
                            </Alert>
                        )}
                        {llmProviderChanged && (
                            <Alert severity="info" sx={{ mt: 2 }}>
                                After saving, Curator will switch its LLM client within
                                30 seconds (next config poll).
                            </Alert>
                        )}
                    </Box>

                    <Divider />

                    <Box>
                        <Typography variant="h6" gutterBottom>
                            Models
                        </Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {modelField(
                                    'enrich_model',
                                    'Enrich model',
                                    currentEnrichModels,
                                    'Model used to enrich each article'
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {modelField(
                                    'synthesize_model',
                                    'Synthesize model',
                                    currentSynthModels,
                                    'Model used to synthesize each page'
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
                            Embeddings
                        </Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 3 }}>
                                <TextField
                                    select
                                    label="Provider"
                                    value={form.data.embeddings_provider}
                                    onChange={(e) => onProviderChange(e.target.value)}
                                    error={Boolean(form.errors.embeddings_provider)}
                                    helperText={
                                        form.errors.embeddings_provider ??
                                        'Local Ollama or hosted OpenAI'
                                    }
                                    fullWidth
                                >
                                    {embeddingProviders.map((p) => (
                                        <MenuItem key={p} value={p}>
                                            {p}
                                        </MenuItem>
                                    ))}
                                </TextField>
                            </Grid>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {modelField(
                                    'embeddings_model',
                                    'Model',
                                    providerModels,
                                    'Embedding model (provider-specific)'
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 2 }}>
                                <TextField
                                    label="Vector dims"
                                    value={selectedDims ?? '—'}
                                    helperText="Derived (column width)"
                                    InputProps={{ readOnly: true }}
                                    fullWidth
                                />
                            </Grid>
                            {isOllama && (
                                <Grid size={{ xs: 12, md: 4 }}>
                                    <TextField
                                        label="Base URL (Ollama)"
                                        value={form.data.embeddings_base_url}
                                        onChange={(e) =>
                                            form.setData('embeddings_base_url', e.target.value)
                                        }
                                        error={Boolean(form.errors.embeddings_base_url)}
                                        helperText={
                                            form.errors.embeddings_base_url ??
                                            'e.g. http://ollama:11434/v1'
                                        }
                                        fullWidth
                                    />
                                </Grid>
                            )}
                        </Grid>

                        {dimsWouldChange && (
                            <Alert severity="warning" sx={{ mt: 2 }}>
                                This model uses <strong>{selectedDims}-d</strong> vectors
                                but the live column is <strong>{savedDims}-d</strong>.
                                Curator will <strong>refuse to switch live</strong> — a
                                vector-width migration + full re-embed is required first
                                (an ops task), otherwise inserts would fail.
                            </Alert>
                        )}
                        {!dimsWouldChange && embeddingChanged && (
                            <Alert severity="info" sx={{ mt: 2 }}>
                                After saving, existing vectors are from the previous model
                                and become stale (different vector space). Click{' '}
                                <strong>Re-embed corpus</strong> below to rebuild every
                                article's embedding with the new model.
                            </Alert>
                        )}
                        {form.data.embeddings_provider === 'openai' && (
                            <Alert severity="info" sx={{ mt: 2 }}>
                                Switching to OpenAI requires <code>OPENAI_API_KEY</code> in
                                Curator's environment — embedding keys are not managed here
                                (ADR-0004).
                            </Alert>
                        )}

                        <Box sx={{ mt: 2 }}>
                            <Button
                                type="button"
                                variant="outlined"
                                startIcon={<AutorenewRoundedIcon />}
                                onClick={() => setReembedOpen(true)}
                                disabled={form.processing}
                            >
                                Re-embed corpus
                            </Button>
                            <Typography
                                variant="caption"
                                color="text.secondary"
                                sx={{ ml: 1.5 }}
                            >
                                Rebuilds all article embeddings with the saved model (runs
                                in Curator, in the background).
                            </Typography>
                        </Box>
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
                        This restores the canonical defaults (Anthropic provider, Haiku
                        models, token caps, temperature 0.2, clustering thresholds, local
                        Ollama bge-m3 embeddings) and clears the monthly budget. Curator
                        polls this row, so the change reaches the live pipeline within its
                        refresh interval. This action is recorded in the audit log.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setResetOpen(false)}>Cancel</Button>
                    <Button onClick={doReset} color="warning" variant="contained">
                        Reset to defaults
                    </Button>
                </DialogActions>
            </Dialog>

            <Dialog open={reembedOpen} onClose={() => setReembedOpen(false)}>
                <DialogTitle>Re-embed the whole corpus?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Curator will rebuild every article's embedding with the currently
                        saved model, in the background. Do this after switching the
                        embedding provider/model so clustering uses one consistent vector
                        space. It uses no LLM budget (embeddings only) but takes a few
                        minutes. This action is recorded in the audit log.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setReembedOpen(false)}>Cancel</Button>
                    <Button onClick={doReembed} variant="contained">
                        Re-embed corpus
                    </Button>
                </DialogActions>
            </Dialog>
        </AppLayout>
    );
}
