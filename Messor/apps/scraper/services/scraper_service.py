#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper Service for the Messor application.

This module provides services for scraping articles from configured outlets.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import concurrent.futures
import json
import os
from typing import List, Generator
from datetime import datetime
from core.scraper import scrape_outlet
from inkbytes.models.outlets import OutletsDataSource, OutletsSource

class ScraperService:
    def __init__(self, config, logger, outlet_service, storage_service=None, message_service=None):
        self.config = config
        self.logger = logger
        self.outlet_service = outlet_service
        self.storage_service = storage_service
        self.message_service = message_service
        self.num_threads = config.get_thread_count()
    
    def create_outlet_scraping_session(self, outlet: OutletsSource):
        """
        Extract articles from a single outlet and handle file upload and messaging.
        
        Now with enhanced duplicate detection across scraping sessions.
        """
        self.logger.info(f"Starting create_outlet_scraping_session: {outlet}")
        try:
            scraping_session = scrape_outlet(
                outlet,
                agent=self.config.scraping.agent.default(),
                headers=self.config.scraping.headers.default(),
                num_workers=self.num_threads,
                languages=self.config.articles.supported_languages()
            )
            session_info = scraping_session.to_json()
            
            # If we have a file path in the session, handle it
            if session_info.get("data") and session_info["data"].get("results_staging_file_name"):
                # Handle the completed session (upload to S3 and send to RabbitMQ)
                self._handle_completed_session(session_info)
                
                # Log details about duplicate filtering
                successful = session_info["data"]["successful_articles"]
                failed = session_info["data"]["failed_articles"]
                total = session_info["data"]["total_articles"]
                
                # Get detailed duplicate statistics if available
                duplicates_current = session_info["data"].get("duplicates_current_batch", 0)
                duplicates_previous = session_info["data"].get("duplicates_previous_scrapes", 0)
                total_duplicates = duplicates_current + duplicates_previous
                duplicate_rate = session_info["data"].get("duplicate_rate", 0)
                
                if total > 0:
                    self.logger.info(
                        f"Duplicate filtering stats for {outlet.name}: "
                        f"Total: {total} articles | "
                        f"New: {successful} | "
                        f"Duplicates: {total_duplicates} ({duplicate_rate:.1f}%) | "
                        f"Current batch: {duplicates_current} | Previous scrapes: {duplicates_previous}"
                    )
                
            self.logger.info(f"Scraping session info: {json.dumps(session_info, indent=2)}")
            self.logger.info(f"Completed create_outlet_scraping_session: {outlet}")
            return scraping_session
        except Exception as e:
            self.logger.error(f"Error in create_outlet_scraping_session: {outlet}: {e}")
            return None
    
    def _handle_completed_session(self,  session_info):
        """Handle a completed scraping session by saving, publishing event, and moving file."""
        try:
            # Save session data if storage service is available
            if self.storage_service:
                self.storage_service.save_scraping_session(session_info)
                
                # Get file path information
                file_name = session_info["data"]["results_staging_file_name"]
                local_path = os.path.join(self.config.storage.staging.local.scraping(), file_name)
                
                # Check if file exists before proceeding
                if os.path.exists(local_path):
                    # Publish event to RabbitMQ
                    if self.message_service and self.message_service.connection and self.message_service.connection.is_open:
                        bucket_name = self.config.digitalocean.spaces.buckets.main.name()
                        s3_path = f"{self.config.digitalocean.spaces.buckets.main.folders.scraping()}/{file_name}"
                        
                        self.message_service.publish_articles_scraped_event(
                            session_info,
                            bucket_name,
                            s3_path
                        )
                        self.logger.info(f"Published event for file: {file_name}")
                    
                    # Move file to Digital Ocean S3
                    if hasattr(self.storage_service, 'digital_ocean_handler'):
                        bucket = self.config.digitalocean.spaces.buckets.main.name()
                        folder = self.config.digitalocean.spaces.buckets.main.folders.scraping()
                        
                        # Use the enhanced upload_file method which supports both folder_path and s3_file_path
                        result = self.storage_service.digital_ocean_handler.upload_file(
                            local_path,
                            bucket,
                            os.path.basename(file_name),
                            folder_path=folder
                        )
                        
                        if result:
                            self.logger.info(f"Uploaded file to S3: {file_name}")
                        else:
                            self.logger.warning(f"Failed to upload file to S3: {file_name}")
                else:
                    self.logger.warning(f"File not found: {local_path}")
        except Exception as e:
            self.logger.error(f"Error handling completed session: {e}")
    
    def generate_outlets_scraping_sessions(self, outlets: List[OutletsSource]) -> Generator:
        """Scrape multiple outlets concurrently using a thread pool."""
        self.logger.info("Starting perform_concurrent_scraping")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                futures = {executor.submit(self.create_outlet_scraping_session, outlet): outlet for outlet in outlets}
                for future in concurrent.futures.as_completed(futures):
                    outlet = futures[future]
                    try:
                        result = future.result()
                        if result:
                            yield result
                    except Exception as e:
                        self.logger.error(f"Error processing outlet {outlet}: {e}")
            self.logger.info("Completed perform_concurrent_scraping")
        except Exception as e:
            self.logger.error(f"Error in perform_concurrent_scraping: {e}")
    
    def execute_scraping_process(self, limit=None, custom_outlet=None):
        """
        Execute the scraping process for outlets.
        
        Args:
            limit: Optional limit on number of outlets to scrape
            custom_outlet: Optional custom outlet definition (dict with name and url)
        
        Returns:
            List of scraping session results
        """
        self.logger.info("Starting execute_scraping_process")
        try:
            # Handle custom outlet case
            if custom_outlet:
                self.logger.info(f"Using custom outlet: {custom_outlet}")
                from inkbytes.models.outlets import OutletsSource
                outlets = [OutletsSource(**custom_outlet)]
            else:
                # Get outlets from service
                outlets = self.outlet_service.get_outlets(OutletsDataSource.REST_API)
                if not outlets:
                    self.logger.warning("No outlets found")
                    self.logger.info("Completed execute_scraping_process")
                    return []
                
                # Apply limit if specified
                if limit and isinstance(limit, int) and limit > 0:
                    self.logger.info(f"Limiting to {limit} outlets")
                    outlets = outlets[:limit]
                
            self.logger.info(f"Starting scraping process for {len(outlets)} outlets/sources")
            result = list(self.generate_outlets_scraping_sessions(outlets))
            self.logger.info("Completed execute_scraping_process")
            return result
        except Exception as e:
            self.logger.error(f"Error in execute_scraping_process: {e}")
            return []