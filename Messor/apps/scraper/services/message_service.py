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
        # Store queue names with reasonable defaults
        self._articles_scraped_queue = "articles-scraped"
        self._topics_extracted_queue = "topics-extracted"
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
                
                # Re-declare queues to ensure they exist
                self.channel.queue_declare(
                    queue=self._articles_scraped_queue,
                    durable=True
                )
                self.channel.queue_declare(
                    queue=self._topics_extracted_queue,
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
            # Get connection parameters from config
            host = self.config.rabbitmq.host()
            port = int(self.config.rabbitmq.port())
            
            # Use default virtual_host if not in config
            try:
                virtual_host = self.config.rabbitmq.virtual_host()
            except AttributeError:
                virtual_host = "/"
                self.logger.info("Virtual host not specified, using default '/'")
            
            username = self.config.rabbitmq.username()
            password = self.config.rabbitmq.password()
            
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
            
            try:
                topics_extracted_queue = self.config.rabbitmq.queues.topics_extracted()
                self._topics_extracted_queue = topics_extracted_queue
            except AttributeError:
                self.logger.info(f"Using default topics_extracted queue name: {self._topics_extracted_queue}")
            
            # Set message TTL (24 hours)
            queue_arguments = {
                'x-message-ttl': 86400000  # 24 hours in milliseconds
            }
            
            # Declare queues with TTL
            self.channel.queue_declare(
                queue=self._articles_scraped_queue,
                durable=True,
                arguments=queue_arguments
            )
            
            self.channel.queue_declare(
                queue=self._topics_extracted_queue,
                durable=True,
                arguments=queue_arguments
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
        
    def publish_topics_extracted_event(self, file_info: Dict[str, Any]) -> bool:
        """Publish an event indicating topics have been extracted from articles."""
        message = {
            "event_type": "topics_extracted",
            "timestamp": file_info.get("processed_time", datetime.utcnow().isoformat()),
            "data": {
                "bucket": file_info.get("bucket"),
                "input_file_path": file_info.get("input_file_path"),
                "output_file_path": file_info.get("output_file_path"),
                "article_count": file_info.get("article_count", 0),
                "topic_count": file_info.get("topic_count", 0)
            }
        }
        
        return self.publish_message(self._topics_extracted_queue, message)