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
import random
import time
from typing import List, Generator, Dict, Any, Optional
from datetime import datetime, timezone
from core.scraper import scrape_outlet
from core.staging_store import prune_old_staging_files
from inkbytes.models.outlets import OutletsDataSource, OutletsSource

class ScraperService:
    def __init__(self, config, logger, outlet_service, storage_service=None, message_service=None):
        self.config = config
        self.logger = logger
        self.outlet_service = outlet_service
        self.storage_service = storage_service
        self.message_service = message_service
        # max_threads controls outlet-level parallelism (how many outlets run
        # concurrently).  Article processing is now sequential within each outlet
        # thread (ADR-0011) so there is no inner pool — num_threads is the only
        # concurrency knob.
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
                    # If the scrape produced 0 new articles StagingStore never
                    # writes to disk — the missing file is expected, not an error.
                    successful = (session_info.get("data") or {}).get("successful_articles", 0)
                    if successful > 0:
                        # Articles were staged but the file disappeared — real problem.
                        self.logger.warning(f"File not found (expected {successful} articles): {local_path}")
                    else:
                        self.logger.debug(f"No articles staged this run, skipping upload: {file_name}")
        except Exception as e:
            self.logger.error(f"Error handling completed session: {e}")
    
    def _outlet_stats_from_session(self, scraping_session) -> Optional[Dict[str, Any]]:
        """Pull Messor's already-computed per-outlet stats off a session.

        Returns a per-outlet dict matching the `/api/scrapesessions` outlets[]
        shape (plus the dedup breakdown Messor owns), or None if the session has
        no usable data. Pure read of values Messor already computed — no NLP, no
        new dedup logic (ADR-0005).
        """
        try:
            info = scraping_session.to_json()
        except Exception:
            return None
        data = (info or {}).get("data") or {}
        if not data:
            return None

        outlet_name = data.get("outlet") or data.get("outlet_name") or "unknown"
        slug = str(outlet_name).lower().replace(" ", "-")
        successful = int(data.get("successful_articles") or 0)
        failed = int(data.get("failed_articles") or 0)
        total = int(data.get("total_articles") or (successful + failed))
        dups = int(data.get("total_duplicates")
                   or (int(data.get("duplicates_current_batch") or 0)
                       + int(data.get("duplicates_previous_scrapes") or 0)))
        return {
            "name":        outlet_name,
            "slug":        slug,
            "articles":    successful,   # matches /api/scrapesessions (staged = successes)
            "successful":  successful,
            "failed":      failed,
            "total":       total,
            "duplicates":  dups,
        }

    def _emit_session_completed(self, run_id: str, started_at, ended_at,
                                duration: float, per_outlet: List[Dict[str, Any]]) -> None:
        """Aggregate per-outlet stats into a run-level summary and emit it.

        Emit-only (ADR-0006): Curator consumes and persists. Best-effort — a
        publish failure is logged and never aborts the harvest.
        """
        if not self.message_service:
            return
        total_articles = sum(o["total"] for o in per_outlet)
        successful = sum(o["successful"] for o in per_outlet)
        failed = sum(o["failed"] for o in per_outlet)
        duplicates = sum(o["duplicates"] for o in per_outlet)
        attempted = successful + failed
        success_rate = (successful / attempted) if attempted > 0 else (
            1.0 if successful > 0 else 0.0)

        # Strip the internal-only `total` key from the published per-outlet rows.
        outlets_payload = [
            {k: v for k, v in o.items() if k != "total"} for o in per_outlet
        ]

        session = {
            "session_id":          run_id,
            "started_at":          started_at.isoformat(),
            "ended_at":            ended_at.isoformat(),
            "duration":            round(duration, 2),
            "total_articles":      total_articles,
            "successful_articles": successful,
            "failed_articles":     failed,
            "duplicates_total":    duplicates,
            "success_rate":        round(success_rate, 4),
            "outlets":             outlets_payload,
            "total_outlets":       len(per_outlet),
        }
        try:
            self.message_service.publish_scrape_session_completed(session)
        except Exception as e:
            self.logger.error(f"Failed to emit scrape.session.completed: {e}")

    # Hard ceiling per outlet — newspaper3k can hang on homepage crawls and
    # download_categories(), pinning threads for hours.  5 min is generous
    # (typical outlets finish in 30-90 s); this kills the wait, not the thread,
    # but limits damage and lets the rest of the pool continue.
    OUTLET_TIMEOUT_SECONDS = 300

    def generate_outlets_scraping_sessions(self, outlets: List[OutletsSource]) -> Generator:
        """Scrape multiple outlets concurrently using a thread pool."""
        self.logger.info("Starting perform_concurrent_scraping")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                futures = {executor.submit(self.create_outlet_scraping_session, outlet): outlet for outlet in outlets}
                for future in concurrent.futures.as_completed(futures, timeout=self.OUTLET_TIMEOUT_SECONDS * len(outlets)):
                    outlet = futures[future]
                    try:
                        result = future.result(timeout=self.OUTLET_TIMEOUT_SECONDS)
                        if result:
                            yield result
                    except concurrent.futures.TimeoutError:
                        self.logger.error(
                            f"Outlet {getattr(outlet, 'name', outlet)} timed out after "
                            f"{self.OUTLET_TIMEOUT_SECONDS}s — skipping"
                        )
                    except Exception as e:
                        self.logger.error(f"Error processing outlet {outlet}: {e}")
            self.logger.info("Completed perform_concurrent_scraping")
        except concurrent.futures.TimeoutError:
            self.logger.error("Overall scraping pool timed out — some outlets skipped")
        except Exception as e:
            self.logger.error(f"Error in perform_concurrent_scraping: {e}")
    
    @staticmethod
    def _outlet_identifiers(outlet) -> set:
        """Collect every slug-like identifier an outlet can be matched on.

        The catalogue's `id` is a string slug (e.g. "bbc"). After loading,
        OutletsSource carries that slug in `name` (and possibly `slug`/`id`);
        we accept any of them, case-insensitively, so the Backoffice's
        `public.outlets.id` matches regardless of which field it landed in.
        """
        ids = set()
        for value in (getattr(outlet, 'id', None),
                      getattr(outlet, 'name', None),
                      getattr(outlet, 'slug', None)):
            if value is None:
                continue
            text = str(value).strip().lower()
            if text:
                ids.add(text)
        return ids

    def _filter_outlets_by_slugs(self, outlets, slugs):
        """Restrict the loaded catalogue to outlets whose id/name/slug matches.

        Unknown slugs are ignored defensively (logged, never fatal). Matching is
        case-insensitive against the outlet's id, name, and slug. Returns the
        filtered list preserving catalogue order.
        """
        wanted = {str(s).strip().lower() for s in slugs if str(s).strip()}
        if not wanted:
            return outlets

        filtered = [o for o in outlets if self._outlet_identifiers(o) & wanted]

        matched = set()
        for o in filtered:
            matched |= (self._outlet_identifiers(o) & wanted)
        unknown = wanted - matched
        if unknown:
            self.logger.warning(
                f"Ignoring unknown outlet slug(s): {sorted(unknown)}"
            )
        self.logger.info(
            f"Outlet subset filter: {len(filtered)} of {len(outlets)} "
            f"outlets matched {sorted(wanted)}"
        )
        return filtered

    def execute_scraping_process(self, limit=None, custom_outlet=None, slugs=None):
        """
        Execute the scraping process for outlets.

        Args:
            limit: Optional limit on number of outlets to scrape
            custom_outlet: Optional custom outlet definition (dict with name and url)
            slugs: Optional list of catalogue outlet slugs to restrict the harvest
                to. Unknown slugs are ignored. Ignored when custom_outlet is set.

        Returns:
            List of scraping session results
        """
        self.logger.info("Starting execute_scraping_process")
        try:
            # Prune staging files older than 30 days before each cycle so disk
            # usage stays bounded.  Safe to call even if scrapes_dir doesn't
            # exist yet (ADR-0012).
            scrapes_dir = self.config.storage.staging.local.scraping()
            prune_old_staging_files(scrapes_dir)

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

                # Restrict to the requested subset of outlets, if any. Applied
                # before --limit so the limit caps the chosen subset, not the
                # full catalogue.
                if slugs:
                    outlets = self._filter_outlets_by_slugs(outlets, slugs)
                    if not outlets:
                        self.logger.warning(
                            "No outlets matched the requested subset; nothing to scrape"
                        )
                        self.logger.info("Completed execute_scraping_process")
                        return []

                # Apply limit if specified
                if limit and isinstance(limit, int) and limit > 0:
                    self.logger.info(f"Limiting to {limit} outlets")
                    outlets = outlets[:limit]
                
            # Shuffle so the same outlets don't always land in the first
            # concurrent batch (alphabetical = acento+aljazeera+apnews+clarin
            # every time → rate-limited together every cycle).
            random.shuffle(outlets)
            self.logger.info(f"Starting scraping process for {len(outlets)} outlets/sources")
            run_started = datetime.now(timezone.utc)
            t0 = time.time()

            result = []

            # Emit one session per outlet as soon as it completes so Curator
            # and the Backoffice update in real-time instead of waiting for the
            # entire 23-outlet sweep to finish.
            for scraping_session in self.generate_outlets_scraping_sessions(outlets):
                result.append(scraping_session)
                outlet_stats = self._outlet_stats_from_session(scraping_session)
                if not outlet_stats:
                    continue
                try:
                    info = (scraping_session.to_json() or {}).get("data") or {}
                    # Parse outlet-level start / end times from the session.
                    start_str = info.get("start_time")
                    end_str   = info.get("end_time")
                    outlet_start = (
                        datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
                        if start_str else run_started
                    )
                    outlet_end = (
                        datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
                        if end_str else datetime.now(timezone.utc)
                    )
                    outlet_duration = float(
                        info.get("duration")
                        or (outlet_end - outlet_start).total_seconds()
                    )
                    # Unique session id per outlet: session-<ts>-<slug>
                    slug = outlet_stats.get("slug", "unknown")
                    outlet_session_id = f"session-{int(outlet_start.timestamp())}-{slug}"
                    self._emit_session_completed(
                        outlet_session_id, outlet_start, outlet_end,
                        outlet_duration, [outlet_stats],
                    )
                    self.logger.info(
                        f"Session emitted for {slug}: {outlet_stats.get('successful', 0)} new articles"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to emit per-outlet session: {e}")

            self.logger.info("Completed execute_scraping_process")
            return result
        except Exception as e:
            self.logger.error(f"Error in execute_scraping_process: {e}")
            return []