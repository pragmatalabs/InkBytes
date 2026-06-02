import AppLayout from '@/Layouts/AppLayout';
import { Head, router } from '@inertiajs/react';
import OpenInNewRoundedIcon from '@mui/icons-material/OpenInNewRounded';
import {
    Box,
    Button,
    Chip,
    FormControl,
    InputLabel,
    Link,
    MenuItem,
    Pagination,
    Paper,
    Select,
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
import { useCallback, useEffect, useMemo, useState } from 'react';

const formatDateTime = (value) => {
    if (!value) {
        return '—';
    }

    try {
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
        }).format(new Date(value));
    } catch (error) {
        return value;
    }
};

const normalizeFilterValue = (value) => (value == null ? '' : value);

export default function ArticlesIndex({
    articles = [],
    pagination = {},
    filters = {},
    filterOptions = {},
}) {
    const [search, setSearch] = useState(normalizeFilterValue(filters.search));
    const [source, setSource] = useState(normalizeFilterValue(filters.source));
    const [language, setLanguage] = useState(normalizeFilterValue(filters.language));
    const [perPage, setPerPage] = useState(String(filters.perPage ?? 25));

    useEffect(() => {
        setSearch(normalizeFilterValue(filters.search));
        setSource(normalizeFilterValue(filters.source));
        setLanguage(normalizeFilterValue(filters.language));
        setPerPage(String(filters.perPage ?? 25));
    }, [filters.search, filters.source, filters.language, filters.perPage]);

    const perPageOptions = useMemo(() => [10, 25, 50, 100], []);

    const applyFilters = useCallback(
        ({ page = 1, reset = false } = {}) => {
            const payload = {
                page,
                perPage: Number(reset ? 25 : perPage),
            };

            if (!reset && search.trim()) {
                payload.search = search.trim();
            }

            if (!reset && source) {
                payload.source = source;
            }

            if (!reset && language) {
                payload.language = language;
            }

            router.get(route('articles.index'), payload, {
                preserveState: true,
                preserveScroll: true,
                replace: true,
            });
        },
        [search, source, language, perPage],
    );

    const onSubmit = (event) => {
        event.preventDefault();
        applyFilters({ page: 1 });
    };

    const onReset = () => {
        setSearch('');
        setSource('');
        setLanguage('');
        setPerPage('25');
        applyFilters({ reset: true, page: 1 });
    };

    return (
        <AppLayout
            title="Articles"
            subtitle="Search and browse ingested scraped articles stored in the platform database."
        >
            <Head title="Articles" />

            <Paper component="form" onSubmit={onSubmit} sx={{ p: 2.5, mb: 2 }}>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
                    <TextField
                        size="small"
                        label="Search title, summary, URL"
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        sx={{ minWidth: 280, flex: 1 }}
                    />

                    <FormControl size="small" sx={{ minWidth: 180 }}>
                        <InputLabel id="article-source-label">Source</InputLabel>
                        <Select
                            labelId="article-source-label"
                            label="Source"
                            value={source}
                            onChange={(event) => setSource(event.target.value)}
                        >
                            <MenuItem value="">All sources</MenuItem>
                            {(filterOptions.sources || []).map((item) => (
                                <MenuItem key={item} value={item}>
                                    {item}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 140 }}>
                        <InputLabel id="article-language-label">Language</InputLabel>
                        <Select
                            labelId="article-language-label"
                            label="Language"
                            value={language}
                            onChange={(event) => setLanguage(event.target.value)}
                        >
                            <MenuItem value="">All languages</MenuItem>
                            {(filterOptions.languages || []).map((item) => (
                                <MenuItem key={item} value={item}>
                                    {item}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 110 }}>
                        <InputLabel id="article-per-page-label">Rows</InputLabel>
                        <Select
                            labelId="article-per-page-label"
                            label="Rows"
                            value={perPage}
                            onChange={(event) => setPerPage(event.target.value)}
                        >
                            {perPageOptions.map((option) => (
                                <MenuItem key={option} value={String(option)}>
                                    {option}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <Stack direction="row" spacing={1}>
                        <Button type="submit" variant="contained">
                            Apply
                        </Button>
                        <Button type="button" variant="outlined" onClick={onReset}>
                            Reset
                        </Button>
                    </Stack>
                </Stack>
            </Paper>

            <Paper sx={{ p: 1.5, mb: 1.5 }}>
                <Typography variant="body2" color="text.secondary">
                    Showing {articles.length} of {pagination.total ?? 0} articles
                </Typography>
            </Paper>

            <TableContainer component={Paper}>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>Title</TableCell>
                            <TableCell>Source</TableCell>
                            <TableCell>Language</TableCell>
                            <TableCell>Published</TableCell>
                            <TableCell>URL</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {articles.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5}>
                                    <Typography variant="body2" color="text.secondary">
                                        No articles found with the current filters.
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            articles.map((article) => (
                                <TableRow key={article.external_id} hover>
                                    <TableCell>
                                        <Typography variant="body2" fontWeight={600}>
                                            {article.title}
                                        </Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {article.summary || 'No summary available.'}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Chip
                                            size="small"
                                            label={article.article_source || 'Unknown'}
                                            variant="outlined"
                                        />
                                    </TableCell>
                                    <TableCell>{article.language || '—'}</TableCell>
                                    <TableCell>{formatDateTime(article.publish_date || article.fetched_on)}</TableCell>
                                    <TableCell>
                                        {article.article_url ? (
                                            <Link
                                                href={article.article_url}
                                                target="_blank"
                                                rel="noreferrer"
                                                underline="hover"
                                                sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}
                                            >
                                                Open
                                                <OpenInNewRoundedIcon sx={{ fontSize: 14 }} />
                                            </Link>
                                        ) : (
                                            '—'
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </TableContainer>

            {(pagination.lastPage || 1) > 1 ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                    <Pagination
                        color="primary"
                        page={pagination.page ?? 1}
                        count={pagination.lastPage ?? 1}
                        onChange={(_, page) => applyFilters({ page })}
                    />
                </Box>
            ) : null}
        </AppLayout>
    );
}
