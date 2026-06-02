#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Server for the Messor application.

This module provides a FastAPI server that runs in a separate thread.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

import threading
from uvicorn import run as uvicorn_run

class APIServer:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.server_thread = None
    
    def start(self):
        """Start the FastAPI server with configured parameters."""
        self.logger.info("Starting start_fastapi_server")
        try:
            server_args = self.config.fast_api.server_args()
            self.logger.info(f"Starting FastAPI server with arguments: {server_args}")
            
            # Start server in a separate thread so it doesn't block the main thread
            self.server_thread = threading.Thread(
                target=uvicorn_run,
                kwargs={arg: value for arg, value in server_args.items()}
            )
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.logger.info("FastAPI server started in background thread")
        except Exception as e:
            self.logger.error(f"Error in start_fastapi_server: {e}")