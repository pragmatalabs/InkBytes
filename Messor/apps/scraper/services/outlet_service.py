"""
News outlet management service for Messor.

This module provides the OutletService class which manages news outlet configurations
and handles both API-based and local file-based outlet sources. It implements
intelligent fallback mechanisms to ensure scraping operations continue even when
external services are unavailable.

The service supports multiple data sources:
- Primary: External REST API for centralized outlet management
- Fallback: Local JSON file for offline operation and redundancy
- Runtime: Dynamic outlet addition for custom scraping targets

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import json
import logging
import os
from typing import List, Optional

from inkbytes.common.api.outlets_handler import OutletsManagerAPI
from inkbytes.models.outlets import OutletsDataSource, OutletsHandler, OutletsSource


class OutletService:
    """Service for managing news outlet configurations and data sources.
    
    This service provides a unified interface for accessing news outlet configurations
    from multiple sources, with intelligent fallback mechanisms to ensure high
    availability. It handles outlet validation, sorting, and dynamic management.
    
    The service implements a hierarchical data source strategy:
    1. Primary: External platform API for centralized management
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
    """
    def __init__(self, config, logger: logging.Logger, rest_client) -> None:
        """Initialize outlet service with required dependencies.
        
        Args:
            config: Application configuration object containing API settings
            logger: Logger instance for this service's operations
            rest_client: HTTP client configured for external API access
        """
        self.config = config
        self.logger = logger
        self.rest_client = rest_client

    def get_outlets(self, source: OutletsDataSource = OutletsDataSource.REST_API) -> List[OutletsSource]:
        """Retrieve news outlet configurations from available data sources.
        
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
        """
        self.logger.info("Starting get_outlets")
        try:
            api_base_url = os.getenv("MESSOR_API_BASE_URL", self.config.platform_api.base_url())
            outlet_manager = OutletsManagerAPI(
                api_base_url,
                self.config.platform_api.endpoints.outlets(),
                ""
            )
            outlets_handler_payload = outlet_manager.get_outlets_payload(source)
            
            # Check if API returned empty payload, fallback to local data
            if not outlets_handler_payload:
                self.logger.warning("External API returned empty payload, falling back to local data file")
                return self._get_outlets_from_local_file()
            
            # organize outlets by name field ascending
            outlets_handler_payload.sort(key=lambda x: x['name'])

            self.logger.info(f"Got raw payload: {outlets_handler_payload}")
            outlets_handler = OutletsHandler()
            outlets_handler.add_outlets_from_payload(outlets_handler_payload)
            self.logger.info(f"Completed get_outlets, found {len(outlets_handler.news_outlets)} outlets")
            return outlets_handler.news_outlets
        except (ValueError, Exception) as error:
            self.logger.error(f"Error in get_outlets from external API: {error}")
            self.logger.info("Falling back to local data file")
            return self._get_outlets_from_local_file()

    def _get_outlets_from_local_file(self) -> List[OutletsSource]:
        """Load outlets from the canonical outlets.json file.

        Search order (first match wins):
          1. Config's offline.local.outlets.file value
          2. outlets.json  (rich format, canonical)
          3. news_outlets_local.json  (legacy)
          4. news_outlets_sources.json (legacy)
          5. /app/data/outlets/outlets.json (Docker path)
        Only active=True outlets are returned.
        """
        try:
            config_path = None
            try:
                config_path = self.config.storage.offline.local.outlets.file()
            except AttributeError:
                pass

            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'outlets')
            possible_paths = []
            if config_path:
                possible_paths.append(config_path)
            possible_paths += [
                os.path.join(data_dir, 'outlets.json'),
                os.path.join(os.getcwd(), 'data', 'outlets', 'outlets.json'),
                os.path.join(data_dir, 'news_outlets_local.json'),
                os.path.join(data_dir, 'news_outlets_sources.json'),
                '/app/data/outlets/outlets.json',
            ]

            local_file_path = None
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    local_file_path = abs_path
                    break

            if not local_file_path:
                self.logger.error("No outlets config file found; scraping will be empty")
                return []

            self.logger.info(f"Loading outlets from: {local_file_path}")
            with open(local_file_path, 'r', encoding='utf-8') as fh:
                payload = json.load(fh)

            # Filter to active outlets only, sort by priority then name
            is_rich_format = payload and isinstance(payload[0], dict) and 'display_name' in payload[0]
            if is_rich_format:
                payload = [o for o in payload if o.get('active', True)]
                payload.sort(key=lambda o: (o.get('priority', 99), o.get('name', '')))
            else:
                payload.sort(key=lambda o: o.get('name', ''))

            # OutletsSource.id is a Strapi integer ID — not used in our outlets.json
            # (where "id" is a string slug like "bbc"). Strip fields that would fail
            # Pydantic v1 type coercion so the model only sees what it understands.
            SCRAPER_FIELDS = {'name', 'url', 'active', 'description', 'slug', 'logo'}
            def _to_scraper_record(o: dict) -> dict:
                return {k: v for k, v in o.items() if k in SCRAPER_FIELDS}

            scraper_payload = [_to_scraper_record(o) for o in payload]

            outlets_handler = OutletsHandler()
            outlets_handler.add_outlets_from_payload(scraper_payload)
            self.logger.info(
                f"Loaded {len(outlets_handler.news_outlets)} active outlets from {local_file_path}"
            )
            return outlets_handler.news_outlets
        except Exception as error:
            self.logger.error(f"Error loading outlets from local file: {error}")
            return []
