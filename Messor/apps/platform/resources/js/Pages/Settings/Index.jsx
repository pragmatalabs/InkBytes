import AppLayout from '@/Layouts/AppLayout';
import { Head, router, useForm } from '@inertiajs/react';
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded';
import RestartAltRoundedIcon from '@mui/icons-material/RestartAltRounded';
import SaveRoundedIcon from '@mui/icons-material/SaveRounded';
import PauseCircleRoundedIcon from '@mui/icons-material/PauseCircleRounded';
import PlayCircleRoundedIcon from '@mui/icons-material/PlayCircleRounded';
import {
    Alert,
    Box,
    Button,
    Chip,
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
    llmProviders = [],
    llmModelSuggestions = {},      // { anthropic: { enrich:[…], synthesize:[…] }, openai: {…}, … }
    embeddingProviders = [],
    embeddingModelSuggestions = {}, // { ollama: […], openai: […] }
    embeddingDimensions = {},
}) {
    const [resetOpen, setResetOpen]   = useState(false);
    const [reembedOpen, setReembedOpen] = useState(false);
    const [stopOpen, setStopOpen]     = useState(false);

    // ADR-0023 "Stop Curator" kill-switch — separate from the settings form.
    const processingEnabled = settings.processing_enabled ?? true;
    const doToggleProcessing = (enabled) => {
        setStopOpen(false);
        router.post(route('settings.processing'), { enabled });
    };

    const form = useForm({
        // LLM
        llm_provider:      settings.llm_provider      ?? 'anthropic',
        enrich_model:      settings.enrich_model      ?? 'claude-haiku-4-5',
        synthesize_model:  settings.synthesize_model  ?? 'claude-haiku-4-5',
        llm_base_url:      settings.llm_base_url      ?? '',
        max_tokens_enrich: settings.max_tokens_enrich ?? 1500,
        max_tokens_synth:  settings.max_tokens_synth  ?? 2500,
        temperature:       settings.temperature       ?? 0.2,
        // Clustering
        similarity_threshold:   settings.similarity_threshold   ?? 0.62,
        entity_overlap_min:     settings.entity_overlap_min     ?? 1,
        min_sources_to_publish: settings.min_sources_to_publish ?? 2,
        recent_window_hours:    settings.recent_window_hours    ?? 48,
        // Embeddings
        embeddings_provider: settings.embeddings_provider ?? 'ollama',
        embeddings_model:    settings.embeddings_model    ?? 'bge-m3',
        embeddings_base_url: settings.embeddings_base_url ?? 'http://localhost:11434/v1',
        // Budget
        monthly_budget_usd:
            settings.monthly_budget_usd == null ? '' : settings.monthly_budget_usd,
        // API keys — empty = keep existing DB value unchanged; non-empty = save new value.
        anthropic_api_key:  '',
        openai_api_key:     '',
        deepseek_api_key:   '',
        embeddings_api_key: '',
    });

    const num = (field) => (e) =>
        form.setData(field, e.target.value === '' ? '' : Number(e.target.value));

    const submit = (e) => {
        e.preventDefault();
        form.transform((data) => ({
            ...data,
            monthly_budget_usd: data.monthly_budget_usd === '' ? null : data.monthly_budget_usd,
            llm_base_url:       data.llm_base_url === '' ? null : data.llm_base_url,
        }));
        form.put(route('settings.update'));
    };

    const doReset   = () => { setResetOpen(false);   router.post(route('settings.reset')); };
    const doReembed = () => { setReembedOpen(false);  router.post(route('settings.reembed')); };

    const onProviderChange = (provider) => {
        form.setData({ ...form.data, embeddings_provider: provider,
            embeddings_model: (embeddingModelSuggestions[provider] ?? [])[0] ?? '',
        });
    };

    // Helper: free-text field with model suggestions listed as helper text.
    const modelTextField = (field, label, suggestions, helper) => {
        const list = (suggestions ?? []).join(', ');
        return (
            <TextField
                label={label}
                value={form.data[field]}
                onChange={(e) => form.setData(field, e.target.value)}
                error={Boolean(form.errors[field])}
                helperText={form.errors[field] ?? (list ? `${helper} — e.g. ${list}` : helper)}
                fullWidth
            />
        );
    };

    const numberField = (field, label, helper, step = 1) => (
        <TextField
            label={label} type="number"
            value={form.data[field]}
            onChange={num(field)}
            error={Boolean(form.errors[field])}
            helperText={form.errors[field] ?? helper}
            inputProps={{ step }}
            fullWidth
        />
    );

    // Key field: shows status when already set in DB; empty = keep unchanged.
    const keyField = (field, label, isSet) => (
        <TextField
            label={label}
            type="password"
            value={form.data[field]}
            onChange={(e) => form.setData(field, e.target.value)}
            error={Boolean(form.errors[field])}
            placeholder={isSet ? 'Set in DB — leave blank to keep, or enter new key' : 'Enter API key'}
            helperText={
                form.errors[field] ??
                (isSet
                    ? '✓ Key stored — Curator uses it automatically'
                    : 'Not set — Curator falls back to the env var if configured')
            }
            fullWidth
            autoComplete="new-password"
        />
    );

    const llmSuggestionsForProvider = llmModelSuggestions[form.data.llm_provider] ?? {};
    const llmProviderChanged = form.data.llm_provider !== settings.llm_provider;
    const isOllama     = form.data.embeddings_provider === 'ollama';
    const selectedDims = embeddingDimensions[form.data.embeddings_model] ?? null;
    const savedDims    = embeddingDimensions[settings.embeddings_model]  ?? null;
    const embeddingChanged =
        form.data.embeddings_provider !== settings.embeddings_provider ||
        form.data.embeddings_model    !== settings.embeddings_model;
    const dimsWouldChange =
        selectedDims !== null && savedDims !== null && selectedDims !== savedDims;

    return (
        <AppLayout
            title="Curator Settings"
            subtitle="LLM provider, models, token caps, clustering thresholds, and the embedding tier. Curator polls this row and applies changes without a redeploy."
        >
            <Head title="Curator Settings" />

            {/* ── Processing kill-switch (ADR-0023) ───────────────────────── */}
            <Paper sx={{ p: 3, mb: 3 }}>
                <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={2}>
                    <Box>
                        <Stack direction="row" alignItems="center" spacing={1.5}>
                            <Typography variant="h6">Processing</Typography>
                            <Chip
                                size="small"
                                label={processingEnabled ? 'Running' : 'Paused'}
                                color={processingEnabled ? 'success' : 'warning'}
                                variant={processingEnabled ? 'filled' : 'outlined'}
                            />
                        </Stack>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 560 }}>
                            {processingEnabled
                                ? 'Curator is consuming and synthesizing articles. Pausing stops the enrich → cluster → synthesize pipeline; incoming articles queue in RabbitMQ (no loss) and the public reader stays up. Takes effect within ~30s.'
                                : 'Curator processing is paused. New articles are queuing in RabbitMQ and will be processed when you resume. The public reader is unaffected.'}
                        </Typography>
                    </Box>
                    {processingEnabled ? (
                        <Button
                            variant="contained"
                            color="warning"
                            startIcon={<PauseCircleRoundedIcon />}
                            onClick={() => setStopOpen(true)}
                        >
                            Stop Curator
                        </Button>
                    ) : (
                        <Button
                            variant="contained"
                            color="success"
                            startIcon={<PlayCircleRoundedIcon />}
                            onClick={() => doToggleProcessing(true)}
                        >
                            Resume Curator
                        </Button>
                    )}
                </Stack>
            </Paper>

            <Paper component="form" onSubmit={submit} sx={{ p: 3 }}>
                <Stack spacing={3}>

                    {/* ── LLM Provider ───────────────────────────────────── */}
                    <Box>
                        <Typography variant="h6" gutterBottom>LLM Provider</Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 4 }}>
                                <TextField
                                    select label="Provider"
                                    value={form.data.llm_provider}
                                    onChange={(e) => form.setData('llm_provider', e.target.value)}
                                    error={Boolean(form.errors.llm_provider)}
                                    helperText={form.errors.llm_provider ?? 'Anthropic or OpenAI-compatible — Curator live-applies on next poll'}
                                    fullWidth
                                >
                                    {llmProviders.map((p) => (
                                        <MenuItem key={p} value={p}>{p}</MenuItem>
                                    ))}
                                </TextField>
                            </Grid>
                            <Grid size={{ xs: 12, md: 8 }}>
                                <TextField
                                    label="Base URL (OpenAI-compatible providers)"
                                    value={form.data.llm_base_url}
                                    onChange={(e) => form.setData('llm_base_url', e.target.value)}
                                    error={Boolean(form.errors.llm_base_url)}
                                    helperText={
                                        form.errors.llm_base_url ??
                                        'Leave blank for default (api.openai.com). Override for DeepSeek, Groq, Together, local Ollama text, etc.'
                                    }
                                    placeholder="e.g. https://api.deepseek.com/v1 or https://api.groq.com/openai/v1"
                                    fullWidth
                                />
                            </Grid>
                        </Grid>
                        {llmProviderChanged && (
                            <Alert severity="info" sx={{ mt: 2 }}>
                                After saving, Curator switches its LLM client within 30 seconds (next config poll).
                            </Alert>
                        )}
                    </Box>

                    <Divider />

                    {/* ── Models ─────────────────────────────────────────── */}
                    <Box>
                        <Typography variant="h6" gutterBottom>Models</Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {modelTextField(
                                    'enrich_model', 'Enrich model',
                                    llmSuggestionsForProvider.enrich,
                                    'Model used to enrich each article'
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {modelTextField(
                                    'synthesize_model', 'Synthesize model',
                                    llmSuggestionsForProvider.synthesize,
                                    'Model used to synthesize each page'
                                )}
                            </Grid>
                        </Grid>
                    </Box>

                    <Divider />

                    {/* ── Generation ─────────────────────────────────────── */}
                    <Box>
                        <Typography variant="h6" gutterBottom>Generation</Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 4 }}>
                                {numberField('max_tokens_enrich', 'Max tokens (enrich)',    'Per-article enrichment cap')}
                            </Grid>
                            <Grid size={{ xs: 12, md: 4 }}>
                                {numberField('max_tokens_synth',  'Max tokens (synthesize)', 'Per-page synthesis cap')}
                            </Grid>
                            <Grid size={{ xs: 12, md: 4 }}>
                                {numberField('temperature', 'Temperature', '0 = deterministic, low for news', 0.05)}
                            </Grid>
                        </Grid>
                    </Box>

                    <Divider />

                    {/* ── Clustering ─────────────────────────────────────── */}
                    <Box>
                        <Typography variant="h6" gutterBottom>Clustering</Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {numberField('similarity_threshold',   'Similarity threshold',   'Cosine; lower = more merging', 0.01)}
                            </Grid>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {numberField('entity_overlap_min',     'Entity overlap min',     'Shared entities to join')}
                            </Grid>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {numberField('min_sources_to_publish', 'Min sources to publish', "Don't publish single-source")}
                            </Grid>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {numberField('recent_window_hours',    'Recent window (hours)',  'Cluster lookback window')}
                            </Grid>
                        </Grid>
                    </Box>

                    <Divider />

                    {/* ── Embeddings ─────────────────────────────────────── */}
                    <Box>
                        <Typography variant="h6" gutterBottom>Embeddings</Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 3 }}>
                                <TextField
                                    select label="Provider"
                                    value={form.data.embeddings_provider}
                                    onChange={(e) => onProviderChange(e.target.value)}
                                    error={Boolean(form.errors.embeddings_provider)}
                                    helperText={form.errors.embeddings_provider ?? 'Local Ollama or hosted OpenAI'}
                                    fullWidth
                                >
                                    {embeddingProviders.map((p) => (
                                        <MenuItem key={p} value={p}>{p}</MenuItem>
                                    ))}
                                </TextField>
                            </Grid>
                            <Grid size={{ xs: 12, md: 3 }}>
                                {modelTextField(
                                    'embeddings_model', 'Model',
                                    embeddingModelSuggestions[form.data.embeddings_provider],
                                    'Embedding model'
                                )}
                            </Grid>
                            <Grid size={{ xs: 12, md: 2 }}>
                                <TextField
                                    label="Vector dims" value={selectedDims ?? '—'}
                                    helperText="Derived (column width)"
                                    InputProps={{ readOnly: true }} fullWidth
                                />
                            </Grid>
                            {isOllama && (
                                <Grid size={{ xs: 12, md: 4 }}>
                                    <TextField
                                        label="Base URL (Ollama)"
                                        value={form.data.embeddings_base_url}
                                        onChange={(e) => form.setData('embeddings_base_url', e.target.value)}
                                        error={Boolean(form.errors.embeddings_base_url)}
                                        helperText={form.errors.embeddings_base_url ?? 'e.g. http://ollama:11434/v1'}
                                        fullWidth
                                    />
                                </Grid>
                            )}
                        </Grid>

                        {dimsWouldChange && (
                            <Alert severity="warning" sx={{ mt: 2 }}>
                                This model uses <strong>{selectedDims}-d</strong> vectors but the live column is{' '}
                                <strong>{savedDims}-d</strong>. Curator will{' '}
                                <strong>refuse to switch live</strong> — a vector-width migration + full re-embed is
                                required first.
                            </Alert>
                        )}
                        {!dimsWouldChange && embeddingChanged && (
                            <Alert severity="info" sx={{ mt: 2 }}>
                                After saving, click <strong>Re-embed corpus</strong> below to rebuild vectors with the
                                new model.
                            </Alert>
                        )}

                        <Box sx={{ mt: 2 }}>
                            <Button
                                type="button" variant="outlined"
                                startIcon={<AutorenewRoundedIcon />}
                                onClick={() => setReembedOpen(true)}
                                disabled={form.processing}
                            >
                                Re-embed corpus
                            </Button>
                            <Typography variant="caption" color="text.secondary" sx={{ ml: 1.5 }}>
                                Rebuilds all article embeddings with the saved model (runs in Curator, in the background).
                            </Typography>
                        </Box>
                    </Box>

                    <Divider />

                    {/* ── API Keys ───────────────────────────────────────── */}
                    <Box>
                        <Typography variant="h6" gutterBottom>API Keys</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Keys stored here are polled by Curator and override the corresponding env vars. Leave a field
                            blank to keep the current value. Keys are never echoed back to this page.
                        </Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {keyField('anthropic_api_key', 'Anthropic API Key', settings.anthropic_api_key_set)}
                            </Grid>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {keyField('openai_api_key', 'OpenAI API Key', settings.openai_api_key_set)}
                            </Grid>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {keyField('deepseek_api_key', 'DeepSeek API Key', settings.deepseek_api_key_set)}
                            </Grid>
                            <Grid size={{ xs: 12, md: 6 }}>
                                {keyField('embeddings_api_key', 'Embeddings API Key', settings.embeddings_api_key_set)}
                            </Grid>
                        </Grid>
                    </Box>

                    <Divider />

                    {/* ── Cost ───────────────────────────────────────────── */}
                    <Box>
                        <Typography variant="h6" gutterBottom>Cost</Typography>
                        <Grid container spacing={2.5}>
                            <Grid size={{ xs: 12, md: 4 }}>
                                {numberField(
                                    'monthly_budget_usd', 'Monthly budget (USD)',
                                    'Month-to-date spend is checked against this on the Cost & Usage page. Leave blank for no budget.',
                                    0.01
                                )}
                            </Grid>
                        </Grid>
                    </Box>

                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="caption" color="text.secondary">
                            {settings.updated_at
                                ? `Last saved ${new Date(settings.updated_at).toLocaleString()}`
                                : 'Not yet saved'}
                        </Typography>
                        <Stack direction="row" spacing={1.5}>
                            <Button
                                type="button" variant="outlined" color="warning"
                                startIcon={<RestartAltRoundedIcon />}
                                onClick={() => setResetOpen(true)}
                                disabled={form.processing}
                            >
                                Reset to defaults
                            </Button>
                            <Button
                                type="submit" variant="contained"
                                startIcon={<SaveRoundedIcon />}
                                disabled={form.processing}
                            >
                                Save settings
                            </Button>
                        </Stack>
                    </Stack>
                </Stack>
            </Paper>

            {/* Reset dialog */}
            <Dialog open={resetOpen} onClose={() => setResetOpen(false)}>
                <DialogTitle>Reset Curator settings to defaults?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        This restores the canonical defaults (Anthropic provider, Haiku models, token caps,
                        temperature 0.2, clustering thresholds, local Ollama bge-m3 embeddings) and clears the
                        monthly budget. API keys are NOT reset. Curator polls this row, so changes reach the live
                        pipeline within the refresh interval. This action is recorded in the audit log.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setResetOpen(false)}>Cancel</Button>
                    <Button onClick={doReset} color="warning" variant="contained">Reset to defaults</Button>
                </DialogActions>
            </Dialog>

            {/* Re-embed dialog */}
            <Dialog open={reembedOpen} onClose={() => setReembedOpen(false)}>
                <DialogTitle>Re-embed the whole corpus?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Curator will rebuild every article's embedding with the currently saved model, in the
                        background. Do this after switching the embedding provider/model so clustering uses one
                        consistent vector space. Uses no LLM budget (embeddings only) but takes a few minutes.
                        This action is recorded in the audit log.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setReembedOpen(false)}>Cancel</Button>
                    <Button onClick={doReembed} color="primary" variant="contained">Re-embed corpus</Button>
                </DialogActions>
            </Dialog>

            {/* Stop Curator dialog (ADR-0023) */}
            <Dialog open={stopOpen} onClose={() => setStopOpen(false)}>
                <DialogTitle>Pause Curator processing?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Curator will stop enriching, clustering, and synthesizing articles within ~30s. Incoming
                        articles keep queuing in RabbitMQ and are <strong>not lost</strong> — they process when you
                        resume. The public reader (inkbytes.org) stays up and keeps serving existing pages. This
                        action is recorded in the audit log.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setStopOpen(false)}>Cancel</Button>
                    <Button onClick={() => doToggleProcessing(false)} color="warning" variant="contained">
                        Stop Curator
                    </Button>
                </DialogActions>
            </Dialog>
        </AppLayout>
    );
}
