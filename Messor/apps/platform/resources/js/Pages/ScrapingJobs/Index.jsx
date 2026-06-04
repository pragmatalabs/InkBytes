import AppLayout from '@/Layouts/AppLayout';
import { useAuthRole } from '@/Hooks/useAuthRole';
import { Head } from '@inertiajs/react';
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
    TextField,
    Typography,
} from '@mui/material';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const statusColor = (status) => {
    if (status === 'running') {
        return 'info';
    }

    if (status === 'completed') {
        return 'success';
    }

    if (status === 'failed') {
        return 'error';
    }

    return 'default';
};

const statusLabel = (status) => {
    if (!status) {
        return 'Unknown';
    }

    return status.charAt(0).toUpperCase() + status.slice(1);
};

const formatDateTime = (value) => {
    if (!value) {
        return '—';
    }

    return new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
    }).format(new Date(value));
};

const formatDuration = (seconds) => {
    if (!Number.isFinite(Number(seconds))) {
        return '—';
    }

    const total = Math.max(0, Number(seconds));
    const mins = Math.floor(total / 60);
    const secs = Math.floor(total % 60);
    return `${mins}m ${secs}s`;
};

const isActiveStatus = (status) => ['pending', 'running'].includes(status);

export default function ScrapingJobsIndex({ jobs: initialJobs = [] }) {
    const { isOperator } = useAuthRole();
    const [jobs, setJobs] = useState(initialJobs);
    const [triggerName, setTriggerName] = useState('');
    const [triggering, setTriggering] = useState(false);
    const [selectedJobId, setSelectedJobId] = useState(null);
    const [logLines, setLogLines] = useState([]);
    const [streamState, setStreamState] = useState('idle');
    const [toast, setToast] = useState({
        open: false,
        message: '',
        severity: 'success',
    });

    const logContainerRef = useRef(null);

    const activeJobExists = useMemo(
        () => jobs.some((job) => isActiveStatus(job.status)),
        [jobs],
    );

    const selectedJob = useMemo(
        () => jobs.find((job) => job.id === selectedJobId) || null,
        [jobs, selectedJobId],
    );

    const fetchJobs = useCallback(async () => {
        try {
            const response = await window.axios.get(route('scraping.status'));
            setJobs(Array.isArray(response.data?.data) ? response.data.data : []);
        } catch (error) {
            console.error('Failed to fetch scraping jobs', error);
        }
    }, []);

    useEffect(() => {
        const intervalId = window.setInterval(fetchJobs, 5000);
        return () => {
            window.clearInterval(intervalId);
        };
    }, [fetchJobs]);

    useEffect(() => {
        if (!selectedJobId) {
            return undefined;
        }

        setLogLines([]);
        setStreamState('live');

        const eventSource = new EventSource(route('scraping.stream', { id: selectedJobId }));

        eventSource.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);

                if (payload.type === 'line' && typeof payload.line === 'string') {
                    setLogLines((current) => [...current, payload.line].slice(-2000));
                }

                if (payload.type === 'end') {
                    setStreamState('ended');
                    eventSource.close();
                    fetchJobs();
                }
            } catch (error) {
                setLogLines((current) => [...current, event.data].slice(-2000));
            }
        };

        eventSource.onerror = () => {
            setStreamState((current) => (current === 'ended' ? current : 'error'));
            eventSource.close();
        };

        return () => {
            eventSource.close();
        };
    }, [fetchJobs, selectedJobId]);

    useEffect(() => {
        if (!selectedJob) {
            return;
        }

        if (['completed', 'failed'].includes(selectedJob.status) && streamState === 'live') {
            setStreamState('ended');
        }
    }, [selectedJob, streamState]);

    useEffect(() => {
        if (!logContainerRef.current) {
            return;
        }

        logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }, [logLines, streamState]);

    const handleTrigger = async () => {
        setTriggering(true);

        try {
            const response = await window.axios.post(route('scraping.trigger'), {
                name: triggerName.trim(),
            });

            const createdJob = response.data?.data;
            setToast({
                open: true,
                message: 'Scraping job started successfully.',
                severity: 'success',
            });

            await fetchJobs();

            if (createdJob?.id) {
                setSelectedJobId(createdJob.id);
            }
        } catch (error) {
            const message =
                error?.response?.data?.message ||
                'Unable to trigger scraping job right now.';

            setToast({
                open: true,
                message,
                severity: 'error',
            });
        } finally {
            setTriggering(false);
        }
    };

    return (
        <AppLayout
            title="Scraping Control Panel"
            subtitle="Trigger scraping workers, monitor run status, and follow live logs."
        >
            <Head title="Scraping Control Panel" />

            {isOperator ? (
                <Paper sx={{ p: 2.5, mb: 2 }}>
                    <Stack
                        direction={{ xs: 'column', md: 'row' }}
                        spacing={1.5}
                        alignItems={{ xs: 'stretch', md: 'center' }}
                    >
                        <TextField
                            size="small"
                            label="Job name"
                            value={triggerName}
                            onChange={(event) =>
                                setTriggerName(event.target.value)
                            }
                            sx={{ minWidth: 260, flex: 1 }}
                        />
                        <Button
                            variant="contained"
                            onClick={handleTrigger}
                            disabled={triggering || activeJobExists}
                        >
                            {triggering ? 'Starting...' : '▶ Iniciar Scraping'}
                        </Button>
                    </Stack>

                    {activeJobExists ? (
                        <Alert severity="info" sx={{ mt: 1.5 }}>
                            A scraping job is already pending or running.
                        </Alert>
                    ) : null}
                </Paper>
            ) : null}

            <TableContainer component={Paper} sx={{ mb: 2 }}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Triggered By</TableCell>
                            <TableCell>Started At</TableCell>
                            <TableCell>Duration</TableCell>
                            <TableCell>Progress</TableCell>
                            <TableCell align="right">Exit Code</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {jobs.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={7}>
                                    <Typography variant="body2" color="text.secondary">
                                        No scraping jobs found yet.
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            jobs.map((job) => (
                                <TableRow
                                    key={job.id}
                                    hover
                                    onClick={() => setSelectedJobId(job.id)}
                                    selected={selectedJobId === job.id}
                                    sx={{ cursor: 'pointer' }}
                                >
                                    <TableCell sx={{ fontWeight: 600 }}>{job.name}</TableCell>
                                    <TableCell>
                                        <Chip
                                            size="small"
                                            color={statusColor(job.status)}
                                            label={statusLabel(job.status)}
                                            variant={job.status === 'completed' ? 'filled' : 'outlined'}
                                            sx={
                                                job.status === 'running'
                                                    ? {
                                                          '@keyframes pulse': {
                                                              '0%': { opacity: 0.55 },
                                                              '50%': { opacity: 1 },
                                                              '100%': { opacity: 0.55 },
                                                          },
                                                          animation: 'pulse 1.4s ease-in-out infinite',
                                                      }
                                                    : undefined
                                            }
                                        />
                                    </TableCell>
                                    <TableCell>{job.triggered_by || 'system'}</TableCell>
                                    <TableCell>{formatDateTime(job.started_at)}</TableCell>
                                    <TableCell>{formatDuration(job.duration_seconds)}</TableCell>
                                    <TableCell>{job.progress ?? '—'}</TableCell>
                                    <TableCell align="right">{job.exit_code ?? '—'}</TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </TableContainer>

            {selectedJob ? (
                <Paper sx={{ p: 2 }}>
                    <Stack
                        direction={{ xs: 'column', sm: 'row' }}
                        justifyContent="space-between"
                        spacing={1}
                        sx={{ mb: 1.25 }}
                    >
                        <Box>
                            <Typography variant="subtitle2" fontWeight={700}>
                                Live Log Viewer — #{selectedJob.id} {selectedJob.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {selectedJob.log_path || 'Local log mirror enabled.'}
                            </Typography>
                        </Box>
                        <Chip
                            size="small"
                            color={
                                streamState === 'live'
                                    ? 'success'
                                    : streamState === 'error'
                                      ? 'error'
                                      : 'default'
                            }
                            label={streamState === 'live' ? '● LIVE' : '■ ENDED'}
                            variant={streamState === 'live' ? 'filled' : 'outlined'}
                        />
                    </Stack>

                    <Box
                        ref={logContainerRef}
                        sx={{
                            backgroundColor: '#0b1220',
                            color: '#e5e7eb',
                            borderRadius: 1.5,
                            border: '1px solid #1f2937',
                            p: 1.5,
                            minHeight: 260,
                            maxHeight: 420,
                            overflowY: 'auto',
                        }}
                    >
                        <Typography
                            component="pre"
                            sx={{
                                m: 0,
                                fontFamily:
                                    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                fontSize: 12,
                                lineHeight: 1.5,
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                            }}
                        >
                            {logLines.length > 0
                                ? logLines.join('\n')
                                : 'Waiting for log output...'}
                        </Typography>
                    </Box>
                </Paper>
            ) : null}

            <Snackbar
                open={toast.open}
                autoHideDuration={3500}
                onClose={() => setToast((current) => ({ ...current, open: false }))}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            >
                <Alert
                    severity={toast.severity}
                    onClose={() => setToast((current) => ({ ...current, open: false }))}
                    variant="filled"
                    sx={{ width: '100%' }}
                >
                    {toast.message}
                </Alert>
            </Snackbar>
        </AppLayout>
    );
}
