# Code Documentation Standards

This guide defines the documentation standards for all code within the Messor project.

## 📋 Documentation Requirements

### **1. All Public Functions Must Have:**
- Google-style docstrings
- Type hints for parameters and return values
- Usage examples where appropriate
- Error conditions and exceptions

### **2. All Classes Must Have:**
- Class-level docstring explaining purpose
- Attribute documentation
- Method documentation
- Usage examples

### **3. Complex Logic Must Have:**
- Inline comments explaining the "why"
- Step-by-step comments for algorithms
- Reference links to external documentation

## 🐍 Python Documentation Standards

### **Docstring Format (Google Style)**

#### **Function Documentation**
```python
def scrape_outlet(self, outlet: OutletsSource, limit: Optional[int] = None) -> List[Article]:
    """Scrape articles from a specific news outlet.
    
    This method handles the complete scraping workflow for a single outlet,
    including connection management, content extraction, and error handling.
    
    Args:
        outlet: The news outlet configuration containing name and URL
        limit: Maximum number of articles to extract. None means no limit
        
    Returns:
        List of successfully scraped Article objects. Empty list if scraping fails.
        
    Raises:
        ConnectionError: When outlet is unreachable or connection times out
        ValidationError: When outlet configuration is invalid or malformed
        ScrapingError: When content extraction fails due to site structure changes
        
    Example:
        >>> outlet = OutletsSource(name="bbc", url="https://bbc.com")
        >>> articles = scraper.scrape_outlet(outlet, limit=10)
        >>> print(f"Scraped {len(articles)} articles from {outlet.name}")
        Scraped 8 articles from bbc
        
    Note:
        This method implements retry logic with exponential backoff for
        handling temporary network issues.
    """
    # Implementation here
```

#### **Class Documentation**
```python
class ScraperService:
    """Web scraping service for news outlet content extraction.
    
    This service orchestrates the complete news scraping workflow, managing
    multiple outlets concurrently while respecting rate limits and handling
    failures gracefully.
    
    The service implements a producer-consumer pattern where outlet scraping
    tasks are distributed across worker threads, with results aggregated
    and processed through a centralized pipeline.
    
    Attributes:
        config: Application configuration containing scraping parameters
        logger: Structured logger for operation tracking and debugging
        outlet_service: Service for managing news outlet configurations
        storage_service: Service for persisting scraped articles
        message_service: Service for publishing scraping events
        
    Example:
        >>> scraper = ScraperService(config, logger, outlet_service, 
        ...                         storage_service, message_service)
        >>> sessions = scraper.execute_scraping_process(limit=10)
        >>> print(f"Completed scraping with {len(sessions)} successful sessions")
        
    Thread Safety:
        This class is thread-safe and can be safely used in multi-threaded
        environments. Internal state is protected by locks where necessary.
    """
    
    def __init__(self, 
                 config: Config, 
                 logger: logging.Logger,
                 outlet_service: OutletService,
                 storage_service: StorageService,
                 message_service: MessageService) -> None:
        """Initialize scraper service with required dependencies.
        
        Args:
            config: Application configuration object
            logger: Logger instance for this service
            outlet_service: Service for outlet management
            storage_service: Service for data persistence
            message_service: Service for event messaging
        """
        self.config = config
        self.logger = logger
        self.outlet_service = outlet_service
        self.storage_service = storage_service
        self.message_service = message_service
        
        # Initialize thread pool for concurrent scraping
        max_workers = min(config.application.max_threads, 20)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Track active scraping sessions
        self._active_sessions: Dict[str, ScrapingSession] = {}
        self._session_lock = threading.Lock()
```

### **Type Hints Standards**

#### **Basic Type Hints**
```python
from typing import List, Dict, Optional, Union, Any, Callable
from pathlib import Path
import logging

def process_articles(articles: List[Article], 
                    filters: Optional[Dict[str, Any]] = None,
                    callback: Optional[Callable[[Article], None]] = None) -> Dict[str, int]:
    """Process a list of articles with optional filtering and callbacks."""
    pass

def load_configuration(config_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from file path."""
    pass
```

#### **Custom Type Definitions**
```python
from typing import TypeVar, Generic, Protocol
from dataclasses import dataclass
from enum import Enum

# Type variables for generic classes
T = TypeVar('T')
ResultType = TypeVar('ResultType')

# Enums for constants
class ScrapingStatus(Enum):
    """Status enumeration for scraping operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"

# Data classes for structured data
@dataclass
class ScrapingResult:
    """Result container for scraping operations.
    
    Attributes:
        session_id: Unique identifier for the scraping session
        outlet_name: Name of the scraped news outlet
        articles_found: Number of articles successfully extracted
        duration_seconds: Time taken for the scraping operation
        status: Final status of the scraping operation
        error_message: Error description if scraping failed
    """
    session_id: str
    outlet_name: str
    articles_found: int
    duration_seconds: float
    status: ScrapingStatus
    error_message: Optional[str] = None

# Protocol for dependency injection
class StorageProtocol(Protocol):
    """Protocol defining storage service interface."""
    
    def save_articles(self, articles: List[Article]) -> bool:
        """Save articles to storage."""
        ...
    
    def get_articles(self, filters: Dict[str, Any]) -> List[Article]:
        """Retrieve articles from storage."""
        ...
```

### **Inline Comments Standards**

#### **Algorithm Explanation**
```python
def extract_article_content(self, html: str, url: str) -> Optional[Article]:
    """Extract article content from HTML using multiple strategies."""
    
    # Parse HTML with error recovery for malformed content
    soup = BeautifulSoup(html, 'html.parser', from_encoding='utf-8')
    
    # Strategy 1: Look for JSON-LD structured data (most reliable)
    json_ld = soup.find('script', type='application/ld+json')
    if json_ld:
        try:
            structured_data = json.loads(json_ld.string)
            if self._is_article_data(structured_data):
                return self._extract_from_json_ld(structured_data, url)
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.debug(f"JSON-LD parsing failed for {url}: {e}")
    
    # Strategy 2: Look for Open Graph meta tags (good fallback)
    og_title = soup.find('meta', property='og:title')
    og_description = soup.find('meta', property='og:description')
    if og_title and og_description:
        article = self._extract_from_open_graph(soup, url)
        if self._validate_article_quality(article):
            return article
    
    # Strategy 3: Heuristic-based content extraction (last resort)
    # This uses common HTML patterns to identify article content
    return self._extract_using_heuristics(soup, url)

def _extract_using_heuristics(self, soup: BeautifulSoup, url: str) -> Optional[Article]:
    """Extract content using heuristic patterns for article identification."""
    
    # Common selectors for article content, ordered by reliability
    content_selectors = [
        'article',                    # HTML5 semantic article tag
        '[role="main"]',             # ARIA main content role
        '.article-content',          # Common class name
        '.post-content',             # Blog post content
        '#content',                  # Generic content ID
    ]
    
    for selector in content_selectors:
        content_element = soup.select_one(selector)
        if content_element:
            # Extract text and clean up whitespace
            text = content_element.get_text(strip=True, separator=' ')
            
            # Apply quality filters
            word_count = len(text.split())
            if word_count >= self.config.scraper.min_word_count:
                return Article(
                    url=url,
                    title=self._extract_title(soup),
                    content=text,
                    word_count=word_count,
                    extracted_at=datetime.utcnow()
                )
    
    return None  # No suitable content found
```

#### **Complex Business Logic**
```python
def calculate_scraping_priority(self, outlets: List[OutletsSource]) -> List[OutletsSource]:
    """Calculate and sort outlets by scraping priority.
    
    Priority is determined by multiple factors to optimize scraping efficiency
    and ensure high-quality content sources are processed first.
    """
    
    def priority_score(outlet: OutletsSource) -> float:
        """Calculate numeric priority score for an outlet."""
        score = 0.0
        
        # Factor 1: Historical success rate (40% weight)
        # Outlets with higher success rates get priority
        success_rate = self.analytics_service.get_success_rate(outlet.name)
        score += success_rate * 0.4
        
        # Factor 2: Average response time (30% weight) 
        # Faster outlets get higher priority to reduce overall scraping time
        avg_response_time = self.analytics_service.get_avg_response_time(outlet.name)
        if avg_response_time > 0:
            # Invert response time so faster sites score higher
            time_score = max(0, 1.0 - (avg_response_time / 10.0))  # 10s max
            score += time_score * 0.3
        
        # Factor 3: Content quality (20% weight)
        # Outlets producing higher quality articles get priority
        quality_score = self.analytics_service.get_content_quality(outlet.name)
        score += quality_score * 0.2
        
        # Factor 4: Recency bonus (10% weight)
        # Recently updated outlets get slight priority boost
        last_update = self.analytics_service.get_last_update(outlet.name)
        hours_since_update = (datetime.utcnow() - last_update).total_seconds() / 3600
        recency_score = max(0, 1.0 - (hours_since_update / 24.0))  # 24h decay
        score += recency_score * 0.1
        
        return score
    
    # Sort outlets by calculated priority (highest first)
    return sorted(outlets, key=priority_score, reverse=True)
```

## 📱 JavaScript/TypeScript Standards

### **JSDoc Documentation**
```typescript
/**
 * Service for managing real-time scraping updates via WebSocket.
 * 
 * This service establishes and maintains a WebSocket connection to receive
 * live updates about scraping progress, article discovery, and system status.
 * 
 * @example
 * ```typescript
 * const wsService = new WebSocketService('ws://localhost:8050/ws/scraping');
 * 
 * wsService.onStatusUpdate((status) => {
 *   console.log(`Progress: ${status.articles_found} articles`);
 * });
 * 
 * wsService.connect();
 * ```
 */
export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;
  private statusUpdateHandlers: Array<(status: ScrapingStatus) => void> = [];

  /**
   * Initialize WebSocket service with server URL.
   * 
   * @param url - WebSocket server URL (ws:// or wss://)
   * @param options - Optional configuration for connection behavior
   */
  constructor(
    private readonly url: string,
    private readonly options: WebSocketOptions = {}
  ) {
    this.options = {
      reconnectDelay: 1000,
      heartbeatInterval: 30000,
      ...options
    };
  }

  /**
   * Establish WebSocket connection with automatic retry logic.
   * 
   * @returns Promise that resolves when connection is established
   * @throws {ConnectionError} When max reconnection attempts exceeded
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(JSON.parse(event.data));
        };

        this.ws.onclose = () => {
          this.handleDisconnection();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            reject(new ConnectionError('Max reconnection attempts exceeded'));
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Handle incoming WebSocket messages and route to appropriate handlers.
   * 
   * @private
   * @param message - Parsed message object from server
   */
  private handleMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'status_update':
        // Notify all registered status update handlers
        this.statusUpdateHandlers.forEach(handler => {
          try {
            handler(message.data as ScrapingStatus);
          } catch (error) {
            console.error('Error in status update handler:', error);
          }
        });
        break;

      case 'article_found':
        this.handleArticleFound(message.data as ArticleFoundEvent);
        break;

      case 'error':
        this.handleError(message.data as ErrorEvent);
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }
}
```

### **React Component Documentation**
```typescript
interface DashboardProps {
  /** Current scraping status from the backend */
  scrapingStatus: ScrapingStatus | null;
  /** Callback fired when user initiates scraping */
  onStartScraping: (options: ScrapingOptions) => void;
  /** Callback fired when user stops scraping */
  onStopScraping: () => void;
  /** Optional CSS class name for styling */
  className?: string;
}

/**
 * Main dashboard component for monitoring and controlling news scraping operations.
 * 
 * This component provides a real-time view of scraping progress, system health,
 * and analytics. It connects to the WebSocket service for live updates and
 * provides controls for starting/stopping scraping operations.
 * 
 * @component
 * @example
 * ```tsx
 * <Dashboard
 *   scrapingStatus={status}
 *   onStartScraping={(options) => scrapingService.start(options)}
 *   onStopScraping={() => scrapingService.stop()}
 * />
 * ```
 */
const Dashboard: React.FC<DashboardProps> = ({
  scrapingStatus,
  onStartScraping,
  onStopScraping,
  className
}) => {
  // State for managing UI-specific data
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Effect to handle scraping status changes and update UI accordingly.
   * This effect is responsible for:
   * - Updating loading states
   * - Clearing errors when scraping starts
   * - Updating article counts from status updates
   */
  useEffect(() => {
    if (!scrapingStatus) return;

    switch (scrapingStatus.status) {
      case 'in_progress':
        setIsLoading(true);
        setError(null);
        break;
      
      case 'completed':
        setIsLoading(false);
        // Update article count from completed status
        if (scrapingStatus.articles_found) {
          setArticles(prev => [
            ...prev.slice(-100), // Keep last 100 articles
            ...scrapingStatus.articles_found
          ]);
        }
        break;
      
      case 'failed':
        setIsLoading(false);
        setError(scrapingStatus.error_message || 'Scraping failed');
        break;
    }
  }, [scrapingStatus]);

  // Component render logic with detailed JSX
  return (
    <div className={`dashboard ${className || ''}`}>
      {/* Dashboard content */}
    </div>
  );
};
```

## 🔧 Configuration Documentation

### **YAML Configuration Comments**
```yaml
# Messor News Harvester Configuration
# This file defines all application settings and service configurations

application:
  # Application metadata and basic settings
  name: Messor                    # Application display name
  version: 1.0                    # Semantic version number
  mode: development               # Environment: development | production | test
  
  # Threading and performance settings
  max_threads: 10                 # Maximum concurrent scraping threads
                                 # Recommended: 2x CPU cores, max 20
  
  # Unique identifier settings
  uuid_prefix: IKPGRB            # Prefix for generated session IDs
  time_zone: America/New_York    # Timezone for timestamps and scheduling

scraping:
  # Content quality filters
  min_word_count: 40             # Minimum words required for article acceptance
                                # Lower values = more articles but potentially lower quality
  
  # Scheduling configuration (Docker mode)
  schedule_interval_minutes: 60   # Minutes between automated scraping cycles
                                # Recommended: 30-180 minutes depending on source update frequency
  
  # Rate limiting and politeness
  request_delay_seconds: 1       # Delay between requests to same domain
  max_retries: 3                # Maximum retry attempts for failed requests
  timeout_seconds: 30           # Request timeout in seconds

logging:
  # Log level configuration
  level: INFO                    # DEBUG | INFO | WARNING | ERROR | CRITICAL
  
  # Log destinations
  destinations:
    - console                    # Log to stdout/stderr
    - file                      # Log to file system
    - rabbit                    # Log to RabbitMQ for centralized collection
  
  # File logging settings
  log_file: logs/messor.log      # Log file path (auto-rotated)
  max_file_size: 100MB          # Maximum size before rotation
  backup_count: 5               # Number of backup files to keep

# External service configurations
rabbitmq:
  host: kloudsix.io             # RabbitMQ server hostname
  port: 5672                    # Standard AMQP port
  virtual_host: /               # Virtual host for isolation
  username: guest               # Authentication username
  password: guest               # Authentication password (use environment variables in production)
  
  # Connection reliability settings
  heartbeat: 600                # Heartbeat interval in seconds
  connection_attempts: 3        # Maximum connection retry attempts
  retry_delay: 5                # Seconds between connection retries
```

## 📊 Documentation Generation Tools

### **Sphinx Configuration** (`docs/conf.py`)
```python
"""
Sphinx configuration for generating API documentation from docstrings.
"""

# Project information
project = 'Messor'
copyright = '2025, InkBytes Technologies'
author = 'Julian de la Rosa'
version = '1.0.0'
release = '1.0.0'

# Extensions for enhanced documentation
extensions = [
    'sphinx.ext.autodoc',        # Auto-generate docs from docstrings
    'sphinx.ext.viewcode',       # Include source code links
    'sphinx.ext.napoleon',       # Google/NumPy style docstring support
    'sphinx.ext.intersphinx',    # Cross-reference other projects
    'sphinx.ext.todo',           # TODO directive support
    'myst_parser',               # Markdown support
]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# Auto-documentation settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# HTML theme configuration
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
}
```

### **Type Checking Configuration**
```toml
# pyproject.toml - Type checking and code quality configuration

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true

# Strict optional checking
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true

# Error formatting
show_error_codes = true
show_column_numbers = true

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # Directories to exclude
  \.eggs
  | \.git
  | \.mypy_cache
  | build
  | dist
  | venv
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
```

## ✅ Documentation Checklist

### **Before Committing Code:**
- [ ] All public functions have docstrings
- [ ] Type hints are present and accurate
- [ ] Complex logic has explanatory comments
- [ ] Examples are provided for non-trivial functions
- [ ] Error conditions are documented
- [ ] Configuration options are explained

### **Code Review Checklist:**
- [ ] Docstrings follow Google style format
- [ ] Type hints match actual implementation
- [ ] Comments explain "why" not "what"
- [ ] Examples are runnable and accurate
- [ ] Error handling is documented
- [ ] Dependencies are clearly stated

This comprehensive code documentation standard ensures that your codebase is self-documenting, maintainable, and accessible to new developers.