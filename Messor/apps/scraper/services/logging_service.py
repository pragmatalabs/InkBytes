#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging Service for the Messor application.

This module provides logging capabilities with configurable destinations and log rotation.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import logging
import os
from typing import List
from inkbytes.common.system.logger.advanced_logger import LogDestination, AdvancedLogger
from inkbytes.common.system.logger.log_formatters import NormalEnhancedSyslogFormatter
from inkbytes.common.system.logger.log_system import LoggerFactory, LoggerConfig

class LoggingService:
    def __init__(self, config):
        self.logger = self._configure_logger(config.logging)
    
    def _configure_logger(self, logging_config) -> logging.Logger:
        """Configure the logging system with date rotation."""
        log_config = LoggerConfig()
        log_config.handler_type = "timed_rotating_file"
        log_config.log_file = os.path.join(logging_config.folder(), logging_config.file_name())
        log_config.log_formatter = NormalEnhancedSyslogFormatter(app_name="Messor")
        log_config.log_level = logging_config.level()
        
        # Add rotation parameters
        log_config.rotation_params = {
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'encoding': 'utf-8',
            'delay': False,
            'utc': False,
            'suffix': '%Y-%m-%d'
        }
        
        logger = LoggerFactory.create_logger("Inkbytes.Messor", [log_config])

        logging.getLogger('botocore').setLevel(logging.ERROR)  # Or use logging.INFO or logging.WARNING
        # Add console handler for better visibility
        if 'console' in logging_config.destinations():
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_config.log_formatter)
            console_handler.setLevel(log_config.log_level)
            logger.addHandler(console_handler)
        
        return logger
    
    def info(self, message: str):
        self.logger.info(message)
        
    def error(self, message: str):
        self.logger.error(message)
        
    def warning(self, message: str):
        self.logger.warning(message)