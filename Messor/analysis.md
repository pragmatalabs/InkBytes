# Messor Codebase Analysis

## Project Overview

The Messor project is a news harvesting application built with Python and React. It's designed to collect and process news content from various sources, with support for scheduled execution and event-driven processing.

## Project Structure

The project follows a modular structure with the following key directories:

- **Main application**: `main.py` (in repository root) acts as a compatibility wrapper that routes to the actual scraper application
- **Core application**: `apps/scraper/` contains the main application logic 
- **Client application**: `client/` is a React frontend
- **Infrastructure**: `docker/` and `infra/docker/` contain Docker configuration and deployment setups

## Main Components

### Core Application (`apps/scraper/`)

The core application is built using:
- Python 3.8+ (with type hints)
- FastAPI for the backend REST API
- Multiple service-oriented architecture with:
  - `APIServer`: Provides REST API endpoints
  - `CommandProcessor`: Handles CLI interaction and command processing
  - `Config`: Configuration management
  - `LoggingService`: Logging infrastructure
  - `OutletService`: Manages news sources and outlets
  - `ScraperService`: Core scraping functionality
  - `StorageService`: Data storage and persistence
  - `AnalyticsService`: Performance monitoring
  - `MessageService`: RabbitMQ event handling

### Configuration (`apps/scraper/env.yaml`)

The configuration file provides:
- Application settings (mode, name, version, threading)
- FastAPI server settings
- Logging configuration (console, file, RabbitMQ)
- Scraping parameters (min word count, timestamp)
- Storage configuration (data paths, file locations)
- DigitalOcean integration (spaces configuration)
- API endpoints (Strapi CMS and Platform API)
- RabbitMQ integration for event-driven architecture
- OpenAI integration
- TinyDB configuration

### Key Features

1. **Event-Driven Architecture**:
   - Uses RabbitMQ for message-based communication
   - Implements queue-based processing for scraping events
   - Supports scheduled scraping modes for Docker environments

2. **Multi-Mode Execution**:
   - Interactive CLI mode with command processing
   - One-shot scraping mode
   - Scheduled mode for continuous operation (Docker environments)
   - Client dashboard mode with React frontend

3. **Scraping Pipeline**:
   - Configurable scraping parameters
   - Support for multiple languages (en, es, fr, de, pt)
   - Proper thread management and locking to prevent concurrent scraping
   - Scheduled execution with configurable intervals (default 60 minutes)

4. **Storage and Persistence**:
   - Local file storage with staging directories
   - Support for cloud storage integration (DigitalOcean Spaces)
   - Data persistence with SQLite-based TinyDB

5. **Client Application**:
   - React-based web dashboard
   - Frontend development server startup capability
   - Browser automation support

## Technical Details

### Architecture Components

- **Application Orchestration**: 
  - `core/application.py` orchestrates all services with proper dependency injection
  - Implements process locking to prevent concurrent scraping operations
  - Supports multiple execution modes: interactive, one-shot, scheduled, client dashboard

- **Service Layer**:
  - Service classes for API interaction, scraping, storage, logging, and messaging
  - Configurable through YAML-based configuration
  - Supports event-driven architecture with RabbitMQ integration

- **Configuration Management**:
  - Dynamic configuration loading from `env.yaml`
  - Fallback logic for backward compatibility
  - Configurable thread counts based on CPU resources

### Execution Flows

1. **Interactive Mode**: Command-line interface with user interaction
2. **One-shot Mode**: Immediate scraping execution with optional parameters
3. **Scheduled Mode**: Continuous scraping cycles in Docker environments
4. **Client Mode**: Web dashboard with automatic browser launch

### Deployment Considerations

- Docker support in `docker/` directory
- Multi-platform support (Linux, macOS, Windows)
- Support for CI/CD environments through scheduled execution
- RabbitMQ-based message queue for scalable processing

This codebase represents a mature, production-ready news harvesting system with support for distributed processing, multi-language content, and robust architecture for handling concurrent scraping operations while providing monitoring and analytics capabilities.