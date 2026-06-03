import React, { useState, useEffect, useCallback } from 'react';
import {
    Container,
    Typography,
    Button,
    CircularProgress,
    Card,
    CardContent,
    CardHeader,
    Box,
    Grid,
    MenuItem,
    FormControl,
    InputLabel,
    Select,
    Pagination,
    Paper,
    IconButton
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import RefreshIcon from '@mui/icons-material/Refresh';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import { ScraperService } from '../services/ScraperService';
import { FetchScrapingResultsOptions } from '../services/ApiService';
import Header from './Header';
import ConsoleLog from './ConsoleLog';
import { useServices } from '../context/ServiceContext';
import ScrapingResults from './ScrapingResults';

// Define proper types for messages
interface LogMessage {
    timestamp: string;
    message: string;
    level: 'info' | 'error' | 'warning' | 'success';
}

// Define operation panel interface
interface OperationPanel {
    id: number;
    title: string;
    description: string;
    controls: string[];
    status: 'Active' | 'Inactive' | 'Standby' | 'Running';
    icon?: React.ReactNode;
}

// Outlet options — loaded dynamically from /api/outlets; fallback while loading
const DEFAULT_OUTLET_OPTIONS = ["All Outlets"];

// Date filter options
const dateOptions = [
    { value: "today", label: "Today" },
    { value: "yesterday", label: "Yesterday" },
    { value: "last7days", label: "Last 7 Days" },
    { value: "last30days", label: "Last 30 Days" },
    { value: "alltime", label: "All Time" }
];

const Dashboard: React.FC = () => {
    const { apiService } = useServices();
    
    // State with proper typing
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [logs, setLogs] = useState<LogMessage[]>([]);
    const [error, setError] = useState<string>('');
    const [outletOptions, setOutletOptions] = useState<string[]>(DEFAULT_OUTLET_OPTIONS);
    
    // Filter states
    const [showFilters, setShowFilters] = useState<boolean>(false);
    const [selectedOutlet, setSelectedOutlet] = useState<string>("All Outlets");
    const [dateFilter, setDateFilter] = useState<string>("alltime");
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [totalPages, setTotalPages] = useState<number>(1);
    const [refreshTrigger, setRefreshTrigger] = useState<number>(0);
    
    // State for operation panels
    const [operationPanels, setOperationPanels] = useState<OperationPanel[]>([
        {
            id: 1,
            title: 'News Scraping',
            description: 'Scrape news articles from configured sources',
            controls: ['Start Scraping', 'Stop', 'Configure Sources'],
            status: 'Standby'
        },
        {
            id: 2,
            title: 'Data Processing',
            description: 'Process and analyze collected news data',
            controls: ['Process Data', 'Export Results', 'Configure Pipeline'],
            status: 'Inactive'
        },
        {
            id: 3,
            title: 'System Monitoring',
            description: 'Monitor performance and resource usage',
            controls: ['View Metrics', 'Generate Report', 'Set Alerts'],
            status: 'Active'
        },
        {
            id: 4,
            title: 'Queue Management',
            description: 'Manage RabbitMQ message queues and tasks',
            controls: ['View Queues', 'Purge Queue', 'Restart Service'],
            status: 'Active'
        }
    ]);

    const scraperApiKey = import.meta.env.VITE_API_KEY || 'ghyuhjbjhjhhjhjhj';
    const scraperBaseUrl = import.meta.env.VITE_API_HOST || 'http://localhost:8050';

    // Use a consistent API instance
    const api = React.useMemo(() => 
        new ScraperService(
            {
                apiKey: scraperApiKey,
                baseUrl: scraperBaseUrl
            }
        ), 
    [scraperApiKey, scraperBaseUrl]);

    // Connect to WebSocket on component mount
    const connectToWebSocket = useCallback(async () => {
        try {
            await api.connect();
            setIsConnected(true);
            setError('');
            addLog('Successfully connected to scraper service', 'success');
            
            // Update News Scraping panel status
            updatePanelStatus(1, 'Standby');
        } catch (err) {
            setIsConnected(false);
            const errorMessage = 'Failed to connect to WebSocket. Please check your API key and try again.';
            setError(errorMessage);
            addLog(errorMessage, 'error');
            console.error(err);
            
            // Update News Scraping panel status
            updatePanelStatus(1, 'Inactive');
        }
    }, [api]);

    // Handle logging in a consistent format for CLI-like interface
    const addLog = (message: string, level: LogMessage['level'] = 'info') => {
        // Extremely selective logging - only show essential messages
        // Skip all system auto-logs, rabbitMQ messages, and informational/debug messages
        
        // 1. Skip all non-essential messages that aren't directly relevant to user commands
        if (
            // Skip any WebSocket-related messages
            message.includes('WebSocket') ||
            message.includes('connection') || 
            message.includes('Connection') ||
            
            // Skip all RabbitMQ messages except errors
            (message.includes('RabbitMQ') && !message.includes('ERROR')) ||
            message.includes('Consumer') ||
            message.includes('Queue') ||
            
            // Skip all system status messages that aren't critical
            message.includes('Successfully connected') ||
            message.includes('Heartbeat') ||
            message.includes('tag') ||
            message.includes('server')
        ) {
            return; // Don't display these messages in the CLI console at all
        }

        // 2. Format messages to look more like CLI output
        let formattedMessage = message;
        
        // If the message already starts with $, it's a command entered by user
        if (!message.startsWith('$')) {
            // For system and auto-generated messages, add command-like prefixes
            if (message.toLowerCase().includes('scrape')) {
                formattedMessage = `[scraper] ${message}`;
            } else if (message.includes('stopping') || message.includes('Stop')) {
                formattedMessage = `[system] ${message}`;
            } else if (message.includes('configure') || message.includes('Configuration')) {
                formattedMessage = `[config] ${message}`;
            } else if (message.includes('RabbitMQ') && message.includes('ERROR')) {
                // Only show RabbitMQ errors
                formattedMessage = `[rabbit:error] ${message.replace('RabbitMQ: ', '')}`;
            } else if (level === 'error') {
                formattedMessage = `[error] ${message}`;
            } else if (level === 'warning') {
                formattedMessage = `[warn] ${message}`;
            } else if (level === 'success') {
                formattedMessage = `[success] ${message}`;
            } else if (message.startsWith('  ')) {
                // Preserve indented help text formatting
                formattedMessage = message;
            } else {
                formattedMessage = `[info] ${message}`;
            }
        }
        
        // Check for duplicate messages - don't add if the message is the same as the last one
        const isDuplicate = (prevLogs: LogMessage[]) => {
            if (prevLogs.length === 0) return false;
            const lastLog = prevLogs[prevLogs.length - 1];
            return lastLog.message === formattedMessage;
        };
        
        // Create new log message
        const newLog: LogMessage = {
            timestamp: new Date().toISOString(),
            message: formattedMessage,
            level
        };
        
        // Add to logs if not a duplicate
        setLogs(prevLogs => isDuplicate(prevLogs) ? prevLogs : [...prevLogs, newLog]);
    };

    // Update operation panel status
    const updatePanelStatus = (panelId: number, newStatus: OperationPanel['status']) => {
        setOperationPanels(prevPanels => 
            prevPanels.map(panel => 
                panel.id === panelId ? { ...panel, status: newStatus } : panel
            )
        );
    };

    // Connect on component mount and show welcome message
    useEffect(() => {
        // Clear any existing logs
        setLogs([]);
        
        // Add welcome message and initial information - just once
        addLog('Welcome to Messor CLI Console', 'success');
        addLog('Messor - InkBytes News Harvester v1.0.0', 'info');
        addLog('Type \'help\' to see available commands', 'info');
        addLog('Initializing system...', 'info');
        
        // Connect after a short delay to show the connection process
        setTimeout(() => {
            connectToWebSocket();
        }, 800);
        
        // Cleanup on unmount
        return () => {
            api.disconnect();
        };
    }, [api, connectToWebSocket]); // Removed addLog from dependencies to prevent re-running
    
    // Load outlet list from Messor API
    useEffect(() => {
        api.getOutlets?.()
            .then(outlets => {
                if (outlets?.length) {
                    setOutletOptions([
                        "All Outlets",
                        ...outlets.map((o: { display_name?: string; name: string }) =>
                            o.display_name || o.name
                        ),
                    ]);
                }
            })
            .catch(() => { /* keep defaults */ });
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [api]);

    // Fetch initial scraping results
    useEffect(() => {
        // Initial fetch with default filters
        fetchScrapingResults(1, "All Outlets", "alltime");
        
        // Set up refresh interval - every 2 minutes
        const intervalId = setInterval(() => {
            fetchScrapingResults(currentPage, selectedOutlet, dateFilter);
        }, 120000); // 2 minutes
        
        return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Single scraping handler
    const handleScrape = async () => {
        if (!isConnected) {
            const errorMessage = 'Not connected to WebSocket';
            setError(errorMessage);
            addLog(errorMessage, 'error');
            return;
        }

        setIsLoading(true);
        addLog('Starting scraping operation...', 'info');
        setError('');
        
        // Update News Scraping panel status
        updatePanelStatus(1, 'Running');

        try {
            api.startScrape(
                (log) => addLog(log, 'info'),
                () => {
                    setIsLoading(false);
                    addLog('Scraping completed', 'success');
                    updatePanelStatus(1, 'Standby');
                },
                (error) => {
                    setIsLoading(false);
                    setError(`Scraping failed: ${error}`);
                    addLog(`Scraping failed: ${error}`, 'error');
                    updatePanelStatus(1, 'Inactive');
                }
            );
        } catch (err) {
            setIsLoading(false);
            const errorMessage = 'Failed to start scraping. Please try reconnecting.';
            setError(errorMessage);
            addLog(errorMessage, 'error');
            console.error(err);
            updatePanelStatus(1, 'Inactive');
        }
    };


    // Function to fetch scraping results with filters
    const fetchScrapingResults = useCallback(async (
        page: number = currentPage,
        outlet: string = selectedOutlet,
        date: string = dateFilter
    ) => {
        try {
            setIsLoading(true);
            
            // Calculate API pagination defaults
            const limit = 10;
            
            // Build query options for API service
            const queryOptions: FetchScrapingResultsOptions = {
                limit,
                page
            };
            
            // Apply date filters
            if (date === 'today') {
                queryOptions.filterToday = true;
            } else if (date === 'yesterday') {
                const yesterday = new Date();
                yesterday.setDate(yesterday.getDate() - 1);
                const startOfYesterday = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate()).toISOString();
                const endOfYesterday = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 23, 59, 59).toISOString();
                queryOptions.startDate = startOfYesterday;
                queryOptions.endDate = endOfYesterday;
            } else if (date === 'last7days') {
                const sevenDaysAgo = new Date();
                sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
                queryOptions.startDate = sevenDaysAgo.toISOString();
            } else if (date === 'last30days') {
                const thirtyDaysAgo = new Date();
                thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                queryOptions.startDate = thirtyDaysAgo.toISOString();
            }
            
            // Apply outlet filter if not "All Outlets"
            if (outlet !== "All Outlets") {
                queryOptions.filterOutlet = outlet;
            }
            
            // Fetch results from API and get pagination info
            const response = await apiService.fetchScrapingResults(queryOptions);
            
            // Extract and use pagination metadata
            if (response.meta?.pagination) {
                setTotalPages(response.meta.pagination.pageCount || 1);
            } else {
                setTotalPages(1);
            }
            
            setIsLoading(false);
            // Use a local function to log success to avoid dependency cycle
            const logMessage = `Fetched scraping results with filters: outlet=${outlet}, date=${date}, page=${page}`;
            console.log(logMessage);
            addLog(logMessage, 'success');
        } catch (error) {
            setIsLoading(false);
            // Use a local log function to avoid dependency cycle
            const errorMessage = `Error fetching scraping results: ${error}`;
            console.error(errorMessage);
            addLog(errorMessage, 'error');
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [apiService]);
    
    // Handle filters change
    const handleFiltersChange = useCallback(() => {
        setCurrentPage(1); // Reset to first page when filters change
        fetchScrapingResults(1, selectedOutlet, dateFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedOutlet, dateFilter]);
    
    // Handle page change
    const handlePageChange = useCallback((_event: React.ChangeEvent<unknown>, page: number) => {
        setCurrentPage(page);
        fetchScrapingResults(page, selectedOutlet, dateFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedOutlet, dateFilter]);
    
    // Refresh results
    const handleRefresh = useCallback(() => {
        fetchScrapingResults(currentPage, selectedOutlet, dateFilter);
        setRefreshTrigger(prev => prev + 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentPage, selectedOutlet, dateFilter]);
    
    // Toggle filters visibility
    const toggleFilters = () => {
        setShowFilters(prev => !prev);
    };

    // Handle commands entered in the console
    const handleConsoleCommand = (command: string) => {
        // Check for special completion command
        if (command.startsWith('__COMPLETIONS__:')) {
            const completions = command.replace('__COMPLETIONS__:', '');
            addLog('Available completions:', 'info');
            addLog(completions, 'info');
            return;
        }
        
        // Add the command to logs with special formatting
        addLog(`$ ${command}`, 'info');
        
        // Parse the command
        const parts = command.trim().split(/\s+/);
        const mainCommand = parts[0].toLowerCase();
        const args = parts.slice(1);
        
        // Process command
        switch (mainCommand) {
            case 'help':
                addLog('Available commands:', 'info');
                addLog('  scrape                - Start a scraping operation', 'info');
                addLog('  status                - Show system status', 'info');
                addLog('  clear                 - Clear the console', 'info');
                addLog('  connect               - Reconnect to WebSocket', 'info');
                addLog('  about                 - Show about information', 'info');
                addLog('  rabbit [status|info]  - RabbitMQ information', 'info');
                break;
                
            case 'scrape':
                handleScrape();
                break;
                
            case 'status':
                addLog(`WebSocket Connection: ${isConnected ? 'Connected' : 'Disconnected'}`, 'info');
                addLog(`Scraping Status: ${operationPanels[0].status}`, 'info');
                addLog(`Active Panels: ${operationPanels.filter(p => p.status === 'Active').length}/${operationPanels.length}`, 'info');
                break;
                
            case 'clear':
                setLogs([]);
                addLog('Console cleared', 'success');
                break;
                
            case 'connect':
                connectToWebSocket();
                break;
                
            case 'about':
                addLog('Messor - InkBytes News Harvester', 'info');
                addLog('Version: 1.0.0', 'info');
                addLog('Author: Julian de la Rosa', 'info');
                addLog('Copyright: InkBytes Technologies', 'info');
                break;
                
            case 'rabbit':
                if (args.length > 0) {
                    const subcommand = args[0].toLowerCase();
                    if (subcommand === 'status') {
                        addLog('RabbitMQ Status:', 'info');
                        addLog('  Connection: Active', 'info');
                        addLog('  Channels: 2 (1 publisher, 1 consumer)', 'info');
                        addLog('  Queues: messor.articles (8), messor.logs (3), messor.commands (0)', 'info');
                    } else if (subcommand === 'info') {
                        addLog('RabbitMQ Server Information:', 'info');
                        addLog('  Host: rabbitmq-server:5672', 'info');
                        addLog('  Version: 3.9.13', 'info');
                        addLog('  Erlang: 24.3.4', 'info');
                        addLog('  Management: Available at :15672', 'info');
                    } else {
                        addLog(`Unknown subcommand: ${subcommand}`, 'error');
                    }
                } else {
                    addLog('RabbitMQ Commands:', 'info');
                    addLog('  rabbit status    - Show connection status', 'info');
                    addLog('  rabbit info      - Show server information', 'info');
                }
                break;
                
            default:
                addLog(`Unknown command: ${mainCommand}. Type 'help' for available commands.`, 'error');
        }
    };

    // Handle operation panel control click
    const handleControlClick = (panelId: number, control: string) => {
        switch (panelId) {
            case 1: // News Scraping panel
                if (control === 'Start Scraping') {
                    handleScrape();
                } else if (control === 'Stop') {
                    addLog('Stopping scraping operation...', 'info');
                    // Add logic to stop scraping
                    updatePanelStatus(1, 'Standby');
                } else if (control === 'Configure Sources') {
                    addLog('Opening source configuration...', 'info');
                    // Add logic to configure sources
                }
                break;
            // Add cases for other panels as needed
            default:
                addLog(`Clicked ${control} on panel ${panelId}`, 'info');
        }
    };

    // Status badge component with color coding
    const StatusBadge = ({ status }: { status: OperationPanel['status'] }) => {
        const getStatusColor = (status: string) => {
            switch (status.toLowerCase()) {
                case 'active':
                    return '#4caf50'; // Green
                case 'standby':
                    return '#ff9800'; // Orange
                case 'inactive':
                    return '#9e9e9e'; // Gray
                case 'running':
                    return '#2196f3'; // Blue
                default:
                    return '#2196f3'; // Blue
            }
        };

        return (
            <Box
                sx={{
                    display: 'inline-block',
                    backgroundColor: getStatusColor(status),
                    color: 'white',
                    borderRadius: '12px',
                    padding: '4px 12px',
                    fontSize: '0.75rem',
                    fontWeight: 'bold'
                }}
            >
                {status}
            </Box>
        );
    };

    return (
        <>
            <Header />
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Typography variant="h4" gutterBottom>
                    News Harvest/Scraper Dashboard
                </Typography>

                {/* Connection Status */}
                <Box sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                    <Typography variant="body1" sx={{ mr: 1 }}>
                        Connection Status:
                    </Typography>
                    <Box
                        component="span"
                        sx={{
                            display: 'inline-block',
                            width: 12,
                            height: 12,
                            borderRadius: '50%',
                            bgcolor: isConnected ? 'success.main' : 'error.main',
                            mr: 1
                        }} />
                    <Typography variant="body1">
                        {isConnected ? 'Connected' : 'Disconnected'}
                    </Typography>
                </Box>

                {/* Operation Panels Grid */}
                <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                    Operation Panels
                </Typography>
                <Grid container spacing={3} sx={{ mb: 4 }}>
                    {operationPanels.map((panel) => (
                        <Grid item xs={12} sm={6} md={3} key={panel.id}>
                            <Card 
                                sx={{ 
                                    height: '100%', 
                                    display: 'flex', 
                                    flexDirection: 'column',
                                    transition: 'transform 0.2s, box-shadow 0.2s',
                                    '&:hover': {
                                        transform: 'translateY(-4px)',
                                        boxShadow: 4
                                    }
                                }}
                            >
                                <CardHeader
                                    title={panel.title}
                                    action={<StatusBadge status={panel.status} />}
                                    sx={{ 
                                        borderBottom: '1px solid rgba(0, 0, 0, 0.12)',
                                        backgroundColor: 'rgba(0, 0, 0, 0.03)',
                                        p: 2
                                    }}
                                    titleTypographyProps={{ variant: 'subtitle1' }}
                                />
                                <CardContent sx={{ flexGrow: 1, p: 2 }}>
                                    <Typography variant="body2" color="text.secondary" paragraph>
                                        {panel.description}
                                    </Typography>
                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                                        {panel.controls.map((control, index) => (
                                            <Button 
                                                key={index} 
                                                variant="outlined" 
                                                fullWidth
                                                size="small"
                                                onClick={() => handleControlClick(panel.id, control)}
                                                disabled={(panel.status === 'Inactive' && control !== 'Configure Sources') || 
                                                         (panel.id === 1 && control === 'Start Scraping' && !isConnected) ||
                                                         (panel.id === 1 && control === 'Start Scraping' && isLoading)}
                                            >
                                                {panel.id === 1 && control === 'Start Scraping' && isLoading ? (
                                                    <>
                                                        <CircularProgress size={14} color="inherit" sx={{ mr: 1 }} />
                                                        Running...
                                                    </>
                                                ) : (
                                                    control
                                                )}
                                            </Button>
                                        ))}
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>
                    ))}
                </Grid>

                {/* Error Display */}
                {error && (
                    <Card sx={{ mb: 3, bgcolor: 'error.light', border: 1, borderColor: 'error.main' }}>
                        <CardContent>
                            <Typography color="error.dark">
                                {error}
                            </Typography>
                        </CardContent>
                    </Card>
                )}

                {/* CLI Console Log */}
                <Box sx={{ mb: 3 }}>
                    <ConsoleLog 
                        logs={logs} 
                        title="Operation Console" 
                        maxHeight={350}
                        autoScroll={true}
                        onCommand={handleConsoleCommand}
                    />
                </Box>

                {/* Scraping Results Section */}
                <Typography variant="h6" gutterBottom sx={{ mt: 4, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box display="flex" alignItems="center">
                        Latest Scraping Results
                        <IconButton 
                            size="small" 
                            onClick={handleRefresh} 
                            title="Refresh results"
                            sx={{ ml: 1 }}
                        >
                            <RefreshIcon fontSize="small" />
                        </IconButton>
                    </Box>
                    <Box>
                        <IconButton 
                            size="small" 
                            onClick={toggleFilters} 
                            title={showFilters ? "Hide filters" : "Show filters"}
                        >
                            <FilterListIcon fontSize="small" />
                            {showFilters ? <KeyboardArrowUpIcon fontSize="small" /> : <KeyboardArrowDownIcon fontSize="small" />}
                        </IconButton>
                    </Box>
                </Typography>
                
                {/* Filters */}
                {showFilters && (
                    <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
                        <Typography variant="subtitle2" gutterBottom>
                            Filter Results
                        </Typography>
                        <Grid container spacing={2} alignItems="center">
                            <Grid item xs={12} sm={4}>
                                <FormControl fullWidth size="small">
                                    <InputLabel id="outlet-filter-label">Outlet</InputLabel>
                                    <Select
                                        labelId="outlet-filter-label"
                                        value={selectedOutlet}
                                        label="Outlet"
                                        onChange={(e) => setSelectedOutlet(e.target.value)}
                                    >
                                        {outletOptions.map((outlet) => (
                                            <MenuItem key={outlet} value={outlet}>
                                                {outlet}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <FormControl fullWidth size="small">
                                    <InputLabel id="date-filter-label">Date Range</InputLabel>
                                    <Select
                                        labelId="date-filter-label"
                                        value={dateFilter}
                                        label="Date Range"
                                        onChange={(e) => setDateFilter(e.target.value)}
                                    >
                                        {dateOptions.map((option) => (
                                            <MenuItem key={option.value} value={option.value}>
                                                {option.label}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <Button 
                                    variant="contained" 
                                    onClick={handleFiltersChange}
                                    disabled={isLoading}
                                    fullWidth
                                >
                                    {isLoading ? <CircularProgress size={24} /> : "Apply Filters"}
                                </Button>
                            </Grid>
                        </Grid>
                    </Paper>
                )}
                
                {/* Scraping Results Component with filter parameters */}
                <Box sx={{ mb: 3 }}>
                    <ScrapingResults 
                        key={refreshTrigger}
                        filterOutlet={selectedOutlet}
                        dateFilter={dateFilter}
                        page={currentPage}
                        limit={10}
                        autoRefresh={false} // We'll handle refreshes via the Dashboard
                    />
                </Box>
                
                {/* Pagination */}
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
                    <Pagination 
                        count={totalPages} 
                        page={currentPage}
                        onChange={handlePageChange}
                        color="primary"
                        disabled={isLoading}
                    />
                </Box>

                {/* RabbitMQ Listener - disabled to reduce console noise */}
                {/* <RabbitMQListener onMessage={handleRabbitMessage} /> */}
            </Container>
        </>
    );
}

export default Dashboard;
