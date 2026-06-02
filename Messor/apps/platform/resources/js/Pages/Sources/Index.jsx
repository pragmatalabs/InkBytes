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

export default function SourcesIndex({ sources = [] }) {
    return (
        <AppLayout
            title="Sources"
            subtitle="Configured ingestion sources currently available in the platform."
        >
            <Head title="Sources" />

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Region</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>URL</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {sources.map((source) => (
                            <TableRow key={source.name} hover>
                                <TableCell sx={{ fontWeight: 600 }}>
                                    {source.name}
                                </TableCell>
                                <TableCell>{source.region}</TableCell>
                                <TableCell>
                                    <Chip
                                        size="small"
                                        label={source.status}
                                        color={
                                            source.status === 'active'
                                                ? 'success'
                                                : 'default'
                                        }
                                        variant={
                                            source.status === 'active'
                                                ? 'filled'
                                                : 'outlined'
                                        }
                                    />
                                </TableCell>
                                <TableCell>
                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                    >
                                        {source.url}
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
