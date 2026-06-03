#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command processor for the Messor application.

This module processes user commands and maps them to appropriate actions.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import sys
import threading
from datetime import datetime
from typing import Dict, Callable

class CommandProcessor:
    def __init__(self, logger, scraper_service, storage_service, analytics_service, api_server, message_service=None):
        self.logger = logger
        self.scraper_service = scraper_service
        self.storage_service = storage_service
        self.analytics_service = analytics_service
        self.api_server = api_server
        self.message_service = message_service
        self.exit_event = threading.Event()
        
        # Scraping lock (set by Application)
        self._scraping_lock = None
        self._application = None
        self.commands = self._register_commands()
        
        # Get Application metadata reference
        from core.application import Application
        self.app_metadata = {
            'name': Application.NAME,
            'version': Application.VERSION,
            'description': Application.DESCRIPTION,
            'author': Application.AUTHOR,
            'email': Application.AUTHOR_EMAIL,
            'copyright': Application.COPYRIGHT
        }
    
    def set_scraping_lock(self, scraping_lock, application):
        """Set the scraping lock and application reference."""
        self._scraping_lock = scraping_lock
        self._application = application

    """
    Internal use to register commands
        # This method is called during initialization to set up the command handlers
        # It returns a dictionary mapping command names to their respective handler functions.
        # This allows for easy addition or modification of commands in the future.
        # The commands are registered based on the services available, such as message_service.
        # This allows for dynamic command registration based on the configuration and services in use.
    """

    def _register_commands(self) -> Dict[str, Callable]:
        """Register command handlers."""
        commands = {
            # Main commands
            "SCRAPE": self.execute_scraping,
            "MOVE": self.storage_service.execute_files_move,
            "CLEAN": self.storage_service.execute_files_clean,
            "EXIT": self.do_exit,
            "ANALYZE": self.analyze_and_display_complexity,
            "HELP": self.display_help,
            "ABOUT": self.display_about_info,
            "VERSION": self.display_version
        }
        
        # Add RabbitMQ commands if message_service is available
        if self.message_service:
            commands.update({
                "QUEUE_STATUS": self.display_queue_status,
                "PUBLISH_TEST": self.publish_test_message
            })
            
        return commands
    
    def execute_scraping(self, args=None):
        """
        Execute scraping process and handle results.
        
        Args:
            args: Optional string of arguments in the format:
                  --limit=N to scrape only N outlets
                  --outlet="name|url" to scrape a custom outlet not in the database
        
        This implementation handles the scraping, publishing events to RabbitMQ,
        and moving files to Digital Ocean S3 in a single command.
        """
        # Check if we should use the lock mechanism for interactive commands
        if self._application and self._scraping_lock:
            if not self._scraping_lock.acquire(blocking=False):
                self.logger.warning("Scraping process already active, cannot start new scraping")
                print("⚠️  A scraping process is already running. Please wait for it to complete.")
                return
            
            try:
                self._application._scraping_active = True
                self.logger.info("Acquired scraping lock for interactive command")
                self._execute_scraping_internal(args)
            finally:
                self._application._scraping_active = False
                self._scraping_lock.release()
                self.logger.info("Released scraping lock for interactive command")
        else:
            # Fallback for when lock is not available (shouldn't happen in normal operation)
            self._execute_scraping_internal(args)
    
    def _execute_scraping_internal(self, args=None):
        """Internal scraping execution without lock management."""
        self.logger.info("Starting execute_scraping")
        
        limit = None
        custom_outlet = None
        
        # Parse arguments if provided
        if args:
            args = args.strip()
            # Parse limit parameter
            if "--limit=" in args:
                try:
                    limit_str = args.split("--limit=")[1].split()[0]
                    limit = int(limit_str)
                    self.logger.info(f"Limit parameter provided: {limit}")
                except (ValueError, IndexError):
                    self.logger.warning("Invalid limit parameter, ignoring")
            
            # Parse custom outlet parameter
            if "--outlet=" in args:
                try:
                    outlet_str = args.split("--outlet=")[1].split('"')[1]
                    name, url = outlet_str.split("|")
                    custom_outlet = {"name": name, "url": url}
                    self.logger.info(f"Custom outlet provided: {name} - {url}")
                except (ValueError, IndexError):
                    self.logger.warning("Invalid outlet parameter, ignoring")
        
        # Execute scraping with parameters
        sessions = self.scraper_service.execute_scraping_process(limit=limit, custom_outlet=custom_outlet)
        
        # In the new refactored version, the ScraperService now handles
        # saving sessions, publishing events, and moving files to S3,
        # so we don't need additional steps here.
        
        self.logger.info(f"Completed scraping of {len(sessions)} sessions")
        return sessions
        
    def analyze_and_display_complexity(self, args=None):
        """
        Analyze complexity and display results.
        
        Args:
            args: Optional arguments to pass to execute_scraping
        """
        sessions = self.execute_scraping(args)
        result = self.analytics_service.analyze_complexity(sessions)
        print("\n=== COMPLEXITY ANALYSIS ===")
        print(f"Total sessions: {result['total_sessions']}")
        print(f"Total articles: {result['total_articles']}")
        print(f"Average articles per session: {result['average_articles_per_session']:.2f}")
        print(f"Errors: {result['errors']}")
        print("===========================\n")
    
    # Add new methods for RabbitMQ commands
    
    def display_queue_status(self):
        """Display status of RabbitMQ queues."""
        if not self.message_service:
            print("Message service not available")
            return
            
        try:
            if not self.message_service.connection or not self.message_service.connection.is_open:
                if not self.message_service.connect():
                    print("Failed to connect to RabbitMQ")
                    return
                    
            # Get queue status — Messor only owns articles-scraped.
            # topics-extracted is Curator's output queue (see ADR-0005).
            articles_queue = self.message_service.channel.queue_declare(
                queue=self.message_service._articles_scraped_queue,
                passive=True
            )

            print("\n=== RABBITMQ QUEUE STATUS ===")
            print(f"Articles scraped queue: {articles_queue.method.message_count} messages")
            print("=============================\n")
        except Exception as e:
            self.logger.error(f"Error getting queue status: {e}")
            print(f"Error getting queue status: {e}")
    
    def publish_test_message(self):
        """Publish a test message to RabbitMQ for testing."""
        if not self.message_service:
            print("Message service not available")
            return
            
        try:
            # Messor only publishes to articles-scraped. ADR-0005.
            queue_name = self.message_service._articles_scraped_queue
            message = {
                "event_type": "test_articles_scraped",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "test": True,
                    "message": "This is a test message"
                }
            }
            if self.message_service.publish_message(queue_name, message):
                print(f"Test message published to {queue_name}")
            else:
                print(f"Failed to publish test message to {queue_name}")
        except Exception as e:
            self.logger.error(f"Error publishing test message: {e}")
            print(f"Error publishing test message: {e}")
        
    def display_help(self):
        """Display available commands."""
        print("\n=== AVAILABLE COMMANDS ===")
        print("SCRAPE - Scrape articles from configured outlets, publish events, and move files to S3")
        print("  Options:")
        print("    --limit=N          - Scrape only the first N outlets")
        print("    --outlet=\"name|url\" - Scrape a custom outlet not in the database")
        print("  Examples:")
        print("    SCRAPE --limit=5")
        print("    SCRAPE --outlet=\"techblog|https://techblog.example.com\"")
        print("MOVE - Move files to Digital Ocean storage")
        print("CLEAN - Clean up staging files")
        print("ANALYZE - Analyze complexity of scraping process")
        print("  Options: Same as SCRAPE command")
        
        # Add RabbitMQ commands to help if available
        if self.message_service:
            print("QUEUE_STATUS - Display status of RabbitMQ queues")
            print("PUBLISH_TEST - Publish a test message to RabbitMQ")
            
        print("ABOUT - Display information about the project and its author")
        print("VERSION - Display version information")
        print("HELP - Display this help message")
        print("EXIT - Exit the application")
        print("=========================\n")
        
    def display_version(self):
        """Display version information."""
        import datetime
        current_year = datetime.datetime.now().year
        
        print(f"\n{self.app_metadata['name']} {self.app_metadata['version']}")
        print(f"{self.app_metadata['description']}")
        print(f"© {current_year} {self.app_metadata['copyright']}\n")
        
    def display_about_info(self):
        """Display information about the project and its author."""
        import datetime
        
        # ASCII art logo
        logo = r"""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   __  __ _____ ____ ____   ___  ____                  ║
    ║   |  \/  | ____/ ___/ ___| / _ \|  _ \                ║
    ║   | |\/| |  _| \___ \___ \| | | | |_) |               ║
    ║   | |  | | |___ ___) |__) | |_| |  _ <                ║
    ║   |_|  |_|_____|____/____/ \___/|_| \_\               ║
    ║                                                       ║
    ║          Inkbytes News Harvester                      ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
        
        # Project information
        current_year = datetime.datetime.now().year
        
        print(logo)
        print(f"  {self.app_metadata['name']} - {self.app_metadata['description']}")
        print(f"  Version: {self.app_metadata['version']}")
        print("\n  A powerful news scraping and analysis tool that harvests")
        print("  articles from various news outlets. Part of the InkBytes ecosystem.")
        print("\n  Key Features:")
        print("  • Automated news harvesting from multiple outlets")
        print("  • Content analysis and extraction")
        print("  • Category and keyword detection")
        print("  • Cloud storage integration")
        print("  • Message queue processing")
        print("  • Web dashboard for monitoring")
        print(f"\n  Author: {self.app_metadata['author']} ({self.app_metadata['email']})")
        print(f"  Copyright © {current_year} {self.app_metadata['copyright']}")
        print("  All rights reserved.\n")
            
    def do_exit(self):
        """Exit the application gracefully."""
        self.logger.info("Starting do_exit")
        self.logger.info("Exiting application")
        self.exit_event.set()
        self.logger.info("Completed do_exit")
        sys.exit(0)
    
    def process_commands(self, auto_command_queue=None):
        """Process user commands in a loop."""
        self.logger.info("Starting process_commands")
        
        self.logger.info("Command processor started. Type 'HELP' for available commands.")
        
        # Process any auto commands first
        if auto_command_queue:
            for auto_command in auto_command_queue:
                print(f"\nExecuting auto command: {auto_command}")
                self._execute_command(auto_command)
        
        while not self.exit_event.is_set():
            try:
                # Get command input from user
                command_input = input("\nEnter command: ").strip()
                
                if not command_input:
                    continue
                
                self._execute_command(command_input)
                
            except KeyboardInterrupt:
                self.logger.info("Command input interrupted")
                self.do_exit()
                break
            except Exception as e:
                self.logger.error(f"Error processing command: {e}")
                
        self.logger.info("Completed process_commands")
    
    def _execute_command(self, command_input):
        """Execute a single command."""
        # Extract the command and arguments
        parts = command_input.split(None, 1)
        command = parts[0].upper()
        args = parts[1] if len(parts) > 1 else None
        
        if command in self.commands:
            self.logger.info(f"Executing command: {command}" + (f" with args: {args}" if args else ""))
            
            # Special handling for commands that accept arguments
            if command in ["SCRAPE", "ANALYZE"] and args:
                self.commands[command](args)
            else:
                self.commands[command]()
        else:
            self.logger.warning(f"Unknown command: {command}")
            self.display_help()