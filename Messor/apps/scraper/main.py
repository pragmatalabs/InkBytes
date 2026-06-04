#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Messor application.

This module initializes and runs the Messor news harvesting application.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Copyright: © 2025 InkBytes Technologies
"""

from core.application import Application
import sys
import os
import time

def print_banner():
    """Print a stylish CLI banner for the application"""
    banner = r"""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   __  __ _____ ____ ____   ___  ____                  ║
    ║   |  \/  | ____/ ___/ ___| / _ \|  _ \                ║
    ║   | |\/| |  _| \___ \___ \| | | | |_) |               ║
    ║   | |  | | |___ ___) |__) | |_| |  _ <                ║
    ║   |_|  |_|_____|____/____/ \___/|_| \_\               ║
    ║                                                       ║
    ║          Inkbytes News Harvester                      ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    # Import the application metadata
    from core.application import Application
    
    print(banner)
    print(f"  {Application.NAME} v{Application.VERSION}")
    print(f"  {Application.DESCRIPTION}")
    print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  System: {os.name.upper()}")
    print("\n" + "="*63 + "\n")

if __name__ == "__main__":
    # Ensure NLTK data is downloaded
    import nltk
    import argparse
    
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Downloading required NLTK data...")
        nltk.download('punkt')
        print("Download complete!")

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Messor - InkBytes News Harvester")
    parser.add_argument("config_path", nargs='?', default="env.yaml", help="Path to the configuration file (defaults to env.yaml in app root)")
    parser.add_argument("--client", action="store_true", help="Automatically start the client web application")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser when starting client")
    parser.add_argument("--scrape", help="Run scraping immediately with optional parameters", nargs='?', const="")
    parser.add_argument("--schedule", action="store_true", help="Run in scheduled mode (for Docker environments) - scrapes continuously at configured intervals")
    parser.add_argument("--no-api", action="store_true", help="Do not start the FastAPI server on :8050 (lets a one-shot --scrape coexist with a running messor-api)")
    
    # Show banner before parsing to make help output nicer
    print_banner()
    
    args = parser.parse_args()
    
    # Check if config file exists, throw error if not
    if not os.path.exists(args.config_path):
        print(f"ERROR: Configuration file '{args.config_path}' not found!")
        print(f"Please ensure the configuration file exists in the app root directory.")
        sys.exit(1)
    
    # Print config info
    print(f"Loading configuration from: {args.config_path}")
    print("Initializing application...\n")
    
    # Create Application instance with the auto_start_client flag
    app = Application(args.config_path)
    
    # Pass the arguments to the run method
    app.run(auto_start_client=args.client,
            auto_scrape=args.scrape,
            no_browser=args.no_browser,
            scheduled_mode=args.schedule,
            no_api=args.no_api)