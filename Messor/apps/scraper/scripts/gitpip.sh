#!/bin/bash

# Get GitLab repository URL from user input
read -p "Enter GitLab repository URL: " gitlab_repo

# Get branch from user input
read -p "Enter branch for installation: " branch

# Get namespace from user input
read -p "Enter namespace for installation: " namespace

# Detect Python version (assuming Python is installed and available in the venv)
python_version=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# Specify the temporary directory to clone the repository based on the detected Python version
repo_name=$(basename -s .git $(basename $gitlab_repo))
dest="venv/lib/python${python_version}/site-packages/$namespace/$repo_name"
mkdir -p "$dest"

# Clone the GitLab repository
git clone --branch $branch $gitlab_repo "$dest"

echo "Package '$repo_name' has been installed in '$namespace' namespace for Python $python_version."