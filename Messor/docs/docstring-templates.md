# Docstring Templates

This document provides standardized templates for documenting code in the Messor project.

## 📋 Template Categories

### **Function Templates**
- [Simple Function](#simple-function)
- [Complex Function](#complex-function)
- [Async Function](#async-function)
- [Generator Function](#generator-function)

### **Class Templates** 
- [Service Class](#service-class)
- [Data Class](#data-class)
- [Exception Class](#exception-class)

### **Module Templates**
- [Service Module](#service-module)
- [Utility Module](#utility-module)

---

## 🔧 Function Templates

### Simple Function
```python
def calculate_word_count(text: str) -> int:
    """Calculate the number of words in the given text.
    
    Args:
        text: The input text to count words from
        
    Returns:
        The number of words found in the text
        
    Example:
        >>> calculate_word_count("Hello world")
        2
    """
    return len(text.split())
```

### Complex Function
```python
def scrape_article_content(url: str, 
                          timeout: int = 30,
                          retry_attempts: int = 3,
                          custom_headers: Optional[Dict[str, str]] = None) -> Optional[Article]:
    """Extract article content from a news website URL.
    
    This function implements a robust article extraction strategy using multiple
    content detection methods. It handles various website structures and includes
    retry logic for handling temporary network issues.
    
    The extraction process follows this priority order:
    1. JSON-LD structured data (most reliable)
    2. Open Graph meta tags (good fallback)
    3. Heuristic content detection (last resort)
    
    Args:
        url: The URL of the article to scrape
        timeout: Request timeout in seconds. Default: 30
        retry_attempts: Number of retry attempts on failure. Default: 3
        custom_headers: Optional HTTP headers to include with request
        
    Returns:
        Article object with extracted content, or None if extraction failed
        
    Raises:
        ConnectionError: When URL is unreachable after all retry attempts
        ValidationError: When URL format is invalid
        ContentError: When article content cannot be extracted or validated
        
    Example:
        >>> article = scrape_article_content(
        ...     "https://bbc.com/news/article", 
        ...     timeout=60,
        ...     custom_headers={"User-Agent": "NewsBot/1.0"}
        ... )
        >>> if article:
        ...     print(f"Title: {article.title}")
        ...     print(f"Words: {article.word_count}")
        
    Note:
        This function respects robots.txt and implements polite crawling delays.
        Large articles (>10MB) are automatically truncated to prevent memory issues.
    """
    # Implementation here
    pass
```

### Async Function
```python
async def upload_to_cloud_storage(file_path: str, 
                                 bucket_name: str,
                                 progress_callback: Optional[Callable[[int], None]] = None) -> bool:
    """Asynchronously upload a file to cloud storage with progress tracking.
    
    Args:
        file_path: Local path to the file to upload
        bucket_name: Target cloud storage bucket name
        progress_callback: Optional callback function for upload progress updates.
            Called with bytes uploaded as argument
            
    Returns:
        True if upload succeeded, False otherwise
        
    Raises:
        FileNotFoundError: When local file doesn't exist
        PermissionError: When insufficient cloud storage permissions
        
    Example:
        >>> async def track_progress(bytes_uploaded: int):
        ...     print(f"Uploaded: {bytes_uploaded} bytes")
        ...
        >>> success = await upload_to_cloud_storage(
        ...     "data/articles.json",
        ...     "news-storage",
        ...     progress_callback=track_progress
        ... )
    """
    # Implementation here
    pass
```

### Generator Function
```python
def stream_articles_from_file(file_path: str, 
                             batch_size: int = 100) -> Generator[List[Article], None, None]:
    """Stream articles from a large file in configurable batches.
    
    This generator function provides memory-efficient processing of large article
    datasets by yielding articles in batches rather than loading everything into memory.
    
    Args:
        file_path: Path to the JSON file containing articles
        batch_size: Number of articles to yield per batch. Default: 100
        
    Yields:
        List of Article objects, with each batch containing up to batch_size articles
        
    Raises:
        FileNotFoundError: When the specified file doesn't exist
        JSONDecodeError: When file contains invalid JSON data
        
    Example:
        >>> for batch in stream_articles_from_file("large_dataset.json", batch_size=50):
        ...     print(f"Processing batch of {len(batch)} articles")
        ...     process_articles(batch)
        Processing batch of 50 articles
        Processing batch of 50 articles
        Processing batch of 23 articles  # Last batch
    """
    # Implementation here
    pass
```

---

## 🏗️ Class Templates

### Service Class
```python
class ScrapingService:
    """Service for orchestrating news article scraping operations.
    
    This service provides a high-level interface for scraping news articles from
    multiple outlets concurrently. It manages the complete scraping workflow
    including outlet discovery, content extraction, validation, and storage.
    
    The service implements several key patterns:
    - Producer-Consumer: Outlets are processed by worker threads
    - Circuit Breaker: Failing outlets are temporarily disabled
    - Rate Limiting: Respects per-domain request limits
    - Graceful Degradation: Continues operation despite individual failures
    
    Thread Safety:
        This class is thread-safe and can be safely used in multi-threaded
        environments. Internal state is protected by locks where necessary.
    
    Attributes:
        config: Application configuration containing scraping parameters
        logger: Structured logger for operation tracking and debugging
        outlet_service: Service for managing news outlet configurations
        storage_service: Service for persisting scraped articles
        
    Example:
        >>> scraper = ScrapingService(config, logger, outlet_service, storage_service)
        >>> scraper.start()
        >>> 
        >>> # Scrape all configured outlets
        >>> results = scraper.scrape_all_outlets()
        >>> print(f"Scraped {results.total_articles} articles")
        >>>
        >>> # Scrape specific outlets with limits
        >>> results = scraper.scrape_outlets(
        ...     outlet_names=["bbc", "reuters"],
        ...     article_limit=50
        ... )
        >>> scraper.stop()
    """
    
    def __init__(self, 
                 config: Config,
                 logger: logging.Logger,
                 outlet_service: OutletService,
                 storage_service: StorageService) -> None:
        """Initialize scraping service with required dependencies.
        
        Args:
            config: Application configuration object
            logger: Logger instance for this service
            outlet_service: Service for outlet management
            storage_service: Service for data persistence
            
        Raises:
            ValueError: When required configuration is missing
            TypeError: When dependencies are of incorrect type
        """
        # Implementation here
        pass
    
    def scrape_outlet(self, outlet: OutletSource, limit: Optional[int] = None) -> ScrapingResult:
        """Scrape articles from a specific news outlet.
        
        Args:
            outlet: The news outlet configuration to scrape
            limit: Maximum number of articles to extract
            
        Returns:
            ScrapingResult containing success status and article count
            
        Raises:
            ConnectionError: When outlet is unreachable
            ValidationError: When outlet configuration is invalid
        """
        # Implementation here
        pass
```

### Data Class
```python
@dataclass
class Article:
    """Represents a scraped news article with metadata.
    
    This immutable data class encapsulates all information about a scraped article
    including content, metadata, and processing information. It provides validation
    and serialization capabilities for storage and transmission.
    
    Attributes:
        title: Article headline or title
        url: Original URL where article was found
        content: Full article text content
        outlet_name: Name of the news outlet source
        published_at: Publication timestamp (UTC)
        scraped_at: When this article was scraped (UTC)
        word_count: Number of words in the content
        language: Detected language code (ISO 639-1)
        tags: List of content tags or categories
        author: Article author name if available
        
    Example:
        >>> article = Article(
        ...     title="Breaking News Title",
        ...     url="https://example.com/news/123",
        ...     content="Article content here...",
        ...     outlet_name="example_news",
        ...     published_at=datetime.utcnow(),
        ...     scraped_at=datetime.utcnow(),
        ...     word_count=150,
        ...     language="en",
        ...     tags=["politics", "international"],
        ...     author="John Reporter"
        ... )
        >>> print(f"{article.title} ({article.word_count} words)")
        Breaking News Title (150 words)
    """
    title: str
    url: str
    content: str
    outlet_name: str
    published_at: datetime
    scraped_at: datetime
    word_count: int
    language: str = "en"
    tags: List[str] = field(default_factory=list)
    author: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate article data after initialization.
        
        Raises:
            ValueError: When required fields are empty or invalid
        """
        if not self.title.strip():
            raise ValueError("Article title cannot be empty")
        if not self.url.strip():
            raise ValueError("Article URL cannot be empty")
        if self.word_count < 0:
            raise ValueError("Word count cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary for serialization.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        # Implementation here
        pass
```

### Exception Class
```python
class ScrapingError(Exception):
    """Base exception for scraping-related errors.
    
    This exception class provides structured error information for debugging
    and error handling in scraping operations. It includes context about
    the failure location and circumstances.
    
    Attributes:
        message: Human-readable error description
        outlet_name: Name of outlet where error occurred (if applicable)
        url: URL being processed when error occurred (if applicable)
        error_code: Machine-readable error code for programmatic handling
        
    Example:
        >>> try:
        ...     scrape_outlet(outlet)
        ... except ScrapingError as e:
        ...     print(f"Scraping failed for {e.outlet_name}: {e.message}")
        ...     if e.error_code == "NETWORK_TIMEOUT":
        ...         retry_scraping(outlet)
    """
    
    def __init__(self, 
                 message: str,
                 outlet_name: Optional[str] = None,
                 url: Optional[str] = None,
                 error_code: str = "GENERIC_ERROR") -> None:
        """Initialize scraping error with context information.
        
        Args:
            message: Human-readable error description
            outlet_name: Name of outlet where error occurred
            url: URL being processed when error occurred
            error_code: Machine-readable error code
        """
        super().__init__(message)
        self.message = message
        self.outlet_name = outlet_name
        self.url = url
        self.error_code = error_code
    
    def __str__(self) -> str:
        """Return formatted error message with context."""
        parts = [self.message]
        if self.outlet_name:
            parts.append(f"outlet={self.outlet_name}")
        if self.url:
            parts.append(f"url={self.url}")
        return " | ".join(parts)
```

---

## 📦 Module Templates

### Service Module
```python
"""
News outlet management service for Messor.

This module provides the OutletService class which manages news outlet configurations
and handles both API-based and local file-based outlet sources. It implements
intelligent fallback mechanisms to ensure scraping operations continue even when
external services are unavailable.

Key Features:
    - Multi-source outlet configuration (API + local files)
    - Automatic fallback on API failure
    - Outlet validation and deduplication
    - Alphabetical sorting for consistent processing
    - Comprehensive error handling and logging

The service supports multiple data sources:
    - Primary: External REST API for centralized outlet management
    - Fallback: Local JSON file for offline operation and redundancy
    - Runtime: Dynamic outlet addition for custom scraping targets

Example Usage:
    >>> from services.outlet_service import OutletService
    >>> outlet_service = OutletService(config, logger, rest_client)
    >>> outlets = outlet_service.get_outlets()
    >>> print(f"Found {len(outlets)} news outlets")

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import logging
from typing import List, Optional

# Module implementation here
```

### Utility Module
```python
"""
Utility functions for text processing and content validation.

This module provides a collection of utility functions for processing scraped
news content, including text cleaning, language detection, and content validation.
These utilities are used throughout the scraping pipeline to ensure high-quality
article extraction and storage.

Functions:
    clean_text: Remove unwanted characters and normalize whitespace
    detect_language: Identify the language of text content
    validate_article_quality: Check if article meets quality standards
    extract_keywords: Extract key terms from article content
    calculate_readability: Compute readability scores for content

Example:
    >>> from utils.text_processing import clean_text, detect_language
    >>> 
    >>> raw_text = "  Breaking News:   Multiple    spaces   here!  "
    >>> clean_text = clean_text(raw_text)
    >>> language = detect_language(clean_text)
    >>> print(f"Cleaned: '{clean_text}' (Language: {language})")
    Cleaned: 'Breaking News: Multiple spaces here!' (Language: en)

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import re
import string
from typing import Dict, List, Optional

# Utility functions here
```

---

## ✅ Docstring Checklist

Before committing code, ensure your docstrings include:

### **Required Elements:**
- [ ] One-line summary (imperative mood)
- [ ] Detailed description for complex functions
- [ ] All parameters documented with types
- [ ] Return value documented with type
- [ ] Exceptions documented with conditions

### **Optional Elements:**
- [ ] Usage examples for non-trivial functions
- [ ] Notes about thread safety or performance
- [ ] References to related functions or documentation
- [ ] Deprecation warnings if applicable

### **Style Guidelines:**
- [ ] Google docstring format
- [ ] Clear, concise language
- [ ] Present tense for descriptions
- [ ] Consistent terminology throughout
- [ ] Proper grammar and spelling

## 🛠️ Tools and Validation

### **Generate Documentation:**
```bash
# Generate API documentation
python scripts/generate_docs.py

# Validate docstrings only
python scripts/generate_docs.py --validate-only

# Include private methods
python scripts/generate_docs.py --include-private
```

### **Type Checking:**
```bash
# Run type checking
mypy core/ services/ api/

# Generate type stub files
stubgen -m services.outlet_service
```

### **Documentation Coverage:**
```bash
# Check documentation coverage
python scripts/generate_docs.py --coverage
```