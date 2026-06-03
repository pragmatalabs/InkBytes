#!/bin/bash

# Docker Host Directory Setup Script
# This script ensures proper host directory structure for Docker volumes

set -e

echo "Verifying project structure for Messor Docker deployment..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Project root: $PROJECT_ROOT"
echo "Docker will bind to existing directories in project root"

# Verify existing project structure (don't create anything)
echo "Verifying required directories exist..."

# Check if data directory exists
if [ ! -d "$PROJECT_ROOT/data" ]; then
    echo "❌ Error: data directory not found at $PROJECT_ROOT/data"
    echo "   This directory should already exist in the project root."
    exit 1
fi

# Check if logs directory exists
if [ ! -d "$PROJECT_ROOT/logs" ]; then
    echo "❌ Error: logs directory not found at $PROJECT_ROOT/logs"  
    echo "   This directory should already exist in the project root."
    exit 1
fi

# Check if env.yaml exists
if [ ! -f "$PROJECT_ROOT/env.yaml" ]; then
    echo "❌ Error: env.yaml not found at $PROJECT_ROOT/env.yaml"
    echo "   This configuration file should exist in the project root."
    exit 1
fi

# Verify data subdirectories exist
echo "Checking data subdirectories..."
for subdir in outlets; do
    if [ ! -d "$PROJECT_ROOT/data/$subdir" ]; then
        echo "⚠️  Warning: data/$subdir directory not found"
        echo "   This may cause issues with the application."
    fi
done

echo "✅ Project structure verification complete!"
echo "   📁 $PROJECT_ROOT/data - will be bound to /app/data"
echo "   📁 $PROJECT_ROOT/logs - will be bound to /app/logs"  
echo "   📄 $PROJECT_ROOT/env.yaml - will be bound to /app/env.yaml"

# Check if outlets file exists
OUTLETS_FILE="$PROJECT_ROOT/data/outlets/news_outlets_sources.json"
if [ ! -f "$OUTLETS_FILE" ]; then
    echo "⚠️  Warning: outlets file not found at $OUTLETS_FILE"
    echo "   The application may not find any outlets to scrape."
else
    echo "✅ Outlets file found: $OUTLETS_FILE"
fi

# Create .env file if it doesn't exist
ENV_FILE="$PROJECT_ROOT/docker/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env file from example..."
    if [ -f "$PROJECT_ROOT/docker/example.changeme.env" ]; then
        cp "$PROJECT_ROOT/docker/example.changeme.env" "$ENV_FILE"
        echo "✅ Created $ENV_FILE from example. Please review and update as needed."
    else
        echo "CONTAINER_NAME=messor" > "$ENV_FILE"
        echo "✅ Created basic $ENV_FILE"
    fi
else
    echo "✅ .env file already exists"
fi

# Check if env.yaml exists
if [ ! -f "$PROJECT_ROOT/env.yaml" ]; then
    echo "⚠️  Warning: env.yaml not found in project root."
    echo "   Please ensure env.yaml exists before starting Docker container."
    echo "   Copy from env.yaml.example if available."
fi

echo ""
echo "✅ Host directory setup complete!"
echo ""
echo "Directory structure created at:"
echo "  📁 $PROJECT_ROOT/data/"
echo "  📁 $PROJECT_ROOT/logs/"
echo ""
echo "Next steps:"
echo "  1. Review and update $ENV_FILE"
echo "  2. Ensure $PROJECT_ROOT/env.yaml exists and is configured"
echo "  3. Run: docker-compose up -d"
echo ""
echo "The data directory will be mounted as a volume and all application"
echo "data will persist on the host filesystem at:"
echo "  $PROJECT_ROOT/data/"