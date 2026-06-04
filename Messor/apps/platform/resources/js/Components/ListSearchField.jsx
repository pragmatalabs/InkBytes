import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import { Box, InputAdornment, TextField } from '@mui/material';
import { useEffect, useState } from 'react';

/**
 * Search box for a server-paginated list (B7). Submits on Enter (so we don't
 * fire a request per keystroke) and calls back with the trimmed term. Seeded
 * from the server-echoed value and kept in sync if it changes underneath.
 *
 * @param {string} value           current q from server state
 * @param {(q: string) => void} onSearch
 * @param {string} placeholder
 */
export default function ListSearchField({
    value = '',
    onSearch,
    placeholder = 'Search… (press Enter)',
    label = 'Search',
    sx,
}) {
    const [text, setText] = useState(value);

    useEffect(() => {
        setText(value ?? '');
    }, [value]);

    const submit = (event) => {
        event.preventDefault();
        onSearch(text.trim());
    };

    return (
        <Box component="form" onSubmit={submit} sx={sx}>
            <TextField
                fullWidth
                size="small"
                label={label}
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder={placeholder}
                InputProps={{
                    startAdornment: (
                        <InputAdornment position="start">
                            <SearchRoundedIcon fontSize="small" />
                        </InputAdornment>
                    ),
                }}
            />
        </Box>
    );
}
