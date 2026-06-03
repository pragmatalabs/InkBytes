# Docker Setup for Messor

This directory contains Docker configurations for running Messor in containerized environments.

## Data Directory Handling

The existing project data directory is **bound as a host volume** to ensure:
- **Uses existing data**: Binds to the actual project data directory at `../data`
- **No duplication**: Does not create new directories - uses your existing project structure
- **Data persistence**: All scraped data continues to be stored in your project directory
- **Host accessibility**: Data remains accessible directly from the project root
- **Development**: Continue using existing data and configuration files

## Volume Mounts

### Data Directory (`../data:/app/data:rw`)
- **Host Path**: `../data` (project root data directory, relative to docker-compose.yaml)
- **Container Path**: `/app/data`
- **Permissions**: Read-Write
- **Purpose**: Binds to existing project data directory - does NOT create new data

### Logs Directory (`../logs:/app/logs:rw`)
- **Host Path**: `../logs` (project root logs directory)
- **Container Path**: `/app/logs`
- **Permissions**: Read-Write
- **Purpose**: Binds to existing project logs directory

### Configuration (`../env.yaml:/app/env.yaml:ro`)
- **Host Path**: `../env.yaml` (project root configuration)
- **Container Path**: `/app/env.yaml` 
- **Permissions**: Read-Only
- **Purpose**: Uses existing project configuration file

## Docker Compose Files

### `docker-compose.yaml`
- **Purpose**: Production deployment
- **Context**: Current directory (.)
- **Networks**: Connects to portainer, messor, and rabbitmq networks

### `docker-compose.local.yaml`
- **Purpose**: Local development
- **Context**: Parent directory (..)
- **Features**: Memory limits and resource constraints

## Environment Variables

### Docker Detection
- `DOCKER_CONTAINER=true`: Used by application to detect Docker environment
- `DATA_DIR=/app/data`: Data directory path inside container
- `LOGS_DIR=/app/logs`: Logs directory path inside container

## Usage

### Production Deployment
```bash
# From docker directory - binds to existing project structure
cd docker
./setup-host-directories.sh  # Verifies project structure
docker-compose up -d
```

### Local Development
```bash
# From docker directory - binds to existing project structure
cd docker
./setup-host-directories.sh  # Verifies project structure
docker-compose -f docker-compose.local.yaml up -d
```

### Scheduled Mode (Default)
The container runs in scheduled mode by default (`CMD ["python", "main.py", "--schedule"]`), which:
- Runs scraping at configured intervals (default: 60 minutes)
- Uses configuration from `env.yaml` for interval settings
- Prevents overlapping scraping processes
- Suitable for production deployments

### Manual Mode
To run in interactive mode instead of scheduled:
```bash
docker-compose run --rm messor python main.py
```

## Data Directory Structure

The mounted data directory will contain:
```
data/
├── articles.db.json          # Article database
├── scrapes/                  # Scraped content
├── history/                  # Scraping history
├── clusters/                 # Content clusters
├── outlets/                  # Outlet configurations
│   └── news_outlets_sources.json
└── rabbit/                   # Message queue data
    └── queue.json
```

## Troubleshooting

### Permission Issues
If you encounter permission issues with the data directory:
```bash
# Fix permissions on host
chmod 755 data logs
chmod -R 644 data/* logs/*
```

### Volume Mount Issues
- Ensure relative paths are correct for your docker-compose location
- Check that host directories exist before starting container
- Verify Docker has permission to access host directories

### Scheduled Mode Not Working
- Check environment variable `DOCKER_CONTAINER=true` is set
- Verify `schedule_interval_minutes` in env.yaml
- Check container logs: `docker-compose logs messor`