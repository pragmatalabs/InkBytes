#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration management for the Messor application.

This module loads and provides access to configuration parameters.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

from inkbytes.common.system.config.config_loader import ConfigLoader

class Config:
    def __init__(self, config_path: str):
        self._config = ConfigLoader(config_path)
    
    @property
    def logging(self):
        return self._config.logging
    
    @property
    def platform_api(self):
        """Access the primary platform API configuration.

        Backward compatible with older configs that still use `strapi_cms`.
        """
        if hasattr(self._config, "platform_api"):
            return self._config.platform_api
        return self._config.strapi_cms

    @property
    def strapi_cms(self):
        """Backward-compatible alias for legacy callers."""
        return self.platform_api
    
    @property
    def digitalocean(self):
        return self._config.digitalocean
    
    @property
    def scraping(self):
        return self._config.scraping
    
    def get_schedule_interval_minutes(self):
        """Get the schedule interval in minutes, default to 60 if not configured."""
        try:
            interval = getattr(self._config.scraping, 'schedule_interval_minutes', 360)
            # Convert to int if it's a ConfigNode or string
            if hasattr(interval, 'value'):
                return int(interval.value)
            return int(interval)
        except (AttributeError, ValueError, TypeError):
            return 60
    
    @property
    def articles(self):
        return self._config.articles
    
    @property
    def storage(self):
        return self._config.storage
    
    @property
    def fast_api(self):
        return self._config.fast_api
    
    @property
    def rabbitmq(self):
        """Access to RabbitMQ configuration."""
        return self._config.rabbitmq
    
    def get_thread_count(self):
        """Calculate the optimal number of worker threads."""
        import os
        return (os.cpu_count() // 2) if os.cpu_count() is not None else 1
