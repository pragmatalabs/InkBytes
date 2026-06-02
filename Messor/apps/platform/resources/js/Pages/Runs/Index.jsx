import AppLayout from '@/Layouts/AppLayout';
import { Head } from '@inertiajs/react';
import {
    Chip,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Typography,
} from '@mui/material';

const formatDate = (value) =>
    new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
    }).format(new Date(value));

const statusColor = (status) => {
    if (status === 'running') {
        return 'warning';
    }

    if (status === 'completed') {
        return 'success';
    }

    if (status === 'failed') {
        return 'error';
    }

    return 'default';
};

export default function RunsIndex({ runs = [] }) {
    return (
        <AppLayout
            title="Execution Runs"
            subtitle="Recent scraper executions and throughput snapshots."
        >
            <Head title="Runs" />

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Run ID</TableCell>
                            <TableCell>Started</TableCell>
                            <TableCell>Duration</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell align="right">Articles</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {runs.map((run) => (
                            <TableRow key={run.id} hover>
                                <TableCell sx={{ fontWeight: 600 }}>
                                    {run.id}
                                </TableCell>
                                <TableCell>{formatDate(run.started_at)}</TableCell>
                                <TableCell>{run.duration}</TableCell>
                                <TableCell>
                                    <Chip
                                        size="small"
                                        label={run.status}
                                        color={statusColor(run.status)}
                                        variant={
                                            run.status === 'completed'
                                                ? 'filled'
                                                : 'outlined'
                                        }
                                    />
                                </TableCell>
                                <TableCell align="right">
                                    <Typography variant="body2" fontWeight={600}>
                                        {run.articles.toLocaleString()}
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </AppLayout>
    );
}
