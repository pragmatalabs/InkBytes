#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Message Service for the Messor application.

This module provides RabbitMQ integration for event-driven communication
between Messor and other components of the InkBytes ecosystem.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import json
import os
import threading
import time
import pika
import ssl
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pika.exceptions import AMQPConnectionError, AMQPChannelError

class MessageService:
    """Service for handling RabbitMQ messaging operations."""
    
    def __init__(self, config, logger):
        """Initialize the MessageService."""
        self.config = config
        self.logger = logger
        self.connection = None
        self.channel = None
        # Store queue names with reasonable defaults.
        # Messor only owns articles-scraped. Curator owns topics-extracted
        # (and everything downstream). See ADR-0005.
        self._articles_scraped_queue = "articles-scraped"
        self._article_exchange = "messor"  # topic exchange; Curator consumes from here
        self._last_heartbeat = time.time()
        self._heartbeat_interval = 30  # Check connection every 30 seconds

    def _check_connection_health(self) -> bool:
        """
        Check if the connection is healthy and the heartbeat interval has passed.
        Returns True if the connection was checked and is healthy.
        """
        current_time = time.time()
        
        # Only check the connection if the heartbeat interval has passed
        if current_time - self._last_heartbeat < self._heartbeat_interval:
            return True
        
        self._last_heartbeat = current_time
        self.logger.info("Performing RabbitMQ connection health check")
        
        try:
            # If no connection exists or it's closed, reconnect
            if not self.connection or not self.connection.is_open:
                self.logger.warning("Connection is closed, attempting to reconnect")
                return self.connect()
                
            # If connection exists but channel is closed, create a new channel
            if not self.channel or not self.channel.is_open:
                self.logger.warning("Channel is closed, creating new channel")
                self.channel = self.connection.channel()
                
                # Re-declare queues to ensure they exist (Messor only owns
                # articles-scraped; topics-extracted is Curator's — ADR-0005)
                self.channel.queue_declare(
                    queue=self._articles_scraped_queue,
                    durable=True
                )
            
            # Connection is healthy
            return True
        except Exception as e:
            self.logger.error(f"Error checking connection health: {e}")
            # Try to reconnect completely
            return self.connect()

    def start_health_check_thread(self):
        """Start a thread to periodically check the connection health."""
        def health_check_worker():
            while True:
                try:
                    self._check_connection_health()
                    time.sleep(self._heartbeat_interval)
                except Exception as e:
                    self.logger.error(f"Error in health check thread: {e}")
                    time.sleep(5)  # Sleep briefly to avoid spinning if there's an error
        
        health_thread = threading.Thread(target=health_check_worker)
        health_thread.daemon = True  # Thread will exit when the main thread exits
        health_thread.start()
        self.logger.info("Started RabbitMQ connection health check thread")
        
    def connect(self) -> bool:
        """Establish connection to RabbitMQ server."""
        self.logger.info("Connecting to RabbitMQ")
        try:
            # Get connection parameters — env vars take precedence so Docker
            # containers work without a mounted env.local.yaml. Fallback to
            # YAML for local dev (env.local.yaml has the real values).
            host = os.getenv("RABBITMQ_HOST") or self.config.rabbitmq.host()
            port = int(os.getenv("RABBITMQ_PORT") or self.config.rabbitmq.port())

            # Use default virtual_host if not in config
            try:
                virtual_host = self.config.rabbitmq.virtual_host()
            except AttributeError:
                virtual_host = "/"
                self.logger.info("Virtual host not specified, using default '/'")

            username = os.getenv("RABBITMQ_USER") or self.config.rabbitmq.username()
            password = os.getenv("RABBITMQ_PASS") or self.config.rabbitmq.password()
            
            # Use default for heartbeat if not in config
            try:
                heartbeat = int(self.config.rabbitmq.heartbeat())
            except (AttributeError, ValueError):
                heartbeat = 600
                self.logger.info("Heartbeat not specified or invalid, using default 600")
            
            # Set default connection_attempts
            try:
                connection_attempts = 3  # Default value
                if hasattr(self.config.rabbitmq, 'connection_attempts'):
                    connection_attempts = int(self.config.rabbitmq.connection_attempts())
            except (AttributeError, ValueError):
                self.logger.info(f"Connection attempts not specified or invalid, using default {connection_attempts}")
            
            # Create connection parameters
            parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=virtual_host,
                credentials=pika.PlainCredentials(username, password),
                heartbeat=heartbeat,
                connection_attempts=connection_attempts
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Get queue names from config
            try:
                articles_scraped_queue = self.config.rabbitmq.queues.articles_scraped()
                self._articles_scraped_queue = articles_scraped_queue
            except AttributeError:
                self.logger.info(f"Using default articles_scraped queue name: {self._articles_scraped_queue}")

            # Set message TTL (24 hours)
            queue_arguments = {
                'x-message-ttl': 86400000  # 24 hours in milliseconds
            }

            # Declare Messor's only output queue. topics-extracted lives in
            # Curator now (ADR-0005); Messor neither produces nor consumes it.
            self.channel.queue_declare(
                queue=self._articles_scraped_queue,
                durable=True,
                arguments=queue_arguments
            )

            # Declare the topic exchange Curator subscribes to.
            # Routing key: event.article.scraped (one message per article).
            try:
                self._article_exchange = self.config.rabbitmq.exchanges.scraping.name()
            except AttributeError:
                pass  # keep default "messor"
            self.channel.exchange_declare(
                exchange=self._article_exchange,
                exchange_type='topic',
                durable=True,
            )

            self.logger.info("Successfully connected to RabbitMQ")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
            
    def close(self):
        """Close the RabbitMQ connection."""
        if self.connection and self.connection.is_open:
            self.logger.info("Closing RabbitMQ connection")
            try:
                if self.channel and self.channel.is_open:
                    self.channel.close()
                self.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing RabbitMQ connection: {e}")
                    
    def publish_message(self, queue: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to a RabbitMQ queue.
        Will attempt to reopen the channel if it's closed.
        """
        self.logger.info(f"Publishing message to queue: {queue}")
        try:
            # Check connection health
            if not self._check_connection_health():
                self.logger.error("Failed to establish healthy connection to RabbitMQ")
                return False
            
            # Publish the message
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )
            self.logger.info(f"Message published to queue: {queue}")
            return True
        except Exception as e:
            self.logger.error(f"Error publishing message to {queue}: {e}")
            
            # Try reconnecting once
            if self.connect():
                try:
                    self.channel.basic_publish(
                        exchange='',
                        routing_key=queue,
                        body=json.dumps(message),
                        properties=pika.BasicProperties(
                            delivery_mode=2,
                            content_type='application/json'
                        )
                    )
                    self.logger.info(f"Message published to queue after reconnection: {queue}")
                    return True
                except Exception as e2:
                    self.logger.error(f"Error publishing message after reconnection: {e2}")
                    return False
            return False
        
    def publish_articles_scraped_event(self, scraping_session, bucket: str, file_path: str) -> bool:
        """Publish an event indicating articles have been scraped and uploaded to S3."""
        import os
        
        # Extract outlet name from file path if possible
        outlet_name = "unknown"
        session_id = ""
        
        try:
            # Try to get outlet from file name
            file_name = os.path.basename(file_path)
            parts = file_name.split('.')
            if len(parts) >= 3:
                outlet_name = parts[1]  # Assuming format: timestamp.outlet.db.json
                session_id = file_name
        except Exception as e:
            self.logger.warning(f"Error extracting outlet from filename: {e}")
            
        # Get data from scraping_session if available
        timestamp = datetime.utcnow().isoformat()
        article_count = 0
        
        if isinstance(scraping_session, dict) and "data" in scraping_session:
            data = scraping_session.get("data", {})
            if data.get("end_time"):
                timestamp = data.get("end_time")
            if "successful_articles" in data:
                article_count = data.get("successful_articles", 0)
            if "outlet" in data and data["outlet"]:
                outlet_name = data["outlet"]
            elif "outlet_name" in data and data["outlet_name"]:
                outlet_name = data["outlet_name"]
            if "results_staging_file_name" in data and data["results_staging_file_name"]:
                session_id = data["results_staging_file_name"]
        
        # Log the extracted data
        self.logger.info(f"Publishing event for outlet: {outlet_name}, "
                        f"articles: {article_count}, "
                        f"session: {session_id}, "
                        f"file: {file_path}")
        
        message = {
            "event_type": "articles_scraped",
            "timestamp": timestamp,
            "data": {
                "bucket": bucket,
                "file_path": file_path,
                "article_count": article_count,
                "outlet": outlet_name,
                "session_id": session_id
            }
        }
        
        return self.publish_message(self._articles_scraped_queue, message)

    def publish_article_event(self, article_dict: Dict[str, Any], session_id: str, spaces_key: str = "",
                              priority: int = 0) -> bool:
        """Publish one inkbytes.article.v1 event per article to the messor topic exchange.

        Curator's --consume mode subscribes to this exchange on routing key
        event.article.scraped.  Maps Messor's Article fields to ArticleV1.

        ``priority`` (pulse lane, ADR-0017): AMQP message priority — 9 for
        pulse runs so Curator's priority queue processes them first.  Transport
        metadata only; the inkbytes.article.v1 payload is unchanged.
        """
        outlet_name = article_dict.get("article_source") or "unknown"

        def _safe_list(value) -> list:
            if isinstance(value, list):
                return value
            return []

        # Truncate body to ~8 000 chars — Curator only uses text[:4000] for
        # embedding and the prompt. Capping here keeps RabbitMQ messages small
        # (~30–50 KB vs potentially 200 KB for long-form articles).
        body_text = (article_dict.get("text") or "")[:8000]

        payload = {
            "schema": "inkbytes.article.v1",
            "session_id": session_id,
            "spaces_key": spaces_key,
            "article": {
                "id": article_dict.get("id", ""),
                "outlet": {
                    "id": outlet_name.lower().replace(" ", "-"),
                    "name": outlet_name,
                },
                "url": article_dict.get("article_url", ""),
                "canonical_url": article_dict.get("source_url") or article_dict.get("article_url") or "",
                "title": article_dict.get("title", ""),
                "text": body_text,
                "language": article_dict.get("language", "en"),
                "published_at": article_dict.get("publish_date"),
                "scraped_at": article_dict.get("fetched_on") or datetime.utcnow().isoformat(),
                "word_count": len((article_dict.get("text") or "").split()),  # original length
                "authors": _safe_list(article_dict.get("authors")),
                "meta_categories": _safe_list(article_dict.get("meta_categories")),
                "category": article_dict.get("category"),
                "keywords": _safe_list(article_dict.get("keywords")),
                "metadata": article_dict.get("metadata") or {},
                # Phase 1 media — passive extraction by Messor; Curator stores as-is
                "lead_image": article_dict.get("lead_image"),
                "video_url":  article_dict.get("video_url"),
            },
        }

        if not self._check_connection_health():
            self.logger.error("RabbitMQ unavailable; skipping article event publish")
            return False

        body = json.dumps(payload, default=str)
        props = pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json',
            # Pulse-lane messages (ADR-0017) carry priority 9 so Curator's
            # x-max-priority queue (Curator ADR-0024) delivers them first.
            priority=priority if priority else None,
        )
        try:
            self.channel.basic_publish(
                exchange=self._article_exchange,
                routing_key="event.article.scraped",
                body=body,
                properties=props,
            )
            self.logger.info("Published article event: %s @ %s", article_dict.get("id"), outlet_name)
            return True
        except Exception as exc:
            self.logger.error("Error publishing article event: %s", exc)
            if self.connect():
                try:
                    self.channel.basic_publish(
                        exchange=self._article_exchange,
                        routing_key="event.article.scraped",
                        body=body,
                        properties=props,
                    )
                    return True
                except Exception as exc2:
                    self.logger.error("Error publishing article event after reconnect: %s", exc2)
            return False

    def publish_scrape_session_completed(self, session: Dict[str, Any]) -> bool:
        """Publish one run-level `scrape.session.completed` event (B12.1 / ADR-0006).

        Messor stays Postgres-free: it EMITS the already-computed per-session +
        per-outlet stats on the `messor` topic exchange (routing key
        `event.scrape.session.completed`); Curator consumes and upserts
        `public.scrape_sessions`. Messor never opens a DB connection.

        `session` is the run-level dict the harvester accumulates across outlets
        — matching the shape `GET /api/scrapesessions` returns (session_id,
        start/end times, total/successful/failed, duplicates, success_rate,
        duration, outlets[], total_outlets).

        Best-effort: returns False (and logs) if RabbitMQ is unavailable. A lost
        run summary is non-fatal history; it must never abort a harvest.
        """
        payload = {
            "schema": "inkbytes.scrape_session.v1",
            "event_type": "scrape.session.completed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "session_id":          session.get("session_id"),
                "started_at":          session.get("started_at"),
                "ended_at":            session.get("ended_at"),
                "total_articles":      session.get("total_articles", 0),
                "successful_articles": session.get("successful_articles", 0),
                "failed_articles":     session.get("failed_articles", 0),
                "duplicates_total":    session.get("duplicates_total", 0),
                "success_rate":        session.get("success_rate", 0.0),
                "duration":            session.get("duration"),
                "outlets":             session.get("outlets", []),
                "total_outlets":       session.get("total_outlets", 0),
                # Lane tag (Messor ADR-0017): 'pulse' = 5-min RSS tick, 'cycle'
                # = full 2-hour sweep. Must be forwarded here — this payload is
                # rebuilt field-by-field, so a missing key silently defaults the
                # session to 'cycle' in Curator (the Backoffice pulse filter was
                # empty because every pulse session arrived untagged).
                "lane":                session.get("lane", "cycle"),
            },
        }

        if not self._check_connection_health():
            self.logger.error(
                "RabbitMQ unavailable; skipping scrape.session.completed publish"
            )
            return False

        body = json.dumps(payload, default=str)
        props = pika.BasicProperties(delivery_mode=2, content_type='application/json')
        try:
            self.channel.basic_publish(
                exchange=self._article_exchange,
                routing_key="event.scrape.session.completed",
                body=body,
                properties=props,
            )
            self.logger.info(
                "Published scrape.session.completed: %s (%d outlets, %d articles)",
                payload["data"]["session_id"],
                payload["data"]["total_outlets"],
                payload["data"]["total_articles"],
            )
            return True
        except Exception as exc:
            self.logger.error("Error publishing scrape.session.completed: %s", exc)
            if self.connect():
                try:
                    self.channel.basic_publish(
                        exchange=self._article_exchange,
                        routing_key="event.scrape.session.completed",
                        body=body,
                        properties=props,
                    )
                    return True
                except Exception as exc2:
                    self.logger.error(
                        "Error publishing scrape.session.completed after reconnect: %s",
                        exc2,
                    )
            return False

    # Note: publish_topics_extracted_event() lived here in pre-ADR-0005
    # Messor. Removed — that's Curator's responsibility now.