#!/bin/bash

set -e

# Display banner
echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║   __  __ _____ ____ ____   ___  ____                  ║"
echo "║   |  \/  | ____/ ___/ ___| / _ \|  _ \                ║"
echo "║   | |\/| |  _| \___ \___ \| | | | |_) |               ║"
echo "║   | |  | | |___ ___) |__) | |_| |  _ <                ║"
echo "║   |_|  |_|_____|____/____/ \___/|_| \_\               ║"
echo "║                                                       ║"
echo "║          Inkbytes News Harvester                      ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "  Messor Installation Script"
echo ""

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
echo "Checking prerequisites..."
if ! command_exists python3; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

if ! command_exists pip3; then
    echo "Error: pip3 is required but not installed."
    exit 1
fi

if ! command_exists npm; then
    echo "Warning: npm is not installed. Frontend components will not be installed."
    INSTALL_FRONTEND=false
else
    INSTALL_FRONTEND=true
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.10"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo "WARNING: This project was developed with Python $REQUIRED_VERSION. You have Python $PYTHON_VERSION."
    echo "Continuing anyway, but there might be compatibility issues."
fi

echo "Python version $PYTHON_VERSION detected. ✓"

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
if [ -d "venv" ]; then
    echo "Found existing virtual environment. Do you want to recreate it? [y/N]"
    read -r recreate
    if [[ "$recreate" =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo "Virtual environment recreated. ✓"
    else
        echo "Using existing virtual environment. ✓"
    fi
else
    python3 -m venv venv
    echo "Virtual environment created. ✓"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo "Virtual environment activated. ✓"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."

# Skip poetry for now since we're having issues with it
echo "Installing dependencies using pip and requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# Explicitly install key dependencies that might be missing
echo "Installing key dependencies..."
pip install uvicorn fastapi pydantic

# Download NLTK data
echo ""
echo "Downloading required NLTK data..."
python -c "import nltk; nltk.download('punkt')"
echo "NLTK data downloaded. ✓"

# Install Inkbytes libraries
echo ""
echo "Installing Inkbytes libraries..."
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
# Create inkbytes namespace directory
SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
mkdir -p "$SITE_PACKAGES/inkbytes"

# Install each Inkbytes library
for repo in common models database; do
    echo "Installing inkbytes/$repo..."

    # Create temporary directory for cloning
    TEMP_DIR=$(mktemp -d)

    # Clone the repository
    git clone --branch develop "https://gitlab.com/inkbytes/${repo}.git" "$TEMP_DIR"

    # Create destination directory
    DEST="$SITE_PACKAGES/inkbytes/$repo"
    mkdir -p "$DEST"

    # Copy files from temp directory to site-packages
    cp -R "$TEMP_DIR"/* "$DEST/"

    # Clean up
    rm -rf "$TEMP_DIR"

    echo "Installed inkbytes/$repo ✓"
done
echo "Inkbytes libraries installed. ✓"

# Install frontend dependencies
if [ "$INSTALL_FRONTEND" = true ]; then
    echo ""
    echo "Installing frontend dependencies..."
    (cd client && npm install)
    echo "Frontend dependencies installed. ✓"
fi

# Create required directories
echo ""
echo "Creating required directories..."
mkdir -p data/history
mkdir -p data/scrapes
mkdir -p logs
echo "Directories created. ✓"

# Check if example environment file exists and copy if needed
if [ -f "env.example.yaml" ] && [ ! -f "env.yaml" ]; then
    echo ""
    echo "Creating env.yaml from template..."
    cp env.example.yaml env.yaml
    echo "⚠️  IMPORTANT: The env.yaml file contains default values and credentials."
    echo "⚠️  You MUST review and update env.yaml with your own settings before running the application."
    echo "⚠️  At minimum, update API keys, passwords, and endpoints to match your environment."
    echo "Configuration file created. ✓"
fi

# Final message
echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║               Installation Complete!                  ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "IMPORTANT: Always make sure the virtual environment is activated"
echo "before running the application, or dependencies won't be found."
echo ""
echo "To run the backend application:"
echo "  source venv/bin/activate && python main.py"
echo "  (or if you have env.yaml: python main.py env.yaml)"
echo ""
if [ "$INSTALL_FRONTEND" = true ]; then
    echo "To start the frontend development server:"
    echo "  cd client && npm run dev"
    echo ""
fi
echo "Thank you for installing Messor!"