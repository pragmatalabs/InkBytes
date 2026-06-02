import AppLayout from '@/Layouts/AppLayout';
import { Head } from '@inertiajs/react';
import {
    Alert,
    Box,
    Button,
    Chip,
    FormControlLabel,
    Paper,
    Stack,
    Switch,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography,
} from '@mui/material';
import { useCallback, useEffect, useMemo, useState } from 'react';

const formatBytes = (bytes) => {
    if (!bytes || Number.isNaN(Number(bytes))) {
        return '0 B';
    }

    const value = Number(bytes);
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const index = Math.min(
        Math.floor(Math.log(value) / Math.log(1024)),
        units.length - 1,
    );

    const normalized = value / 1024 ** index;
    return `${normalized.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
};

const formatPorts = (ports) => {
    if (!Array.isArray(ports) || ports.length === 0) {
        return '—';
    }

    return ports
        .map((port) => {
            if (!port.public_port || !port.private_port) {
                return `${port.private_port ?? '?'}${port.type ? `/${port.type}` : ''}`;
            }

            const host = port.ip || '0.0.0.0';
            return `${host}:${port.public_port} -> ${port.private_port}${port.type ? `/${port.type}` : ''}`;
        })
        .join(', ');
};

const stateColor = (state) => {
    if (state === 'running') {
        return 'success';
    }

    if (state === 'paused') {
        return 'warning';
    }

    if (state === 'exited' || state === 'dead') {
        return 'error';
    }

    return 'default';
};

export default function RuntimeIndex({ snapshot }) {
    const [data, setData] = useState(snapshot);
    const [loading, setLoading] = useState(false);
    const [autoRefresh, setAutoRefresh] = useState(true);

    const fetchSnapshot = useCallback(async () => {
        setLoading(true);
        try {
            const response = await window.axios.get(route('runtime.snapshot'));
            setData(response.data);
        } catch (error) {
            setData((current) => ({
                ...current,
                available: false,
                message: 'Failed to refresh runtime snapshot.',
            }));
            console.error('Failed to fetch runtime snapshot', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!autoRefresh) {
            return undefined;
        }

        const intervalId = window.setInterval(fetchSnapshot, 5000);
        return () => {
            window.clearInterval(intervalId);
        };
    }, [autoRefresh, fetchSnapshot]);

    const updatedAt = useMemo(() => {
        if (!data?.updated_at) {
            return 'Unknown';
        }

        return new Date(data.updated_at).toLocaleTimeString();
    }, [data?.updated_at]);

    return (
        <AppLayout
            title="Runtime Monitor"
            subtitle="Live container and process visibility for the active Docker compose project."
        >
            <Head title="Runtime Monitor" />

            <Paper sx={{ p: 2.5, mb: 2 }}>
                <Stack
                    direction={{ xs: 'column', md: 'row' }}
                    justifyContent="space-between"
                    spacing={1.5}
                >
                    <Box>
                        <Typography variant="subtitle1" fontWeight={700}>
                            Project: {data?.project || 'Unknown'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Last updated: {updatedAt}
                        </Typography>
                    </Box>

                    <Stack
                        direction={{ xs: 'column', sm: 'row' }}
                        spacing={1.5}
                        alignItems={{ xs: 'flex-start', sm: 'center' }}
                    >
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={autoRefresh}
                                    onChange={(event) =>
                                        setAutoRefresh(event.target.checked)
                                    }
                                />
                            }
                            label="Auto refresh (5s)"
                        />
                        <Button
                            variant="outlined"
                            onClick={fetchSnapshot}
                            disabled={loading}
                        >
                            {loading ? 'Refreshing...' : 'Refresh now'}
                        </Button>
                    </Stack>
                </Stack>
            </Paper>

            {!data?.available ? (
                <Alert severity="warning" sx={{ mb: 2 }}>
                    {data?.message ||
                        'Runtime data is currently unavailable. Ensure Docker socket access is configured.'}
                </Alert>
            ) : null}

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Service</TableCell>
                            <TableCell>Container</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell align="right">CPU</TableCell>
                            <TableCell align="right">Memory</TableCell>
                            <TableCell align="right">PIDs</TableCell>
                            <TableCell>Ports</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {(data?.containers || []).map((container) => (
                            <TableRow key={container.id} hover>
                                <TableCell sx={{ fontWeight: 600 }}>
                                    {container.service || 'unknown'}
                                </TableCell>
                                <TableCell>
                                    <Typography variant="body2" fontWeight={600}>
                                        {container.name}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {container.id}
                                    </Typography>
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        size="small"
                                        color={stateColor(container.state)}
                                        label={container.status || container.state}
                                        variant="outlined"
                                    />
                                </TableCell>
                                <TableCell align="right">
                                    {Number(container?.stats?.cpu_percent ?? 0).toFixed(2)}%
                                </TableCell>
                                <TableCell align="right">
                                    <Typography variant="body2">
                                        {formatBytes(container?.stats?.memory_usage)}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {Number(container?.stats?.memory_percent ?? 0).toFixed(2)}%
                                    </Typography>
                                </TableCell>
                                <TableCell align="right">
                                    {container?.stats?.pids ?? 0}
                                </TableCell>
                                <TableCell>{formatPorts(container.ports)}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Stack spacing={2} sx={{ mt: 2 }}>
                {(data?.containers || []).map((container) => (
                    <Paper key={`${container.id}-processes`} sx={{ p: 2 }}>
                        <Typography variant="subtitle2" fontWeight={700}>
                            {container.service} processes
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            {container.name}
                        </Typography>

                        <Table size="small" sx={{ mt: 1.5 }}>
                            <TableHead>
                                <TableRow>
                                    <TableCell>User</TableCell>
                                    <TableCell>PID</TableCell>
                                    <TableCell align="right">%CPU</TableCell>
                                    <TableCell align="right">%MEM</TableCell>
                                    <TableCell>Command</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {(container.processes || []).length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} sx={{ color: 'text.secondary' }}>
                                            Process details not available.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    (container.processes || []).map((process, index) => (
                                        <TableRow key={`${container.id}-process-${index}`}>
                                            <TableCell>{process.user || '—'}</TableCell>
                                            <TableCell>{process.pid || '—'}</TableCell>
                                            <TableCell align="right">{process.cpu || '0.0'}</TableCell>
                                            <TableCell align="right">{process.memory || '0.0'}</TableCell>
                                            <TableCell sx={{ fontFamily: 'monospace' }}>
                                                {process.command || '—'}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </Paper>
                ))}
            </Stack>
        </AppLayout>
    );
}
