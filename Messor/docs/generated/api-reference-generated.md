# API Reference

## core/scraper.py

### class SessionSavingMode

*No documentation available*

### class JsonEncoderForDateTime

*No documentation available*

#### encodeDatetimeObject(self, obj)

*No documentation available*

### class ScrapingStats

*No documentation available*

### class ScrapingSession

*No documentation available*

#### complete_session(self)

Mark the session as completed and set the end time.

#### increment_total_articles(self)

Increment the total number of articles.

#### increment_failed_articles(self)

Increment the number of failed articles.

#### increment_successful_articles(self)

Increment the number of successful articles.

#### increment_duplicates_current_batch(self)

Increment the number of duplicate articles in the current batch.

#### increment_duplicates_previous_scrapes(self)

Increment the number of duplicate articles found in previous scrapes.

#### set_results_staging_file_name(self, file_name)

Set the name of the results staging file.

#### calculate_duration(self)

Calculate the duration of the scraping session in seconds.

#### calculate_success_rate(self)

Calculate the success rate of the scraping session.

#### calculate_duplicate_rate(self)

Calculate the percentage of articles that were detected as duplicates.

#### to_json(self)

Convert the session to a JSON-serializable dict.

### class Config

*No documentation available*

### class ScraperResults

*No documentation available*

### class NewsScraper

Class responsible for scraping news articles from a given news outlet.

#### scrape_news_outlet(self, executor, outlet)

Scrape articles from a news outlet.

Args:
    executor: The executor for concurrent processing.
    outlet: The outlet to scrape.

Returns:
    ScrapingSession: The scraping session with stats.

#### process_outlet_articles(self, outletBrand, results)

Process articles from an outlet and save them to the database.
Checks for duplicates not only in the current database but also in previously scraped files.

Args:
    outletBrand: The brand name of the outlet.
    results: List of article futures to process.

#### log_progress()

*No documentation available*

### Functions

#### scrape_outlet(outlet: Any, agent: Any, headers: Any, num_workers: Any, languages: Any) -> ScrapingSession

Scrape articles from a given outlet.

This function coordinates the scraping process for a single outlet:
1. Initializes the newspaper and scraper
2. Scrapes the outlet
3. Handles duplicate article detection across sessions
4. Completes the session with statistics

Args:
    outlet: The news outlet to scrape.
    agent: The user agent to use.
    headers: The headers to use for the request.
    num_workers: Number of concurrent workers.
    languages: List of languages to filter articles by.

Returns:
    ScrapingSession: The scraping session containing stats.

#### validate_outlet_url(outlet: Any)

Validate that an outlet URL is not empty.

Args:
    outlet: The Outlet object containing the URL to be validated.

Returns:
    bool: True if the URL is valid and not empty.

#### process_found_articles(executor: Any, outlet: Any, paper: Any) -> list

Process articles found in a newspaper.

Args:
    executor: The executor to submit tasks to.
    outlet: The outlet being scraped.
    paper: The newspaper object containing articles.

Returns:
    list: A list of futures for article scraping tasks.

#### article_exists(article: Article, data_handler: DataHandler) -> bool

Check if an article already exists in the database.

Args:
    article: The article to check.
    data_handler: The database handler.

Returns:
    bool: True if the article exists, False otherwise.

#### check_article_exists_in_all_scrapes(article: Article, outlet_name: str) -> bool

Check if an article already exists in any scrape file for the given outlet.

Args:
    article: The article to check.
    outlet_name: The name of the outlet.
    
Returns:
    bool: True if the article exists in any scrape file, False otherwise.

#### pre_process_article(article: newspaper.Article) -> newspaper.Article

Download, parse and run NLP on an article.

Args:
    article: The newspaper article object.

Returns:
    newspaper.Article: The processed article, or None if processing failed.

#### scrape_outlet_article(article: newspaper.Article, newsPaperBrand: str) -> Article

Scrape a single article from an outlet.

Args:
    article: The newspaper article to scrape.
    newsPaperBrand: The name of the newspaper brand.

Returns:
    Article: The scraped article object.

#### extract_metadata_category(data: dict) -> List[str]

Extract comprehensive category information from article metadata.

Args:
    data: The metadata dictionary.

Returns:
    list: List of unique categories found in metadata.

#### extract_html_categories(html: str) -> List[str]

Extract categories from the HTML content of a page.

Args:
    html: HTML content of the page.

Returns:
    list: List of categories found in HTML.

#### extract_newspaper_metadata(article: newspaper.Article) -> Dict[(str, Any)]

Extract metadata from a newspaper Article object.

Args:
    article: A newspaper.Article object.

Returns:
    dict: A dictionary of metadata.

#### extract_url_categories(url: str) -> List[str]

Extract potential categories from the URL structure.

Args:
    url: The URL to extract categories from.

Returns:
    list: A list of potential categories extracted from the URL.

#### unify_keywords(article: Article) -> List[str]

Combine keywords from article and its metadata.

Args:
    article: The article object.

Returns:
    list: Combined and deduplicated keywords.

#### get_comprehensive_categories(article: newspaper.Article, articleRecord: Article) -> List[str]

Get comprehensive categories from multiple sources for an article.

Args:
    article: The newspaper article object.
    articleRecord: The Article record object.

Returns:
    list: A comprehensive list of categories from all available sources.

#### create_article_record(article: newspaper.Article, newsPaperBrand: str) -> Article

Create an article record from a newspaper article.

Args:
    article: The newspaper article.
    newsPaperBrand: The newspaper brand name.

Returns:
    Article: The created article record.

#### build_newspaper_article(article: newspaper.Article) -> newspaper.Article

Build a newspaper article by processing it.

Args:
    article: The article to build.

Returns:
    newspaper.Article: The built article if successful, None otherwise.

#### handle_error_in_article_processing(article: newspaper.Article, error: ValueError) -> None

Handle errors that occur during article processing.

Args:
    article: The article being processed.
    error: The error that occurred.

## core/config.py

### class Config

*No documentation available*

#### logging(self)

*No documentation available*

#### strapi_cms(self)

*No documentation available*

#### digitalocean(self)

*No documentation available*

#### scraping(self)

*No documentation available*

#### get_schedule_interval_minutes(self)

Get the schedule interval in minutes, default to 60 if not configured.

#### articles(self)

*No documentation available*

#### storage(self)

*No documentation available*

#### fast_api(self)

*No documentation available*

#### rabbitmq(self)

Access to RabbitMQ configuration.

#### get_thread_count(self)

Calculate the optimal number of worker threads.

## core/application.py

### class Application

Main application orchestrator for Messor News Harvester.

This class serves as the central coordinator for all system services and manages
the complete application lifecycle. It implements dependency injection to wire
services together and provides different execution modes for various deployment
scenarios.

The application supports multiple execution modes:
- Interactive CLI: Manual command processing with user interaction
- One-shot: Execute specific operations and exit
- Scheduled: Continuous operation with automated scraping cycles (Docker)

Thread Safety:
    This class implements process locking to ensure only one scraping operation
    runs at a time, making it safe for concurrent access and scheduled execution.

Attributes:
    NAME: Application display name
    VERSION: Semantic version number
    DESCRIPTION: Brief application description
    AUTHOR: Primary author information
    AUTHOR_EMAIL: Contact email for the author
    COPYRIGHT: Copyright holder information
    
Example:
    >>> app = Application('env.yaml')
    >>> app.run(auto_start_client=True, scheduled_mode=False)
    
    # Docker scheduled mode
    >>> app = Application('env.yaml')
    >>> app.run(scheduled_mode=True)

#### run(self, auto_start_client, auto_scrape, no_browser, scheduled_mode)

Execute the application in the specified mode with given parameters.

This is the main entry point that orchestrates the complete application
lifecycle. It handles service startup, mode selection, and graceful shutdown.
The method supports multiple execution modes to accommodate different
deployment scenarios and use cases.

Execution Modes:
    - Interactive: Default CLI mode with user interaction
    - One-shot: Execute scraping and exit (when auto_scrape provided)
    - Scheduled: Continuous operation with automated cycles (Docker mode)
    - Client: Web dashboard mode with optional browser launch

Args:
    auto_start_client: Automatically start the React web dashboard.
        When True, launches the client development server and optionally
        opens the browser. Default: False
    auto_scrape: Parameters for automatic scraping execution.
        Format: "--limit=N --outlet=name|url" or empty string for default.
        When provided, queues scraping for immediate execution. Default: None
    no_browser: Suppress automatic browser launch when starting client.
        Only effective when auto_start_client is True. Default: False
    scheduled_mode: Enable continuous scheduled scraping mode.
        Designed for Docker environments, runs scraping at configured
        intervals with automatic retry and overlap prevention. Default: False
        
Raises:
    SystemExit: On critical errors that prevent application startup
    KeyboardInterrupt: When user interrupts scheduled mode execution
    
Example:
    # Interactive CLI mode
    >>> app.run()
    
    # One-shot scraping with client dashboard
    >>> app.run(auto_start_client=True, auto_scrape="--limit=5")
    
    # Docker scheduled mode
    >>> app.run(scheduled_mode=True)
    
Note:
    In scheduled mode, the method runs indefinitely until interrupted.
    All other modes will eventually terminate and return control.

#### is_scraping_active(self)

Check if a scraping process is currently active.

#### execute_scraping_with_lock(self, scrape_args)

Execute scraping with lock protection to prevent overlapping processes.

## core/api_server.py

### class APIServer

*No documentation available*

#### start(self)

Start the FastAPI server with configured parameters.

## core/command_processor.py

### class CommandProcessor

*No documentation available*

#### set_scraping_lock(self, scraping_lock, application)

Set the scraping lock and application reference.

#### execute_scraping(self, args)

Execute scraping process and handle results.

Args:
    args: Optional string of arguments in the format:
          --limit=N to scrape only N outlets
          --outlet="name|url" to scrape a custom outlet not in the database

This implementation handles the scraping, publishing events to RabbitMQ,
and moving files to Digital Ocean S3 in a single command.

#### analyze_and_display_complexity(self, args)

Analyze complexity and display results.

Args:
    args: Optional arguments to pass to execute_scraping

#### display_queue_status(self)

Display status of RabbitMQ queues.

#### publish_test_message(self)

Publish a test message to RabbitMQ for testing.

#### display_help(self)

Display available commands.

#### display_version(self)

Display version information.

#### display_about_info(self)

Display information about the project and its author.

#### do_exit(self)

Exit the application gracefully.

#### process_commands(self, auto_command_queue)

Process user commands in a loop.

## services/message_service.py

### class MessageService

Service for handling RabbitMQ messaging operations.

#### start_health_check_thread(self)

Start a thread to periodically check the connection health.

#### health_check_worker()

*No documentation available*

#### connect(self)

Establish connection to RabbitMQ server.

#### close(self)

Close the RabbitMQ connection.

#### publish_message(self, queue, message)

Publish a message to a RabbitMQ queue.
Will attempt to reopen the channel if it's closed.

#### publish_articles_scraped_event(self, scraping_session, bucket, file_path)

Publish an event indicating articles have been scraped and uploaded to S3.

#### publish_topics_extracted_event(self, file_info)

Publish an event indicating topics have been extracted from articles.

## services/logging_service.py

### class LoggingService

*No documentation available*

#### info(self, message)

*No documentation available*

#### error(self, message)

*No documentation available*

#### warning(self, message)

*No documentation available*

## services/outlet_service.py

### class OutletService

Service for managing news outlet configurations and data sources.

This service provides a unified interface for accessing news outlet configurations
from multiple sources, with intelligent fallback mechanisms to ensure high
availability. It handles outlet validation, sorting, and dynamic management.

The service implements a hierarchical data source strategy:
1. Primary: External API (Strapi CMS) for centralized management
2. Fallback: Local JSON file for offline operation
3. Auto-creation: Generates default outlets if no sources available

Features:
    - Automatic API-to-local fallback on connection failures
    - Intelligent outlet validation and deduplication
    - Support for custom runtime outlet injection
    - Alphabetical sorting for consistent processing order
    - Comprehensive error handling and logging

Attributes:
    config: Application configuration containing API endpoints and settings
    logger: Structured logger for operation tracking and debugging
    rest_client: HTTP client for external API communications
    
Example:
    >>> outlet_service = OutletService(config, logger, rest_client)
    >>> outlets = outlet_service.get_outlets()
    >>> print(f"Found {len(outlets)} news outlets")
    Found 25 news outlets
    
    # Outlets are automatically sorted alphabetically by name
    >>> for outlet in outlets[:3]:
    ...     print(f"- {outlet.name}: {outlet.url}")
    - bbc: https://www.bbc.com/
    - cnn: https://www.cnn.com/
    - reuters: https://www.reuters.com/

#### get_outlets(self, source)

Retrieve news outlet configurations from available data sources.

This method implements a robust outlet retrieval strategy with automatic
fallback mechanisms. It first attempts to fetch outlets from the external
API, and if that fails (due to network issues, API downtime, or empty
responses), it automatically falls back to local data sources.

The method ensures consistent outlet ordering and validates all outlet
configurations before returning them for scraping operations.

Args:
    source: The preferred data source for outlet retrieval.
        Defaults to REST_API for centralized management.
        
Returns:
    List of validated OutletsSource objects, sorted alphabetically by name.
    Returns empty list only if all data sources are unavailable or invalid.
    
Example:
    >>> outlets = outlet_service.get_outlets()
    >>> print(f"Retrieved {len(outlets)} outlets")
    Retrieved 25 outlets
    
    # Outlets are pre-sorted for consistent processing
    >>> first_outlet = outlets[0]
    >>> print(f"First outlet: {first_outlet.name} -> {first_outlet.url}")
    First outlet: bbc -> https://www.bbc.com/

Note:
    This method implements automatic retry logic and fallback strategies
    to maximize availability. Monitor logs for fallback notifications
    which may indicate external service issues.

## services/scraper_service.py

### class ScraperService

*No documentation available*

#### create_outlet_scraping_session(self, outlet)

Extract articles from a single outlet and handle file upload and messaging.

Now with enhanced duplicate detection across scraping sessions.

#### generate_outlets_scraping_sessions(self, outlets)

Scrape multiple outlets concurrently using a thread pool.

#### execute_scraping_process(self, limit, custom_outlet)

Execute the scraping process for outlets.

Args:
    limit: Optional limit on number of outlets to scrape
    custom_outlet: Optional custom outlet definition (dict with name and url)

Returns:
    List of scraping session results

## services/storage_service.py

### class StorageService

*No documentation available*

#### save_scraping_session(self, scraping_session)

Save scraping session data based on configured saving mode.

#### save_session_to_file(self, scraping_session, file_path)

Save the scraping session to a local file.

#### send_session_to_api(self, scraping_session)

Send the scraping session to the API.

#### upload_file_to_s3(self, local_file_path, bucket, folder)

Upload a single file to S3 and publish an event.

#### execute_files_move(self)

Upload scraped files to Digital Ocean Spaces and publish events.

#### execute_files_clean(self)

Clean up staging files after successful processing.

## services/analytics_service.py

### class AnalyticsService

*No documentation available*

#### analyze_complexity(self, scraping_sessions)

Analyze the complexity of the scraping process based on the scraping sessions.

## api/main.py

### Functions

#### shutdown()

*No documentation available*

#### on_shutdown()

*No documentation available*

## api/routers/scrape.py

### class ConnectionManager

Manages WebSocket connections and message queues for each client.

This class is responsible for:
- Tracking active WebSocket connections
- Managing message queues for each connection
- Providing thread-safe methods to send messages to clients

#### disconnect(self, websocket)

Remove a WebSocket connection and clean up its resources.

Args:
    websocket: The WebSocket connection to remove

#### queue_message(self, message, websocket)

Thread-safe method to queue a message for sending to a WebSocket client.

This method can be called from any thread to safely queue messages
for delivery to the WebSocket client.

Args:
    message: The message to queue
    websocket: The WebSocket connection to send to
    
Returns:
    bool: True if message was queued successfully, False otherwise

### class ThreadSafeLogger

A proxy logger that safely queues messages for the WebSocket.

This class intercepts logging calls from the scraper and forwards them
to both the original logger and the WebSocket client via a thread-safe queue.

#### info(self, message)

Log an info message and queue it for WebSocket delivery.

Args:
    message: The message to log

#### error(self, message)

Log an error message and queue it for WebSocket delivery.

Args:
    message: The message to log

#### warning(self, message)

Log a warning message and queue it for WebSocket delivery.

Args:
    message: The message to log

### Functions

#### run_scraper_with_logging()

Run the scraper with intercepted logging.

This function:
1. Saves the original logger
2. Replaces it with our thread-safe logger
3. Runs the scraping process
4. Restores the original logger

Returns:
    The result of the scraping process

#### load_rabbit_config()

Load RabbitMQ configuration from queue.json file

#### fetch_from_rabbitmq()

Fetch the latest scraping results from RabbitMQ

#### format_scrape_results(raw_data: Any)

Format raw scraping results into the expected API response format

#### read_results_from_disk()

Read scraping results from a JSON file on disk

## api/utils/log_readers.py

## api/utils/api_security.py

