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
        """Access the platform API configuration."""
        return self._config.platform_api
    
    @property
    def digitalocean(self):
        return self._config.digitalocean
    
    @property
    def scraping(self):
        return self._config.scraping
    
    def get_schedule_interval_minutes(self):
        """Get the schedule interval in minutes.

        Priority: MESSOR_SCHEDULE_INTERVAL_MINUTES env var → env.yaml → 360 (4×/day).
        """
        import os
        env_val = os.environ.get("MESSOR_SCHEDULE_INTERVAL_MINUTES")
        if env_val is not None:
            try:
                return max(1, int(env_val))
            except (ValueError, TypeError):
                pass
        try:
            interval = getattr(self._config.scraping, 'schedule_interval_minutes', 360)
            if hasattr(interval, 'value'):
                return int(interval.value)
            return int(interval)
        except (AttributeError, ValueError, TypeError):
            return 360

    def get_harvest_anchor_hours_utc(self) -> list[int] | None:
        """Fixed UTC hours to run the scheduled harvest at, or None (interval mode).

        When set, the scheduler runs at these hours-of-day (UTC) instead of every
        `schedule_interval_minutes` — used to keep cycles OUT of the DeepSeek peak
        windows (UTC 01–04 + 06–10, where Curator's enrich/synthesize bills 2×).
        Peak ≈ overnight in the Americas (LATAM-primary audience), so the routine
        sweep pauses there; the pulse lane still catches breaking news.

        Priority: MESSOR_HARVEST_ANCHORS_UTC ("0,4,10,...") → env.yaml
        `scraping.harvest_anchors_utc` → None. Invalid/empty → None (interval mode).
        """
        import os
        raw = os.environ.get("MESSOR_HARVEST_ANCHORS_UTC")
        if raw is None:
            val = getattr(self._config.scraping, 'harvest_anchors_utc', None)
            raw = getattr(val, 'value', val) if val is not None else None
        if not raw:
            return None
        try:
            hours = sorted({int(h) for h in str(raw).split(',') if h.strip() != ""}
                           & set(range(24)))
            return hours or None
        except (ValueError, TypeError):
            return None

    def get_startup_delay_minutes(self) -> int:
        """Minutes to wait before the FIRST scraping cycle on startup.

        Prevents a burst of back-to-back full-outlet sweeps when Docker
        restarts Messor repeatedly (e.g. during OOM recovery).  The API
        is still available immediately; only the scheduled scrape is delayed.
        Default: 0 (no delay) — set scraping.startup_delay_minutes in env.yaml
        to override.  The env var MESSOR_STARTUP_DELAY_MINUTES takes precedence.
        """
        import os
        env_val = os.environ.get("MESSOR_STARTUP_DELAY_MINUTES")
        if env_val is not None:
            try:
                return max(0, int(env_val))
            except (ValueError, TypeError):
                pass
        try:
            val = getattr(self._config.scraping, 'startup_delay_minutes', 0)
            if hasattr(val, 'value'):
                return max(0, int(val.value))
            return max(0, int(val))
        except (AttributeError, ValueError, TypeError):
            return 0

    def get_pulse_interval_minutes(self) -> int:
        """Breaking-news pulse interval (Messor ADR-0017).

        Every N minutes, scrape only pulse-flagged outlets via RSS and publish
        their articles at AMQP priority 9.  0 disables the pulse lane.
        Priority: MESSOR_PULSE_INTERVAL_MINUTES env var → env.yaml
        (scraping.pulse_interval_minutes) → 5.
        """
        import os
        env_val = os.environ.get("MESSOR_PULSE_INTERVAL_MINUTES")
        if env_val is not None:
            try:
                return max(0, int(env_val))
            except (ValueError, TypeError):
                pass
        try:
            val = getattr(self._config.scraping, 'pulse_interval_minutes', 5)
            if hasattr(val, 'value'):
                return max(0, int(val.value))
            return max(0, int(val))
        except (AttributeError, ValueError, TypeError):
            return 5

    @property
    def curator_api(self):
        """Curator API config (primary outlet source — always available)."""
        return getattr(self._config, "curator_api", None)

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
