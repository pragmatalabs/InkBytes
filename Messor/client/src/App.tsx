// src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { 
  CssBaseline, 
  AppBar, 
  Toolbar, 
  Typography, 
  Container, 
  Box, 
  Button,
  ThemeProvider,
  createTheme
} from '@mui/material';
import { ServiceProvider } from './context/ServiceContext';
import Dashboard from './components/Dashboard';
import ScrapingResults from './components/ScrapingResults';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#f50057',
    },
  },
});

const App: React.FC = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ServiceProvider>
        <Router>
          <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <AppBar position="static">
              <Toolbar>
                <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                  Messor — InkBytes
                </Typography>
                <Button color="inherit" component={Link} to="/">
                  Dashboard
                </Button>
                <Button color="inherit" component={Link} to="/results">
                  Results
                </Button>
              </Toolbar>
            </AppBar>
            
            <Container component="main" maxWidth="xl" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/results" element={<ScrapingResults />} />
              </Routes>
            </Container>
            
            <Box component="footer" sx={{ py: 3, px: 2, mt: 'auto', backgroundColor: 'background.paper' }}>
              <Container maxWidth="lg">
                <Typography variant="body2" color="text.secondary" align="center">
                  © {new Date().getFullYear()} InkBytes Technologies — Messor v1.0.0
                </Typography>
              </Container>
            </Box>
          </Box>
        </Router>
      </ServiceProvider>
    </ThemeProvider>
  );
};

export default App;