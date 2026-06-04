import AppLayout from '@/Layouts/AppLayout';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { Head, router, usePage } from '@inertiajs/react';
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded';
import HubRoundedIcon from '@mui/icons-material/HubRounded';
import {
    Alert,
    Box,
    Button,
    Chip,
    Paper,
    Snackbar,
    Stack,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Tooltip,
    Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';

const STATUS_COLORS = {
    published: 'success',
    draft: 'warning',
    dropped: 'default',
};

const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : '—');

export default function ModerationIndex({ events = [], stats = {} }) {
    const { flash } = usePage().props;
    const { isOperator } = useAuthRole();
    const [snack, setSnack] = useState(null);
    const [busy, setBusy] = useState(null); // `${kind}:${id}` while a command is in-flight

    useEffect(() => {
        if (flash?.success) {
            setSnack({ severity: 'success', message: flash.success });
        } else if (flash?.error) {
            setSnack({ severity: 'error', message: flash.error });
        }
    }, [flash]);

    const send = (key, routeName, id) => {
        setBusy(key);
        router.post(
            route(routeName, id),
            {},
            {
                preserveScroll: true,
                onFinish: () => setBusy(null),
            }
        );
    };

    return (
        <AppLayout
            title="Moderation"
            subtitle="Review Curator events and pages, then publish, unpublish, drop, or trigger a re-synthesize / re-cluster. Actions are sent to Curator as commands — they take effect when Curator applies them."
        >
            <Head title="Moderation" />

            <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                <Chip label={`${stats.event_count ?? 0} events`} variant="outlined" />
                <Chip label={`${stats.page_count ?? 0} pages`} variant="outlined" />
                <Chip
                    label={`${stats.published_count ?? 0} published`}
                    color="success"
                    variant="outlined"
                />
            </Stack>

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Headline / Event</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell align="right">Sources</TableCell>
                            <TableCell>Freshness</TableCell>
                            <TableCell>Published</TableCell>
                            <TableCell align="right">Cost</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {events.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={7}>
                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                        sx={{ py: 2, textAlign: 'center' }}
                                    >
                                        No events yet.
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            events.map((event) => {
                                const page = event.page;
                                const pid = page?.id;
                                const published = Boolean(page?.is_published);

                                return (
                                    <TableRow key={event.id} hover>
                                        <TableCell sx={{ maxWidth: 360 }}>
                                            <Typography
                                                variant="body2"
                                                sx={{ fontWeight: 600 }}
                                            >
                                                {page?.headline ?? (
                                                    <em>(no page synthesized)</em>
                                                )}
                                            </Typography>
                                            <Typography
                                                variant="caption"
                                                color="text.secondary"
                                                sx={{ fontFamily: 'monospace' }}
                                            >
                                                {event.id}
                                                {event.topic ? ` · ${event.topic}` : ''}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                size="small"
                                                label={event.status}
                                                color={
                                                    STATUS_COLORS[event.status] ??
                                                    'default'
                                                }
                                                variant={
                                                    event.status === 'published'
                                                        ? 'filled'
                                                        : 'outlined'
                                                }
                                            />
                                        </TableCell>
                                        <TableCell align="right">
                                            {page
                                                ? page.evidence_count
                                                : event.source_count}
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="caption">
                                                {fmt(page?.freshness_at)}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="caption">
                                                {fmt(page?.published_at)}
                                            </Typography>
                                        </TableCell>
                                        <TableCell align="right">
                                            {page?.cost_cents != null
                                                ? `${(page.cost_cents / 100).toFixed(2)}¢`
                                                : '—'}
                                        </TableCell>
                                        <TableCell align="right">
                                            <Stack
                                                direction="row"
                                                spacing={0.5}
                                                justifyContent="flex-end"
                                                flexWrap="wrap"
                                                useFlexGap
                                            >
                                                {!isOperator && (
                                                    <Typography
                                                        variant="caption"
                                                        color="text.secondary"
                                                    >
                                                        read-only
                                                    </Typography>
                                                )}
                                                {isOperator && page && !published && (
                                                    <Button
                                                        size="small"
                                                        variant="contained"
                                                        color="success"
                                                        disabled={busy != null}
                                                        onClick={() =>
                                                            send(
                                                                `pub:${pid}`,
                                                                'moderation.pages.publish',
                                                                pid
                                                            )
                                                        }
                                                    >
                                                        Publish
                                                    </Button>
                                                )}
                                                {isOperator && page && published && (
                                                    <Button
                                                        size="small"
                                                        variant="outlined"
                                                        disabled={busy != null}
                                                        onClick={() =>
                                                            send(
                                                                `unpub:${pid}`,
                                                                'moderation.pages.unpublish',
                                                                pid
                                                            )
                                                        }
                                                    >
                                                        Unpublish
                                                    </Button>
                                                )}
                                                {isOperator && page && (
                                                    <Button
                                                        size="small"
                                                        variant="outlined"
                                                        color="error"
                                                        disabled={busy != null}
                                                        onClick={() =>
                                                            send(
                                                                `drop:${pid}`,
                                                                'moderation.pages.drop',
                                                                pid
                                                            )
                                                        }
                                                    >
                                                        Drop
                                                    </Button>
                                                )}
                                                {isOperator && (
                                                    <Tooltip title="Re-run synthesis for this event">
                                                        <span>
                                                            <Button
                                                                size="small"
                                                                variant="text"
                                                                startIcon={
                                                                    <AutorenewRoundedIcon fontSize="small" />
                                                                }
                                                                disabled={busy != null}
                                                                onClick={() =>
                                                                    send(
                                                                        `resyn:${event.id}`,
                                                                        'moderation.events.resynthesize',
                                                                        event.id
                                                                    )
                                                                }
                                                            >
                                                                Re-synth
                                                            </Button>
                                                        </span>
                                                    </Tooltip>
                                                )}
                                                {isOperator && (
                                                    <Tooltip title="Re-cluster this event's articles">
                                                        <span>
                                                            <Button
                                                                size="small"
                                                                variant="text"
                                                                startIcon={
                                                                    <HubRoundedIcon fontSize="small" />
                                                                }
                                                                disabled={busy != null}
                                                                onClick={() =>
                                                                    send(
                                                                        `reclus:${event.id}`,
                                                                        'moderation.events.recluster',
                                                                        event.id
                                                                    )
                                                                }
                                                            >
                                                                Re-cluster
                                                            </Button>
                                                        </span>
                                                    </Tooltip>
                                                )}
                                            </Stack>
                                        </TableCell>
                                    </TableRow>
                                );
                            })
                        )}
                    </TableBody>
                </Table>
            </TableContainer>

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
