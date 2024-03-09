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

# Specify the temporary directory to clone the repository
repo_name=$(basename -s .git $(basename $gitlab_repo))
dest=/app/venv/lib/python3.10/site-packages/$namespace/$repo_name
mkdir -p "$dest"

# Clone the GitLab repository
git clone --branch $branch $gitlab_repo $dest

echo "Package '$repo_name' has been installed in '$namespace' namespace."
