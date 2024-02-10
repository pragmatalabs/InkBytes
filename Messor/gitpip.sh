#!/bin/bash

# Get GitLab repository URL from user input
read -p "Enter GitLab repository URL: " gitlab_repo

# Get namespace from user input
read -p "Enter branch for installation: " branch

read -p "Enter namespace for installation: " namespace
# Specify the temporary directory to clone the repository
repo_name=$(basename -s .git $(basename $gitlab_repo))
dest=venv/lib/python3.10/site-packages/$namespace/$repo_name
mkdir -p "$dest"

# Clone the GitLab repository
git clone --branch $branch $gitlab_repo $dest



echo "Package '$repo_name' has been installed as '$namespace' namespace."
