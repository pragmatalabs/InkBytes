import AppLayout from '@/Layouts/AppLayout';
import { Head, router, useForm } from '@inertiajs/react';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
    Alert,
    Box,
    Button,
    Chip,
    Grid,
    Paper,
    Stack,
    TextField,
    ToggleButton,
    ToggleButtonGroup,
    Typography,
} from '@mui/material';

/**
 * On-Demand Breaking Desk (ADR-0029).
 *
 * Enter a title (Google News search) or paste a URL → Messor scrapes the
 * coverage on demand at priority 9 → results stream in below as Curator
 * processes them → mark breaking / force publish per event.
 */
export default function BreakingDeskIndex() {
    const [mode, setMode] = useState('query'); // 'query' | 'url'
    const form = useForm({ query: '', url: '', lang: 'en', limit: 10 });
    const [events, setEvents] = useState([]);
    const [polling, setPolling] = useState(false);
    const pollRef = useRef(null);

    const fetchResults = useCallback(async () => {
        try {
            const res = await fetch(route('breaking.results'), {
                headers: { Accept: 'application/json' },
            });
            if (res.ok) {
                const data = await res.json();
                setEvents(data.events ?? []);
            }
        } catch {
            /* transient — keep last results */
        }
    }, []);

    // Poll the results endpoint every 5s while the desk is open.
    useEffect(() => {
        fetchResults();
        setPolling(true);
        pollRef.current = setInterval(fetchResults, 5000);
        return () => clearInterval(pollRef.current);
    }, [fetchResults]);

    function submit(e) {
        e.preventDefault();
        // Only send the active field; clear the other so validation is clean.
        const payload = mode === 'url'
            ? { query: '', url: form.data.url }
            : { query: form.data.query, url: '' };
        router.post(route('breaking.search'), { ...form.data, ...payload }, {
            preserveScroll: true,
            onSuccess: () => setTimeout(fetchResults, 3000),
        });
    }

    function action(name, eventId) {
        router.post(route(name, eventId), {}, {
            preserveScroll: true,
            onSuccess: () => setTimeout(fetchResults, 1500),
        });
    }

    return (
        <AppLayout
            title="Breaking Desk"
            subtitle="Search a title or paste a URL to scrape coverage on demand (priority enrich). Then mark the resulting event breaking or force-publish its page — manual gate, ADR-0029."
        >
            <Head title="Breaking Desk" />

            <Paper variant="outlined" sx={{ p: 2.5, mb: 3 }}>
                <form onSubmit={submit}>
                    <Stack spacing={2}>
                        <ToggleButtonGroup
                            size="small"
                            exclusive
                            value={mode}
                            onChange={(_, v) => v && setMode(v)}
                        >
                            <ToggleButton value="query">
                                <SearchRoundedIcon sx={{ mr: 0.5, fontSize: 18 }} /> Search a title
                            </ToggleButton>
                            <ToggleButton value="url">Paste a URL</ToggleButton>
                        </ToggleButtonGroup>

                        <Grid container spacing={2} alignItems="center">
                            <Grid size={{ xs: 12, md: 8 }}>
                                {mode === 'query' ? (
                                    <TextField
                                        fullWidth
                                        label="Title or topic"
                                        placeholder="e.g. Anthropic Fable Mythos access"
                                        value={form.data.query}
                                        onChange={(e) => form.setData('query', e.target.value)}
                                        error={Boolean(form.errors.query)}
                                        helperText={form.errors.query}
                                    />
                                ) : (
                                    <TextField
                                        fullWidth
                                        label="Article URL"
                                        placeholder="https://www.example.com/news/story"
                                        value={form.data.url}
                                        onChange={(e) => form.setData('url', e.target.value)}
                                        error={Boolean(form.errors.url)}
                                        helperText={form.errors.url}
                                    />
                                )}
                            </Grid>
                            <Grid size={{ xs: 6, md: 2 }}>
                                <ToggleButtonGroup
                                    size="small"
                                    exclusive
                                    value={form.data.lang}
                                    onChange={(_, v) => v && form.setData('lang', v)}
                                    disabled={mode === 'url'}
                                >
                                    <ToggleButton value="en">EN</ToggleButton>
                                    <ToggleButton value="es">ES</ToggleButton>
                                </ToggleButtonGroup>
                            </Grid>
                            <Grid size={{ xs: 6, md: 2 }}>
                                <Button
                                    fullWidth
                                    type="submit"
                                    variant="contained"
                                    startIcon={<BoltRoundedIcon />}
                                    disabled={form.processing}
                                >
                                    Scrape now
                                </Button>
                            </Grid>
                        </Grid>
                        <Typography variant="caption" color="text.secondary">
                            Title search uses Google News; results are scraped at priority 9 and
                            appear below within ~a minute. URL mode scrapes that one page directly.
                        </Typography>
                    </Stack>
                </form>
            </Paper>

            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
                <Typography variant="h6">On-demand results</Typography>
                <Chip
                    size="small"
                    label={polling ? 'live · refreshes every 5s' : 'idle'}
                    color={polling ? 'success' : 'default'}
                    variant="outlined"
                />
            </Stack>

            {events.length === 0 ? (
                <Paper variant="outlined" sx={{ p: 4, textAlign: 'center' }}>
                    <Typography color="text.secondary">
                        No on-demand events yet. Scrape a title or URL above — the resulting
                        event will appear here once Curator clusters it.
                    </Typography>
                </Paper>
            ) : (
                <Stack spacing={1.5}>
                    {events.map((ev) => (
                        <Paper key={ev.id} variant="outlined" sx={{ p: 2 }}>
                            <Grid container spacing={2} alignItems="center">
                                <Grid size={{ xs: 12, md: 7 }}>
                                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                                        {ev.is_breaking && (
                                            <Chip size="small" color="error" label="BREAKING" />
                                        )}
                                        {ev.page?.is_published ? (
                                            <Chip size="small" color="success" variant="outlined" label="published" />
                                        ) : (
                                            <Chip size="small" variant="outlined" label={ev.status} />
                                        )}
                                        <Chip size="small" variant="outlined"
                                            label={`${ev.source_count} src · ${ev.article_count} art`} />
                                    </Stack>
                                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                        {ev.page?.headline || ev.topic || '(awaiting synthesis…)'}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {ev.id} · updated {ev.last_updated_at
                                            ? new Date(ev.last_updated_at).toLocaleString()
                                            : '—'}
                                    </Typography>
                                </Grid>
                                <Grid size={{ xs: 12, md: 5 }}>
                                    <Stack direction="row" spacing={1} justifyContent={{ md: 'flex-end' }} flexWrap="wrap" useFlexGap>
                                        {ev.is_breaking ? (
                                            <Button size="small" onClick={() => action('breaking.clear', ev.id)}>
                                                Clear breaking
                                            </Button>
                                        ) : (
                                            <Button size="small" variant="contained" color="error"
                                                startIcon={<BoltRoundedIcon />}
                                                onClick={() => action('breaking.mark', ev.id)}>
                                                Mark breaking
                                            </Button>
                                        )}
                                        <Button size="small" variant="outlined"
                                            disabled={ev.page?.is_published}
                                            onClick={() => action('breaking.force', ev.id)}>
                                            Force publish
                                        </Button>
                                    </Stack>
                                </Grid>
                            </Grid>
                        </Paper>
                    ))}
                </Stack>
            )}
        </AppLayout>
    );
}
