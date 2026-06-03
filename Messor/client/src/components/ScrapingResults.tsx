// src/components/ScrapingResults.tsx
import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Typography, 
  List, 
  ListItem, 
  ListItemText, 
  Accordion, 
  AccordionSummary, 
  AccordionDetails,
  CircularProgress,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  Grid,
  Paper,
  Tabs,
  Tab,
  useTheme,
  LinearProgress
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AssessmentIcon from '@mui/icons-material/Assessment';
import TableChartIcon from '@mui/icons-material/TableChart';
import TerminalIcon from '@mui/icons-material/Terminal';
import VisibilityIcon from '@mui/icons-material/Visibility';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import { useServices } from '../context/ServiceContext';
import { ScrapingSession as ScrapingSessionType } from '../types';
import { FetchScrapingResultsOptions } from '../services/ApiService';

interface PieDataItem {
  name: string;
  value: number | string;
  fill?: string;
}

interface BarDataItem {
  name: string;
  successful: number;
  failed: number;
  total: number;
  successRate: number | string;
}

interface FallbackChartProps<TData> {
  data?: TData[];
}

// Fallback chart components when recharts isn't available
const FallbackPieChart: React.FC<FallbackChartProps<PieDataItem>> = (props) => {
  const { data } = props;
  
  return (
    <Box sx={{ 
      height: 300, 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      gap: 2
    }}>
      <Typography variant="body1" color="text.secondary">
        Pie Chart Visualization
      </Typography>
      
      {data && data.map((item, index: number) => (
        <Box key={index} sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          width: '100%', 
          maxWidth: 300
        }}>
          <Box sx={{ 
            width: 16, 
            height: 16, 
            bgcolor: item.fill || '#2196f3', 
            mr: 1,
            borderRadius: '50%'
          }} />
          <Typography variant="body2" sx={{ flex: 1 }}>
            {item.name}
          </Typography>
          <Typography variant="body2" fontWeight="bold">
            {typeof item.value === 'number' ? Math.round(item.value) : item.value}
          </Typography>
        </Box>
      ))}
    </Box>
  );
};

const FallbackBarChart: React.FC<FallbackChartProps<BarDataItem>> = (props) => {
  const { data } = props;
  
  return (
    <Box sx={{ 
      height: 300, 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      gap: 2
    }}>
      <Typography variant="body1" color="text.secondary">
        Bar Chart Visualization
      </Typography>
      
      {data && data.map((item, index: number) => (
        <Box key={index} sx={{ 
          width: '100%',
          mb: 1
        }}>
          <Typography variant="body2" gutterBottom>
            {item.name}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box sx={{ flex: 1 }}>
              <Box sx={{ 
                height: 20, 
                display: 'flex', 
                borderRadius: 1, 
                overflow: 'hidden'
              }}>
                <Box sx={{ 
                  width: `${(item.successful / item.total) * 100}%`, 
                  bgcolor: 'success.main'
                }} />
                <Box sx={{ 
                  width: `${(item.failed / item.total) * 100}%`, 
                  bgcolor: 'error.main'
                }} />
              </Box>
            </Box>
            <Typography variant="caption" sx={{ minWidth: 100 }}>
              {item.successful} / {item.total} ({item.successRate}%)
            </Typography>
          </Box>
        </Box>
      ))}
    </Box>
  );
};

// Tab Panel interface
interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

// Tab Panel component
function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`scraping-tabpanel-${index}`}
      aria-labelledby={`scraping-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

// Accessibility properties for tabs
function a11yProps(index: number) {
  return {
    id: `scraping-tab-${index}`,
    'aria-controls': `scraping-tabpanel-${index}`,
  };
}

interface ScrapingResultsProps {
  filterOutlet?: string;
  dateFilter?: string;
  page?: number;
  limit?: number;
  autoRefresh?: boolean;
}

const ScrapingResults: React.FC<ScrapingResultsProps> = ({
  filterOutlet = "All Outlets",
  dateFilter = "today",
  page = 1,
  limit = 10,
  autoRefresh = true
}) => {
  const { apiService } = useServices();
  const [session, setSession] = useState<ScrapingSessionType | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const theme = useTheme();

  const getErrorMessage = (error: unknown): string => {
    if (error instanceof Error && error.message) {
      return error.message;
    }

    return 'Failed to load scraping results';
  };

  // Function to build query options based on props
  const buildQueryOptions = (): FetchScrapingResultsOptions => {
    const options: FetchScrapingResultsOptions = {
      limit,
      page
    };
    
    // Handle outlet filter
    if (filterOutlet !== "All Outlets") {
      options.filterOutlet = filterOutlet;
    }
    
    // Handle date filter
    if (dateFilter === 'today') {
      options.filterToday = true;
    } else if (dateFilter === 'yesterday') {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      options.startDate = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate()).toISOString();
      options.endDate = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 23, 59, 59).toISOString();
    } else if (dateFilter === 'last7days') {
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      options.startDate = sevenDaysAgo.toISOString();
    } else if (dateFilter === 'last30days') {
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      options.startDate = thirtyDaysAgo.toISOString();
    }
    
    return options;
  };

  useEffect(() => {
    const fetchResults = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Build query options based on props
        const queryOptions = buildQueryOptions();
        console.log('Fetching with options:', queryOptions);
        
        // Fetch results with the constructed options
        const results = await apiService.fetchScrapingResults(queryOptions);
        setSession(results);
      } catch (error: unknown) {
        console.error('Error fetching results:', error);
        setError(getErrorMessage(error));
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    fetchResults();
    
    // Set up a timer to refresh data if autoRefresh is enabled
    let intervalId: number | undefined;
    if (autoRefresh) {
      intervalId = window.setInterval(() => {
        // Only update if we've already loaded a session
        if (session && session.id) {
          const queryOptions = buildQueryOptions();
          apiService.fetchScrapingResults(queryOptions)
            .then(updatedResults => {
              setSession(updatedResults);
            })
            .catch(error => {
              console.warn('Error refreshing data:', error);
            });
        }
      }, 60000); // Refresh every minute
    }
    
    // Clean up interval on unmount
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiService, filterOutlet, dateFilter, page, limit, autoRefresh]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert 
          severity="error" 
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => setLoading(true)}>
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
        <Alert severity="info">
          If the server is not running or there's a CORS issue, you'll see sample data in development mode.
        </Alert>
      </Container>
    );
  }

  if (!session) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert 
          severity="info"
          action={
            <Button color="inherit" size="small" onClick={() => setLoading(true)}>
              Retry
            </Button>
          }
        >
          No scraping session data available. Try running a scrape operation first.
        </Alert>
      </Container>
    );
  }

  // Pie chart data for successful vs failed articles
  const pieData = [
    { name: 'Successful', value: session.total_articles_scraped * session.overall_success_rate, fill: theme.palette.success.main },
    { name: 'Failed', value: session.total_articles_scraped * (1 - session.overall_success_rate), fill: theme.palette.error.main }
  ];

  // Bar chart data for outlets
  const barData = session.results.map(result => ({
    name: result.outlet.name.length > 15 ? result.outlet.name.substring(0, 12) + '...' : result.outlet.name,
    successful: result.successful_scrapes,
    failed: result.total_articles - result.successful_scrapes,
    total: result.total_articles,
    successRate: (result.successful_scrapes / result.total_articles * 100).toFixed(1)
  }));

  // Format session duration in a human-readable format
  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
  };

  // JSON representation for the raw data tab
  const sessionData = {
    data: {
      start_time: session.start_time,
      end_time: session.end_time,
      total_articles: session.total_articles_scraped,
      results_staging_file_name: `${Date.now()}.${session.results[0]?.outlet.name || 'Unknown'}.db.json`,
      failed_articles: session.total_articles_scraped * (1 - session.overall_success_rate),
      successful_articles: session.total_articles_scraped * session.overall_success_rate,
      duration: session.duration,
      success_rate: session.overall_success_rate,
      outlet: session.results[0]?.outlet.name || 'Unknown',
      completed_session: true
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Paper sx={{ borderRadius: 2, overflow: 'hidden', boxShadow: 3 }}>
        {/* Header with session info */}
        <Box sx={{ 
          p: 3, 
          bgcolor: 'primary.main', 
          color: 'primary.contrastText',
          borderTopLeftRadius: 8,
          borderTopRightRadius: 8
        }}>
          <Typography variant="h4" sx={{ mb: 1 }}>
            Scraping Results
          </Typography>
          <Typography variant="h6" sx={{ opacity: 0.9 }}>
            Session ID: {session.id}
          </Typography>
        </Box>

        {/* Stats Cards */}
        <Box sx={{ p: 3, bgcolor: 'background.paper' }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={3}>
              <Card variant="outlined" sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': { transform: 'translateY(-4px)', boxShadow: 2 }
              }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    TOTAL ARTICLES
                  </Typography>
                  <Typography variant="h3" component="div" sx={{ mb: 1, fontWeight: 'bold' }}>
                    {session.total_articles_scraped}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <TableChartIcon color="primary" fontSize="small" sx={{ mr: 1 }} />
                    <Typography variant="body2">
                      From {session.total_outlets_scraped} outlets
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Card variant="outlined" sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': { transform: 'translateY(-4px)', boxShadow: 2 }
              }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    SUCCESS RATE
                  </Typography>
                  <Typography variant="h3" component="div" sx={{ mb: 1, fontWeight: 'bold' }}>
                    {(session.overall_success_rate * 100).toFixed(1)}%
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <LinearProgress 
                      variant="determinate" 
                      value={session.overall_success_rate * 100} 
                      color={session.overall_success_rate > 0.7 ? "success" : session.overall_success_rate > 0.5 ? "warning" : "error"}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Card variant="outlined" sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': { transform: 'translateY(-4px)', boxShadow: 2 }
              }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    DURATION
                  </Typography>
                  <Typography variant="h3" component="div" sx={{ mb: 1, fontWeight: 'bold' }}>
                    {formatDuration(session.duration)}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <AccessTimeIcon color="primary" fontSize="small" sx={{ mr: 1 }} />
                    <Typography variant="body2">
                      {new Date(session.end_time).toLocaleTimeString()} completed
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Card variant="outlined" sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': { transform: 'translateY(-4px)', boxShadow: 2 },
                bgcolor: 'primary.light'
              }}>
                <CardContent>
                  <Typography variant="subtitle2" color="primary.contrastText" gutterBottom>
                    VIEWS
                  </Typography>
                  <Typography variant="h3" component="div" sx={{ mb: 1, fontWeight: 'bold', color: 'primary.contrastText' }}>
                    {session.views || 1}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <VisibilityIcon sx={{ mr: 1, color: 'primary.contrastText' }} fontSize="small" />
                    <Typography variant="body2" sx={{ color: 'primary.contrastText' }}>
                      {session.last_viewed ? `Last: ${new Date(session.last_viewed).toLocaleTimeString()}` : 'First view'}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>

        {/* Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange} 
            aria-label="scraping results tabs"
            variant="fullWidth"
          >
            <Tab 
              label="Dashboard" 
              {...a11yProps(0)} 
              icon={<AssessmentIcon />} 
              iconPosition="start" 
            />
            <Tab 
              label="Results by Outlet" 
              {...a11yProps(1)} 
              icon={<TableChartIcon />} 
              iconPosition="start"
            />
            <Tab 
              label="Raw Data" 
              {...a11yProps(2)} 
              icon={<TerminalIcon />}
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* Dashboard Tab */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            {/* Success Rate Pie Chart */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2, height: '100%' }}>
                <Typography variant="h6" gutterBottom>
                  Articles Success Rate
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <FallbackPieChart data={pieData} />
              </Paper>
            </Grid>

            {/* Outlets Bar Chart */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2, height: '100%' }}>
                <Typography variant="h6" gutterBottom>
                  Articles by Outlet
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <FallbackBarChart data={barData} />
              </Paper>
            </Grid>

            {/* Summary Statistics */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Scraping Summary
                </Typography>
                <Divider sx={{ mb: 2 }} />
                
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Start Time:
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {new Date(session.start_time).toLocaleString()}
                    </Typography>
                    
                    <Typography variant="subtitle2" color="text.secondary">
                      End Time:
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {new Date(session.end_time).toLocaleString()}
                    </Typography>
                    
                    <Typography variant="subtitle2" color="text.secondary">
                      Duration:
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {formatDuration(session.duration)} ({session.duration.toFixed(2)} seconds)
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Total Outlets:
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {session.total_outlets_scraped}
                    </Typography>
                    
                    <Typography variant="subtitle2" color="text.secondary">
                      Total Articles:
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {session.total_articles_scraped} 
                      {' '}({Math.round(session.total_articles_scraped * session.overall_success_rate)} successful, 
                      {' '}{Math.round(session.total_articles_scraped * (1 - session.overall_success_rate))} failed)
                    </Typography>
                    
                    <Typography variant="subtitle2" color="text.secondary">
                      Average Articles Per Outlet:
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {(session.total_articles_scraped / session.total_outlets_scraped).toFixed(1)}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Results by Outlet Tab */}
        <TabPanel value={tabValue} index={1}>
          {session.results.map((result, index) => (
            <Accordion key={index} sx={{ mb: 1 }}>
              <AccordionSummary 
                expandIcon={<ExpandMoreIcon />}
                sx={{ 
                  bgcolor: result.failed_scrapes > 0 ? 'warning.light' : 'success.light'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', pr: 2 }}>
                  <Typography sx={{ fontWeight: 'medium' }}>
                    {result.outlet.name}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Typography variant="body2" sx={{ mr: 2 }}>
                      {result.successful_scrapes} of {result.total_articles} articles
                    </Typography>
                    <Box sx={{ 
                      bgcolor: result.successful_scrapes / result.total_articles > 0.7 ? 'success.main' : 'warning.main',
                      color: 'white',
                      px: 1,
                      py: 0.5,
                      borderRadius: 1,
                      fontSize: '0.75rem',
                      fontWeight: 'bold'
                    }}>
                      {Math.round((result.successful_scrapes / result.total_articles) * 100)}%
                    </Box>
                  </Box>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2">Outlet Details:</Typography>
                    <Typography variant="body2">URL: {result.outlet.url}</Typography>
                    <Typography variant="body2">Type: {result.outlet.type}</Typography>
                    <Typography variant="body2">Total Articles: {result.total_articles}</Typography>
                    <Typography variant="body2">Successful Scrapes: {result.successful_scrapes}</Typography>
                    <Typography variant="body2">Failed Scrapes: {result.failed_scrapes}</Typography>
                    <Typography variant="body2">Duration: {formatDuration(result.duration)} ({result.duration.toFixed(2)} seconds)</Typography>
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    <FallbackPieChart data={[
                      { name: 'Successful', value: result.successful_scrapes, fill: theme.palette.success.main },
                      { name: 'Failed', value: result.failed_scrapes, fill: theme.palette.error.main }
                    ]} />
                  </Grid>
                </Grid>
                
                {result.errors.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" color="error">Errors:</Typography>
                    <List dense sx={{ bgcolor: 'error.light', borderRadius: 1, py: 0 }}>
                      {result.errors.map((error, errorIndex) => (
                        <ListItem key={errorIndex}>
                          <ListItemText 
                            primary={error} 
                            primaryTypographyProps={{ 
                              variant: 'body2', 
                              color: 'error.dark' 
                            }} 
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          ))}
        </TabPanel>

        {/* Raw Data Tab */}
        <TabPanel value={tabValue} index={2}>
          <Paper sx={{ 
            p: 2, 
            bgcolor: '#272822', 
            color: '#f8f8f2', 
            fontFamily: 'monospace',
            fontSize: '0.9rem',
            borderRadius: 1,
            position: 'relative',
            overflowX: 'auto'
          }}>
            <Box component="pre" sx={{ m: 0 }}>
              {`// ${new Date().toISOString()} Messor: [INFO] Unknown in Unknown (args: -) - Scraping session info:`}
              {JSON.stringify(sessionData, null, 2)}
              {`\nINFO:Inkbytes.Messor:Scraping session info:`}
              {JSON.stringify(sessionData, null, 2)}
            </Box>
          </Paper>
        </TabPanel>
      </Paper>
    </Container>
  );
};

export default ScrapingResults;
