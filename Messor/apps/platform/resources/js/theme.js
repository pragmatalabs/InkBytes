import { createTheme } from '@mui/material/styles';

const theme = createTheme({
    palette: {
        mode: 'light',
        primary: {
            main: '#0f5fd7',
        },
        secondary: {
            main: '#0c7f6f',
        },
        background: {
            default: '#f4f7fb',
            paper: '#ffffff',
        },
        text: {
            primary: '#10213a',
            secondary: '#4f5f79',
        },
    },
    shape: {
        borderRadius: 14,
    },
    typography: {
        fontFamily:
            '"Figtree","Plus Jakarta Sans","Inter","Segoe UI","Roboto","Helvetica","Arial",sans-serif',
        h4: {
            fontWeight: 700,
        },
        h5: {
            fontWeight: 700,
        },
    },
    components: {
        MuiPaper: {
            defaultProps: {
                elevation: 0,
            },
            styleOverrides: {
                root: {
                    border: '1px solid #e2e8f0',
                },
            },
        },
        MuiButton: {
            styleOverrides: {
                root: {
                    textTransform: 'none',
                    fontWeight: 600,
                    borderRadius: 10,
                },
            },
        },
    },
});

export default theme;
