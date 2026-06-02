#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core application orchestrator for Messor News Harvester.

This module provides the Application class that serves as the main entry point
and orchestrates all services within the Messor news harvesting system. It manages
the complete application lifecycle including service initialization, dependency
injection, scheduled operations, and graceful shutdown.

The Application class implements the following key patterns:
- Dependency Injection: Services are injected with their required dependencies
- Service Orchestration: Coordinates startup/shutdown of all system components
- Process Locking: Ensures single-instance scraping operations
- Environment Detection: Adapts behavior for Docker vs. native deployments

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""
import logging
import os
import threading
import time
from typing import List, Optional

from core.api_server import APIServer
from core.command_processor import CommandProcessor
from core.config import Config
from inkbytes.common.api.rest import RestClient
from services.logging_service import LoggingService
from services.outlet_service import OutletService
from services.scraper_service import ScraperService
from services.storage_service import StorageService
from services.analytics_service import AnalyticsService
from services.message_service import MessageService

class Application:
    """Main application orchestrator for Messor News Harvester.
    
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
    """
    
    # Application metadata constants
    NAME = "Messor"
    VERSION = "1.0.0"
    DESCRIPTION = "InkBytes News Harvester"
    AUTHOR = "Julian de la Rosa"
    AUTHOR_EMAIL = "juliandelarosa@icloud.com"
    COPYRIGHT = "InkBytes Technologies"
    
    def __init__(self, config_path: str) -> None:
        """Initialize application with configuration and set up service dependencies.
        
        This constructor implements the dependency injection pattern to wire all
        services together. Services are initialized in dependency order to ensure
        proper startup sequence.
        
        Args:
            config_path: Path to the YAML configuration file
            
        Raises:
            FileNotFoundError: When configuration file doesn't exist
            ValueError: When configuration is invalid or malformed
            
        Note:
            Services are lazy-loaded and connections are established during the
            run() method to allow for proper error handling and recovery.
        """
        # Initialize core services with configuration
        self.config = Config(config_path)
        self.logger = LoggingService(self.config)
        api_base_url = os.getenv("MESSOR_API_BASE_URL", self.config.platform_api.base_url())
        self.rest_client = RestClient(api_base_url)
        
        # Initialize message service for RabbitMQ event handling
        self.message_service = MessageService(self.config, self.logger)
        
        # Initialize storage service first since scraper service depends on it
        # This service handles both local file storage and cloud uploads
        self.storage_service = StorageService(self.config, self.logger, self.rest_client)
        self.storage_service.message_service = self.message_service  # Inject messaging capability
        
        # Initialize outlet service for news source management
        # Handles both API-based and local file-based outlet configurations
        self.outlet_service = OutletService(self.config, self.logger, self.rest_client)
        
        # Initialize scraper service with all required dependencies
        # This is the core service that orchestrates the web scraping operations
        self.scraper_service = ScraperService(
            self.config, 
            self.logger, 
            self.outlet_service,      # For getting news sources
            self.storage_service,     # For persisting scraped data
            self.message_service      # For publishing events
        )
        
        # Initialize supporting services
        self.analytics_service = AnalyticsService(self.logger)  # Performance metrics
        self.api_server = APIServer(self.config, self.logger)   # REST API interface
        
        # Initialize command processor for CLI interaction
        # This processor handles all user commands and interactive operations
        self.command_processor = CommandProcessor(
            self.logger,
            self.scraper_service,
            self.storage_service,
            self.analytics_service,
            self.api_server,
            self.message_service
        )
        
        # Initialize command queue for automated operations
        self.auto_command_queue: List[str] = []
        
        # Initialize process locking mechanism to prevent concurrent scraping
        # This ensures only one scraping operation runs at a time across all modes
        self._scraping_lock = threading.Lock()
        self._scraping_active = False
        
        # Wire the locking mechanism into the command processor
        self.command_processor.set_scraping_lock(self._scraping_lock, self)
    
    def run(self, 
            auto_start_client: bool = False, 
            auto_scrape: Optional[str] = None, 
            no_browser: bool = False, 
            scheduled_mode: bool = False) -> None:
        """Execute the application in the specified mode with given parameters.
        
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
        """
        self.logger.info("Starting main")
        try:
            should_connect_rabbitmq = True
            try:
                should_connect_rabbitmq = bool(self.config.logging.log_to_broker())
            except Exception:
                should_connect_rabbitmq = True

            # Connect to RabbitMQ only when broker logging is enabled
            if should_connect_rabbitmq:
                if self.message_service.connect():
                    # Start the background health check thread
                    self.message_service.start_health_check_thread()
                else:
                    self.logger.warning("Failed to connect to RabbitMQ, continuing without messaging")
            else:
                self.logger.info("RabbitMQ messaging disabled by configuration")
            
            # Start the API server
            self.api_server.start()
            
            # Give the server a moment to start
            time.sleep(1)
            
            # Handle client app startup
            client_process = None
            
            # Only start client if explicitly requested with --client flag  
            if auto_start_client:
                print("\nAuto-starting client web application...")
                client_choice = 'y'
            else:
                client_choice = 'n'
                
            if client_choice == 'y' or client_choice == 'yes':
                try:
                    import subprocess
                    import os
                    
                    print("\nStarting client application...")
                    client_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client")
                    
                    if os.name == 'nt':  # Windows
                        client_process = subprocess.Popen(["cmd", "/c", "cd", client_dir, "&&", "npm", "run", "dev"], 
                                                        creationflags=subprocess.CREATE_NEW_CONSOLE)
                    else:  # macOS/Linux
                        client_process = subprocess.Popen(["npm", "run", "dev"], 
                                                        cwd=client_dir, 
                                                        stdout=subprocess.PIPE, 
                                                        stderr=subprocess.PIPE)
                    
                    # Set client URL
                    client_url = "http://localhost:5173"
                    
                    # Launch browser automatically if not disabled
                    if not no_browser:
                        import webbrowser
                        print(f"Client application started. Opening dashboard at {client_url}")
                        # Use a small delay to ensure server has time to start
                        threading.Timer(1.5, lambda: webbrowser.open(client_url)).start()
                    else:
                        print(f"Client application started. Dashboard available at {client_url}")
                        
                    print("The client will run in the background while you interact with the command line.\n")
                except Exception as e:
                    self.logger.error(f"Error starting client application: {e}")
                    print(f"Error starting client application: {e}")
                    print("You can start it manually with: cd client && npm run dev\n")
            
            # Handle scheduled mode for Docker environments
            if scheduled_mode:
                self._run_scheduled_mode(auto_scrape)
            else:
                # Queue scrape command if requested
                if auto_scrape is not None:
                    scrape_command = f"SCRAPE {auto_scrape}" if auto_scrape else "SCRAPE"
                    self.auto_command_queue.append(scrape_command)
                    print(f"\nQueued scrape command: {scrape_command}")
                
                # Process commands in the main thread
                self.command_processor.process_commands(self.auto_command_queue)
            
            # Clean up connections and processes
            self.message_service.close()
            
            # Terminate client process if it was started
            if client_process:
                try:
                    client_process.terminate()
                    print("\nClient application has been stopped.")
                except:
                    pass
            
            self.logger.info("Completed main")
        except Exception as e:
            self.logger.error(f"Error in main: {e}")
            import sys
            sys.exit(1)
    
    def _is_docker_environment(self):
        """Detect if running in a Docker container."""
        import os
        return (
            os.path.exists('/.dockerenv') or 
            os.environ.get('DOCKER_CONTAINER') == 'true' or
            os.environ.get('CONTAINER') == 'docker'
        )
    
    def _run_scheduled_mode(self, scrape_args=None):
        """Run the application in scheduled mode for Docker environments."""
        import time
        
        interval_minutes = self.config.get_schedule_interval_minutes()
        
        self.logger.info(f"Starting scheduled mode with {interval_minutes} minute intervals")
        print(f"\n=== SCHEDULED MODE ACTIVE ===")
        print(f"Running scraping every {interval_minutes} minutes")
        print(f"Docker environment detected: {self._is_docker_environment()}")
        print("Press Ctrl+C to stop scheduled execution")
        print("================================\n")
        
        try:
            while True:
                # Execute scraping
                start_time = time.time()
                self.logger.info("Starting scheduled scraping cycle")
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting scraping cycle...")
                
                try:
                    success = self.execute_scraping_with_lock(scrape_args)
                    duration = time.time() - start_time
                    
                    if success:
                        self.logger.info(f"Scraping cycle completed in {duration:.2f} seconds")
                        print(f"✅ Scraping cycle completed in {duration:.2f} seconds")
                    else:
                        self.logger.info(f"Scraping cycle skipped (already running) after {duration:.2f} seconds")
                        print(f"⏭️  Scraping cycle skipped (already running)")
                except Exception as e:
                    self.logger.error(f"Error during scheduled scraping: {e}")
                    print(f"❌ Error during scheduled scraping: {e}")
                
                # Wait for the next cycle
                wait_seconds = interval_minutes * 60
                next_run = time.time() + wait_seconds
                next_run_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_run))
                
                self.logger.info(f"Next scraping cycle scheduled for: {next_run_str}")
                print(f"Next scraping cycle scheduled for: {next_run_str}")
                print(f"Waiting {interval_minutes} minutes...\n")
                
                time.sleep(wait_seconds)
                
        except KeyboardInterrupt:
            self.logger.info("Scheduled mode interrupted by user")
            print("\nScheduled mode stopped by user.")
        except Exception as e:
            self.logger.error(f"Error in scheduled mode: {e}")
            print(f"Error in scheduled mode: {e}")
            raise
    
    def is_scraping_active(self):
        """Check if a scraping process is currently active."""
        return self._scraping_active
    
    def execute_scraping_with_lock(self, scrape_args=None):
        """Execute scraping with lock protection to prevent overlapping processes."""
        if not self._scraping_lock.acquire(blocking=False):
            self.logger.warning("Scraping process already active, skipping this cycle")
            print("⚠️  Scraping process already active, skipping this cycle")
            return False
        
        try:
            self._scraping_active = True
            self.logger.info("Acquired scraping lock, starting scraping process")
            self.command_processor._execute_scraping_internal(scrape_args)
            return True
        except Exception as e:
            self.logger.error(f"Error during locked scraping: {e}")
            raise
        finally:
            self._scraping_active = False
            self._scraping_lock.release()
            self.logger.info("Released scraping lock")
