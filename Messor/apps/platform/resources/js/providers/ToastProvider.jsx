import { usePage } from '@inertiajs/react';
import { Alert, Snackbar } from '@mui/material';
import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from 'react';

/**
 * B13 — single toast standard.
 *
 * One MUI Snackbar+Alert mounted once (inside AppLayout). Pages raise toasts
 * via the `useToast()` hook instead of rolling their own local Snackbar state.
 * Laravel `flash.success` / `flash.error` are auto-surfaced here, so a page
 * that only needs to echo a flashed message does not have to wire anything.
 */
const ToastContext = createContext({
    showToast: () => {},
    showSuccess: () => {},
    showError: () => {},
});

const ANCHOR = { vertical: 'bottom', horizontal: 'center' };
const DEFAULT_DURATION = 5000;

export function ToastProvider({ children }) {
    const page = usePage();
    const flash = page?.props?.flash;

    const [toast, setToast] = useState(null); // { severity, message, duration }

    const showToast = useCallback((message, severity = 'success', options = {}) => {
        if (!message) {
            return;
        }
        setToast({
            severity,
            message,
            duration: options.duration ?? DEFAULT_DURATION,
        });
    }, []);

    const showSuccess = useCallback(
        (message, options) => showToast(message, 'success', options),
        [showToast],
    );
    const showError = useCallback(
        (message, options) => showToast(message, 'error', options),
        [showToast],
    );

    // Auto-surface server flash. Inertia replaces `flash` on every visit, so a
    // repeated message (same text twice) still re-triggers because the object
    // identity changes per response.
    useEffect(() => {
        if (flash?.success) {
            showToast(flash.success, 'success');
        } else if (flash?.error) {
            showToast(flash.error, 'error');
        }
    }, [flash, showToast]);

    const close = useCallback((_event, reason) => {
        if (reason === 'clickaway') {
            return;
        }
        setToast(null);
    }, []);

    const value = useMemo(
        () => ({ showToast, showSuccess, showError }),
        [showToast, showSuccess, showError],
    );

    return (
        <ToastContext.Provider value={value}>
            {children}
            <Snackbar
                open={Boolean(toast)}
                autoHideDuration={toast?.duration ?? DEFAULT_DURATION}
                onClose={close}
                anchorOrigin={ANCHOR}
            >
                {toast ? (
                    <Alert
                        severity={toast.severity}
                        onClose={() => setToast(null)}
                        variant="filled"
                        sx={{ width: '100%' }}
                    >
                        {toast.message}
                    </Alert>
                ) : undefined}
            </Snackbar>
        </ToastContext.Provider>
    );
}

/** Access the shared toast API: { showToast, showSuccess, showError }. */
export function useToast() {
    return useContext(ToastContext);
}
