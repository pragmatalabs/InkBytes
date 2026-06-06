import {
    Box,
    Chip,
    CircularProgress,
    Dialog,
    DialogContent,
    DialogTitle,
    Divider,
    Grid,
    IconButton,
    Stack,
    Tooltip,
    Typography,
} from '@mui/material';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import { useEffect, useRef, useState } from 'react';
import { router } from '@inertiajs/react';

/** ── helpers ──────────────────────────────────────────────────────────────── */

function fmt(n) {
    if (n == null) return '—';
    return Number(n).toLocaleString();
}

function StatusDot({ ok, label }) {
    const color = ok ? '#10b981' : '#ef4444';
    return (
        <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75 }}>
            <Box component="span" sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: color, display: 'inline-block', flexShrink: 0 }} />
            <Typography variant="caption" color="text.secondary">{label}</Typography>
        </Box>
    );
}

function StatCard({ label, value, sub, highlight }) {
    return (
        <Box sx={{
            border: 1, borderColor: 'divider', borderRadius: 2, p: 2,
            bgcolor: highlight ? 'warning.50' : 'background.paper',
            minWidth: 0,
        }}>
            <Typography variant="h5" fontWeight={700} sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {fmt(value)}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">{label}</Typography>
            {sub != null && (
                <Typography variant="caption" color="text.disabled" display="block" sx={{ mt: 0.25 }}>{sub}</Typography>
            )}
        </Box>
    );
}

function Section({ title, children }) {
    return (
        <Box>
            <Typography variant="overline" color="text.secondary" fontSize={10} letterSpacing={1.5}>
                {title}
            </Typography>
            <Box sx={{ mt: 1 }}>{children}</Box>
        </Box>
    );
}

/** ── main component ────────────────────────────────────────────────────────── */

export default function CuratorStatusModal({ open, onClose }) {
    const [data, setData]       = useState(null);
    const [loading, setLoading] = useState(false);
    const [lastAt, setLastAt]   = useState(null);
    const intervalRef           = useRef(null);

    async function fetchStatus() {
        setLoading(true);
        try {
            const res = await fetch(route('curator-pipeline'), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            const json = await res.json();
            setData(json);
            setLastAt(new Date());
        } catch {
            setData({ reachable: false, error: 'Network error' });
        } finally {
            setLoading(false);
        }
    }

    // Start polling when open; stop when closed.
    useEffect(() => {
        if (!open) {
            clearInterval(intervalRef.current);
            return;
        }
        fetchStatus();
        intervalRef.current = setInterval(fetchStatus, 5000);
        return () => clearInterval(intervalRef.current);
    }, [open]);

    const reachable  = data?.reachable;
    const llm        = data?.llm ?? {};
    const embeddings = data?.embeddings ?? {};

    const pendingPct = data?.articles_total > 0
        ? Math.round((data.articles_pending / data.articles_total) * 100)
        : 0;

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="sm"
            fullWidth
            PaperProps={{ sx: { borderRadius: 3 } }}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}>
                <Stack direction="row" alignItems="center" spacing={1.5}>
                    <Typography variant="h6" fontWeight={700}>Curator Status</Typography>
                    {loading && <CircularProgress size={14} />}
                </Stack>
                <Stack direction="row" alignItems="center" spacing={0.5}>
                    <Tooltip title="Refresh now">
                        <IconButton size="small" onClick={fetchStatus} disabled={loading}>
                            <RefreshRoundedIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                    <IconButton size="small" onClick={onClose}>
                        <CloseRoundedIcon fontSize="small" />
                    </IconButton>
                </Stack>
            </DialogTitle>

            <DialogContent sx={{ pt: 1 }}>
                {!data && loading && (
                    <Box sx={{ py: 6, textAlign: 'center' }}>
                        <CircularProgress size={28} />
                    </Box>
                )}

                {data && !reachable && (
                    <Box sx={{ py: 4, textAlign: 'center' }}>
                        <StatusDot ok={false} label={data.error ?? 'Curator is offline'} />
                        <Typography variant="caption" display="block" color="text.disabled" mt={1}>
                            Make sure Curator is running on port 8060
                        </Typography>
                    </Box>
                )}

                {data && reachable && (
                    <Stack spacing={2.5}>

                        {/* ── Pipeline counters ─────────────────── */}
                        <Section title="Pipeline">
                            <Grid container spacing={1.5}>
                                <Grid item xs={6} sm={3}>
                                    <StatCard label="Articles" value={data.articles_total} />
                                </Grid>
                                <Grid item xs={6} sm={3}>
                                    <StatCard
                                        label="Enriched"
                                        value={data.articles_enriched}
                                        sub={`${pendingPct > 0 ? pendingPct + '% pending' : 'all done'}`}
                                        highlight={pendingPct > 10}
                                    />
                                </Grid>
                                <Grid item xs={6} sm={3}>
                                    <StatCard label="Events" value={data.events_published} sub={`${fmt(data.events_total)} total`} />
                                </Grid>
                                <Grid item xs={6} sm={3}>
                                    <StatCard label="Pages" value={data.pages_published} />
                                </Grid>
                            </Grid>
                        </Section>

                        <Divider />

                        {/* ── Live activity ─────────────────────── */}
                        <Section title="Active">
                            <Stack spacing={1}>
                                <Stack direction="row" justifyContent="space-between" alignItems="center">
                                    <Typography variant="body2" color="text.secondary">
                                        Syntheses in-flight
                                    </Typography>
                                    <Stack direction="row" alignItems="center" spacing={1}>
                                        <Typography variant="body2" fontWeight={600} fontFamily="monospace">
                                            {fmt(data.synths_in_flight)}
                                        </Typography>
                                        <StatusDot
                                            ok={!data.synths_in_flight}
                                            label={data.synths_in_flight > 0 ? 'Running' : 'Idle'}
                                        />
                                    </Stack>
                                </Stack>

                                <Stack direction="row" justifyContent="space-between" alignItems="center">
                                    <Typography variant="body2" color="text.secondary">
                                        Articles pending enrichment
                                    </Typography>
                                    <Chip
                                        label={fmt(data.articles_pending)}
                                        size="small"
                                        color={data.articles_pending > 100 ? 'warning' : 'default'}
                                        sx={{ fontFamily: 'monospace', fontWeight: 600 }}
                                    />
                                </Stack>

                                <Stack direction="row" justifyContent="space-between" alignItems="center">
                                    <Typography variant="body2" color="text.secondary">
                                        Re-embedding corpus
                                    </Typography>
                                    <StatusDot
                                        ok={!embeddings.reembedding}
                                        label={embeddings.reembedding ? 'In progress' : 'Idle'}
                                    />
                                </Stack>
                            </Stack>
                        </Section>

                        <Divider />

                        {/* ── LLM tier ──────────────────────────── */}
                        <Section title="LLM">
                            <Stack spacing={0.75}>
                                {[
                                    ['Provider',  llm.provider  ?? '—'],
                                    ['Enrich',    llm.enrich_model ?? '—'],
                                    ['Synthesize',llm.synthesize_model ?? '—'],
                                    ...(llm.base_url ? [['Base URL', llm.base_url]] : []),
                                ].map(([k, v]) => (
                                    <Stack key={k} direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
                                        <Typography variant="body2" color="text.secondary" flexShrink={0}>{k}</Typography>
                                        <Typography variant="body2" fontFamily="monospace" noWrap sx={{ textAlign: 'right', maxWidth: 240 }}>
                                            {v}
                                        </Typography>
                                    </Stack>
                                ))}
                            </Stack>
                        </Section>

                        <Divider />

                        {/* ── Embeddings tier ───────────────────── */}
                        <Section title="Embeddings">
                            <Stack spacing={0.75}>
                                {[
                                    ['Provider', embeddings.provider ?? '—'],
                                    ['Model',    embeddings.model    ?? '—'],
                                    ['Dims',     embeddings.dimensions ?? '—'],
                                ].map(([k, v]) => (
                                    <Stack key={k} direction="row" justifyContent="space-between" alignItems="center">
                                        <Typography variant="body2" color="text.secondary">{k}</Typography>
                                        <Typography variant="body2" fontFamily="monospace">{v}</Typography>
                                    </Stack>
                                ))}

                                <Stack direction="row" justifyContent="space-between" alignItems="center">
                                    <Typography variant="body2" color="text.secondary">Status</Typography>
                                    {embeddings.blocked
                                        ? <Chip label={`Blocked: ${embeddings.blocked}`} size="small" color="error" />
                                        : embeddings.stale
                                            ? <Chip label="Stale — re-embed needed" size="small" color="warning" />
                                            : <StatusDot ok label="Healthy" />
                                    }
                                </Stack>
                            </Stack>
                        </Section>

                        {/* ── Footer ────────────────────────────── */}
                        <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography variant="caption" color="text.disabled">
                                {lastAt
                                    ? `Last refreshed: ${lastAt.toLocaleTimeString()} · ${data.latency_ms ?? '—'}ms`
                                    : '—'}
                            </Typography>
                            <Typography variant="caption" color="text.disabled">
                                Auto-refreshes every 5 s
                            </Typography>
                        </Stack>

                    </Stack>
                )}
            </DialogContent>
        </Dialog>
    );
}
