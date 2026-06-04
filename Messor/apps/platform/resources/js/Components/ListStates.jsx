import { Alert, Box, CircularProgress, Typography } from '@mui/material';

/**
 * B13 — shared empty / loading / error states for list pages.
 *
 * These give every table the same look for "nothing here", "loading…", and
 * "the source is unreachable", instead of each page hand-rolling a centred
 * <Typography> or a bespoke <Alert>. Presentation only — no data fetching.
 *
 * Two usage shapes:
 *  - Inside a table body: wrap in a single full-width row, e.g.
 *      <TableRow><TableCell colSpan={n}><EmptyState .../></TableCell></TableRow>
 *  - Standalone (cards / panels): drop the component directly.
 */

/** Empty list: a title and an optional secondary line. */
export function EmptyState({
    title = 'Nothing here yet',
    description,
    icon = null,
    sx,
}) {
    return (
        <Box sx={{ py: 4, px: 2, textAlign: 'center', ...sx }}>
            {icon ? <Box sx={{ mb: 1, color: 'text.disabled' }}>{icon}</Box> : null}
            <Typography variant="body1" color="text.secondary" sx={{ fontWeight: 600 }}>
                {title}
            </Typography>
            {description ? (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {description}
                </Typography>
            ) : null}
        </Box>
    );
}

/** In-flight load: a centred spinner with an optional label. */
export function LoadingState({ label = 'Loading…', size = 28, sx }) {
    return (
        <Box
            sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 1.25,
                py: 4,
                ...sx,
            }}
        >
            <CircularProgress size={size} />
            {label ? (
                <Typography variant="body2" color="text.secondary">
                    {label}
                </Typography>
            ) : null}
        </Box>
    );
}

/**
 * Error / unreachable state. Defaults to a `warning` severity (a degraded but
 * non-fatal source — e.g. Messor API down), pass `severity="error"` for a hard
 * failure. Renders as a standalone MUI Alert.
 */
export function ErrorState({
    title,
    message = 'Something went wrong.',
    severity = 'warning',
    sx,
}) {
    return (
        <Alert severity={severity} sx={sx}>
            {title ? <strong>{title}</strong> : null}
            {title ? ' — ' : null}
            {message}
        </Alert>
    );
}
