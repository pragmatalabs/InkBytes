#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Storage Service for the Messor application.

This module provides file storage capabilities for scraping results,
including local file storage and DigitalOcean Spaces integration.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import json
import os
from typing import Dict, Any, List

from core.scraper import SessionSavingMode
from inkbytes.common.api.rest import RestClient
from inkbytes.common.files.csv_json_handler import clean_staging_db_files
from inkbytes.common.files.digital_ocean_spaces import DigitalOceanSpacesHandler

class StorageService:
    def __init__(self, config, logger, rest_client):
        self.config = config
        self.logger = logger
        self.rest_client = rest_client
        self.digital_ocean_handler = self._configure_digital_ocean()
        self.num_threads = config.get_thread_count()
        # This will be injected by Application
        self.message_service = None
    
    def _configure_digital_ocean(self) -> DigitalOceanSpacesHandler:
        """Configure the Digital Ocean Spaces handler."""
        return DigitalOceanSpacesHandler(
            self.config.digitalocean.access_id(),
            self.config.digitalocean.secret_key(),
            self.config.digitalocean.region_name(),
            self.config.digitalocean.endpoint_url()
        )
    
    def save_scraping_session(self, scraping_session):
        """Save scraping session data based on configured saving mode."""
        self.logger.info("Starting save_scraping_session")
        file_path = "scraping_session.json"
        
        try:
            # Extract filename from session if available. The articles live in
            # the `<ts>.<outlet>.db.json` staging file (StagingStore `_default`
            # format). Write the session SUMMARY to a sibling `.session.json`
            # so we do NOT clobber the staged articles — they are still needed
            # for per-article RabbitMQ publishing (see save_session_to_file),
            # cross-session dedup, and S3 archival.
            if isinstance(scraping_session, dict) and "data" in scraping_session:
                if "results_staging_file_name" in scraping_session["data"]:
                    file_name = scraping_session["data"]["results_staging_file_name"]
                    summary_name = file_name.replace(".db.json", ".session.json")
                    file_path = os.path.join(self.config.storage.staging.local.scraping(), summary_name)
            
            session_saving_mode = self.config.scraping.save_mode()
            
            result = False
            if session_saving_mode == SessionSavingMode.SAVE_TO_FILE.value:
                result = self.save_session_to_file(scraping_session, file_path)
            elif session_saving_mode == SessionSavingMode.SEND_TO_API.value:
                result = self.send_session_to_api(scraping_session, file_path)
            else:
                self.logger.error(f"Invalid session saving mode: {session_saving_mode}")
                result = self.save_session_to_file(scraping_session, file_path)
                
            self.logger.info("Completed save_scraping_session")
            return result
        except Exception as e:
            self.logger.error(f"Error in save_scraping_session: {e}")
            return self.save_session_to_file(scraping_session, file_path)

    def save_session_to_file(self, scraping_session, file_path):
        """Save the scraping session to a local file."""
        self.logger.info(f"Starting save_session_to_file: {file_path}")
        try:
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            with open(file_path, 'w') as file:
                if isinstance(scraping_session, dict):
                    json.dump(scraping_session, file)
                else:
                    # Handle non-dict objects by converting to string
                    file.write(str(scraping_session))

            self.logger.info(f"Session saved to file {file_path}.")

            # Publish per-article events now that articles are staged locally.
            # This fires in all save modes (local + S3), without requiring a
            # successful upload first — critical for dev where S3 is skipped.
            if isinstance(scraping_session, dict) and "data" in scraping_session:
                staging_file = scraping_session["data"].get("results_staging_file_name")
                if staging_file:
                    staging_path = os.path.join(
                        self.config.storage.staging.local.scraping(),
                        staging_file,
                    )
                    self._publish_articles_from_staging_file(
                        staging_path, session_id=staging_file
                    )

            self.logger.info(f"Completed save_session_to_file: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error in save_session_to_file: {file_path}: {e}")
            return False

    def _publish_articles_from_staging_file(
        self, staging_file_path: str, session_id: str, s3_key: str = ""
    ) -> int:
        """Read articles from a staging file and emit one RabbitMQ event per article.

        Returns the count of successfully published events.
        Only runs if message_service is connected and has publish_article_event.
        """
        if not (
            self.message_service
            and hasattr(self.message_service, "publish_article_event")
            and self.message_service.connection
            and self.message_service.connection.is_open
        ):
            return 0

        if not os.path.exists(staging_file_path):
            self.logger.warning(f"Staging file not found for event publish: {staging_file_path}")
            return 0

        try:
            with open(staging_file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as e:
            self.logger.error(f"Error reading staging file {staging_file_path}: {e}")
            return 0

        # StagingStore format: {"_default": {"1": {...article...}, ...}}
        if isinstance(data, dict) and "_default" in data:
            articles = list(data["_default"].values())
        elif isinstance(data, list):
            articles = data
        else:
            self.logger.warning(f"Unexpected staging file format in {staging_file_path}")
            return 0

        published = 0
        for article_dict in articles:
            if isinstance(article_dict, dict):
                if self.message_service.publish_article_event(article_dict, session_id, s3_key):
                    published += 1

        self.logger.info(
            "Published %d/%d article events from %s", published, len(articles), staging_file_path
        )
        return published

    def send_session_to_api(self, scraping_session, file_path=None):
        """Send the scraping session to the API."""
        self.logger.info("Starting send_session_to_api")
        try:
            post_headers = {
                "Authorization": f'Bearer {self.config.platform_api.token()}',
                'Content-Type': self.config.platform_api.post_headers.content_type(),
            }
            response = self.rest_client.send_api_request(
                "POST",
                self.config.platform_api.endpoints.session(),
                data=scraping_session,
                headers=post_headers
            )
            if response is not None:
                self.logger.info("Successfully sent session to API.")
                self._send_articles_batch_to_api(scraping_session, file_path, post_headers)
                self.logger.info("Completed send_session_to_api")
                return True
            else:
                self.logger.error("API request failed, falling back to save session locally.")
                self.logger.info("Completed send_session_to_api")
                return self.save_session_to_file(scraping_session, "scraping_session.json")
        except Exception as e:
            self.logger.error(f"Error in send_session_to_api: {e}")
            return self.save_session_to_file(scraping_session, "scraping_session.json")

    def _resolve_articles_batch_endpoint(self) -> str:
        """Resolve articles batch endpoint from config with a safe fallback."""
        default_endpoint = "articles/batch"

        try:
            endpoints = self.config.platform_api.endpoints
            endpoint_getter = getattr(endpoints, "articles_batch", None)
            if callable(endpoint_getter):
                endpoint = endpoint_getter()
                if isinstance(endpoint, str) and endpoint.strip():
                    return endpoint.strip("/")
        except Exception as e:
            self.logger.warning(f"Unable to resolve articles batch endpoint from config: {e}")

        return default_endpoint

    def _load_articles_from_staging_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load article payloads from the JSON staging file format."""
        if not file_path or not os.path.exists(file_path):
            self.logger.warning(f"Articles staging file not found: {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except Exception as e:
            self.logger.error(f"Unable to read articles staging file {file_path}: {e}")
            return []

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            default_bucket = payload.get("_default")
            if isinstance(default_bucket, dict):
                return [item for item in default_bucket.values() if isinstance(item, dict)]

            # Generic dict fallback if shape is { "1": {article...}, ... }.
            if all(isinstance(item, dict) for item in payload.values()):
                return [item for item in payload.values() if isinstance(item, dict)]

        return []

    def _send_articles_batch_to_api(self, scraping_session, file_path: str, headers: Dict[str, str]) -> bool:
        """Send scraped article records to the platform API."""
        articles = self._load_articles_from_staging_file(file_path)
        if not articles:
            self.logger.warning("No articles found in staging file to send to API.")
            return False

        run_code = None
        if isinstance(scraping_session, dict):
            run_code = scraping_session.get("data", {}).get("results_staging_file_name")

        endpoint = self._resolve_articles_batch_endpoint()
        payload = {
            "data": {
                "run_code": run_code,
                "articles": articles,
            }
        }

        response = self.rest_client.send_api_request(
            "POST",
            endpoint,
            data=payload,
            headers=headers
        )

        if response is None:
            self.logger.error("Failed to send articles batch to API.")
            return False

        summary = response.get("data", {}) if isinstance(response, dict) else {}
        inserted = summary.get("inserted")
        skipped = summary.get("skipped")
        received = summary.get("received")
        self.logger.info(
            f"Articles batch sent to API (received={received}, inserted={inserted}, skipped={skipped})."
        )
        return True
    
    def upload_file_to_s3(self, local_file_path, bucket=None, folder=None):
        """Upload a single file to S3 and publish an event."""
        self.logger.info(f"Starting upload_file_to_s3: {local_file_path}")
        try:
            if not os.path.exists(local_file_path):
                self.logger.error(f"File not found: {local_file_path}")
                return False
                
            bucket_name = bucket or self.config.digitalocean.spaces.buckets.main.name()
            folder_path = folder or self.config.digitalocean.spaces.buckets.main.folders.scraping()
            file_name = os.path.basename(local_file_path)
            
            # Upload file
            result = self.digital_ocean_handler.upload_file(
                local_file_path,
                bucket_name,
                file_name,
                folder_path=folder_path
            )
            
            if result:
                self.logger.info(f"Successfully uploaded {file_name} to {bucket_name}/{folder_path}")
                
                # S3 upload is archival only. RabbitMQ events were already
                # published in save_session_to_file — do not re-publish here.
                s3_path = f"{folder_path}/{file_name}"
                self.logger.info("S3 archived: %s → %s", file_name, s3_path)
                        
                return True
            else:
                self.logger.error(f"Failed to upload {file_name}")
                return False
        except Exception as e:
            self.logger.error(f"Error in upload_file_to_s3: {e}")
            return False
    
    def execute_files_move(self):
        """Upload scraped files to Digital Ocean Spaces and publish events."""
        self.logger.info("Starting execute_files_move")
        try:
            # Get list of files before uploading
            local_path = self.config.storage.staging.local.scraping()
            bucket_name = self.config.digitalocean.spaces.buckets.main.name()
            folder = self.config.digitalocean.spaces.buckets.main.folders.scraping()
            
            # Use the enhanced upload_directory method
            result = self.digital_ocean_handler.upload_directory(
                local_path,
                bucket_name,
                s3_prefix=folder,
                extension='.db.json',
                num_of_threads=self.num_threads
            )
            
            if result:
                self.logger.info("Successfully uploaded files to Digital Ocean S3")
                
                # S3 upload is archival only. RabbitMQ events were already
                # published per-article in save_session_to_file.
                self.logger.info("S3 batch archive complete: %s → %s", local_path, folder)
            else:
                self.logger.warning("Some files failed to upload to Digital Ocean S3")
                
            self.logger.info("Completed execute_files_move")
        except Exception as e:
            self.logger.error(f"Error in execute_files_move: {e}")

    def execute_files_clean(self):
        """Clean up staging files after successful processing."""
        self.logger.info("Starting execute_files_clean")
        try:
            clean_staging_db_files(
                self.config.storage.staging.local.scraping(),
                self.config.storage.staging.local.history()
            )
            self.logger.info("Completed execute_files_clean")
        except Exception as e:
            self.logger.error(f"Error in execute_files_clean: {e}")
