import React, { useEffect, useState } from 'react';
import {
    AppBar,
    Toolbar,
    Typography,
    Button
} from '@mui/material';
import { Link } from 'react-router-dom';
import logo from '../assets/logo.png'; // Ensure the logo image path is correct

const Header: React.FC = () => {
    const [imgError, setImgError] = useState(false);

    // For debugging purposes - log when component mounts
    useEffect(() => {
        console.log('Logo path:', logo);
        // You can also check if the logo import is working correctly
        console.log('Logo import type:', typeof logo);
    }, []);

    return (
        <AppBar position="fixed">
            <Toolbar>
                {!imgError ? (
                    <img 
                        src={logo} 
                        alt="Logo" 
                        style={{ 
                            marginRight: '10px', 
                            height: '40px', 
                            display: 'block',
                            border: '1px solid transparent' // Makes it easier to see the image boundaries
                        }} 
                        onError={(e) => {
                            console.error('Failed to load logo:', e);
                            setImgError(true);
                        }}
                    />
                ) : (
                    <div style={{ 
                        marginRight: '10px', 
                        height: '40px', 
                        width: '40px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#f0f0f0',
                        color: '#666',
                        fontSize: '10px'
                    }}>
                        Logo Error
                    </div>
                )}
                <Typography variant="h6" style={{ flexGrow: 1 }}>
                    Inkbytes Messor Dashboard
                </Typography>
                <Button color="inherit" component={Link} to="/">
                    Dashboard
                </Button>
                <Button color="inherit" component={Link} to="/results">
                    Results
                </Button>
            </Toolbar>
        </AppBar>
    );
}

export default Header;