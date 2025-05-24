#!/bin/bash
set -e

# Stock Analyzer Push Script for GitHub and Docker Hub
# This script helps push your code to GitHub and Docker Hub

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Stock Analyzer GitHub and Docker Hub Push ===${NC}"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: Git is not installed.${NC}"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    exit 1
fi

# Get GitHub username
read -p "Enter your GitHub username: " GITHUB_USERNAME
if [ -z "$GITHUB_USERNAME" ]; then
    echo -e "${RED}Error: GitHub username cannot be empty.${NC}"
    exit 1
fi

# Get Docker Hub username
read -p "Enter your Docker Hub username: " DOCKER_USERNAME
if [ -z "$DOCKER_USERNAME" ]; then
    echo -e "${RED}Error: Docker Hub username cannot be empty.${NC}"
    exit 1
fi

# Get repository name or use default
read -p "Enter repository name [stock-analyzer]: " REPO_NAME
REPO_NAME=${REPO_NAME:-stock-analyzer}

# Check if this is a new repository or an update
if [ -d .git ]; then
    echo -e "${YELLOW}Git repository already initialized. Updating existing repository.${NC}"
    GIT_INIT=false
else
    echo -e "${YELLOW}Initializing new Git repository.${NC}"
    git init
    GIT_INIT=true
fi

# Rename README_GITHUB.md to README.md if it exists
if [ -f README_GITHUB.md ] && [ ! -f README.md ]; then
    echo -e "${YELLOW}Renaming README_GITHUB.md to README.md${NC}"
    mv README_GITHUB.md README.md
fi

# Add all files to git
echo -e "${GREEN}Adding files to git...${NC}"
git add .

# Commit changes
read -p "Enter commit message [Update Stock Analyzer]: " COMMIT_MSG
COMMIT_MSG=${COMMIT_MSG:-"Update Stock Analyzer"}
echo -e "${GREEN}Committing changes with message: '${COMMIT_MSG}'${NC}"
git commit -m "$COMMIT_MSG"

# Setup GitHub repository if this is a new repository
if [ "$GIT_INIT" = true ]; then
    echo -e "${YELLOW}Setting up GitHub repository...${NC}"
    echo -e "${YELLOW}Please create a new repository named '${REPO_NAME}' on GitHub before continuing.${NC}"
    echo -e "${YELLOW}Do not initialize it with README, .gitignore, or license files.${NC}"
    read -p "Press Enter when you've created the repository on GitHub..."
    
    # Add remote and set branch
    echo -e "${GREEN}Adding GitHub remote...${NC}"
    git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
    git branch -M main
fi

# Push to GitHub
echo -e "${GREEN}Pushing to GitHub...${NC}"
git push -u origin main

# Build Docker image
echo -e "${GREEN}Building Docker image...${NC}"
docker build -t "$REPO_NAME" .

# Tag Docker image
echo -e "${GREEN}Tagging Docker image...${NC}"
docker tag "$REPO_NAME:latest" "${DOCKER_USERNAME}/${REPO_NAME}:latest"

# Login to Docker Hub
echo -e "${YELLOW}Logging in to Docker Hub...${NC}"
docker login

# Push to Docker Hub
echo -e "${GREEN}Pushing to Docker Hub...${NC}"
docker push "${DOCKER_USERNAME}/${REPO_NAME}:latest"

# Create a .env file for docker-compose with Docker username
echo -e "${GREEN}Creating/updating .env file for docker-compose...${NC}"
if [ -f .env ]; then
    # Add or update DOCKER_USERNAME in existing .env file
    if grep -q "DOCKER_USERNAME=" .env; then
        sed -i "s/DOCKER_USERNAME=.*/DOCKER_USERNAME=${DOCKER_USERNAME}/" .env
    else
        echo "DOCKER_USERNAME=${DOCKER_USERNAME}" >> .env
    fi
else
    echo "DOCKER_USERNAME=${DOCKER_USERNAME}" > .env
fi

echo -e "${GREEN}Success! Your code has been pushed to:${NC}"
echo -e "${GREEN}GitHub: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}${NC}"
echo -e "${GREEN}Docker Hub: https://hub.docker.com/r/${DOCKER_USERNAME}/${REPO_NAME}${NC}"
echo -e "${YELLOW}To deploy using docker-compose:${NC}"
echo -e "${YELLOW}docker-compose up -d${NC}"