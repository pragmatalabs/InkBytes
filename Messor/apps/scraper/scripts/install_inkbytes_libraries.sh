#!/bin/bash

# Validate script arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <gitlab_repo_url> <branch> <namespace>"
    exit 1
fi

# Assign arguments to variables
gitlab_repo=$1
branch=$2
namespace=$3

# Detect Python version (this assumes you're using a venv and Python is installed)
python_version=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# Specify the temporary directory to clone the repository based on the detected Python version
repo_name=$(basename -s .git $(basename $gitlab_repo))
dest="/app/venv/lib/python${python_version}/site-packages/$namespace/$repo_name"
mkdir -p "$dest"

# Clone the GitLab repository
git clone --branch $branch $gitlab_repo $dest

echo "Package '$repo_name' has been installed in '$namespace' namespace for Python $python_version."