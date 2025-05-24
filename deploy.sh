#!/bin/bash
set -e

# Stock Analyzer Web App Deployment Script
# This script deploys the stock analyzer web application using Docker

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Stock Analyzer Web App Deployment ===${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating a template...${NC}"
    cat > .env << EOL
DB_HOST=your_database_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_SCHEMA=public
EOL
    echo -e "${YELLOW}Please edit the .env file with your database credentials.${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs
chmod 777 logs

# Check if the container already exists
if docker ps -a --format '{{.Names}}' | grep -q '^stock-analyzer$'; then
    echo -e "${YELLOW}Container 'stock-analyzer' already exists. Stopping and removing...${NC}"
    docker stop stock-analyzer || true
    docker rm stock-analyzer || true
fi

# Build the Docker image
echo -e "${GREEN}Building Docker image...${NC}"
docker build -t stock-analyzer .

# Run the container
echo -e "${GREEN}Starting container...${NC}"
docker run -d \
    --name stock-analyzer \
    -p 5000:5000 \
    --restart unless-stopped \
    --env-file .env \
    -v "$(pwd)/logs:/app/logs" \
    stock-analyzer

# Check if container started successfully
if docker ps --format '{{.Names}}' | grep -q '^stock-analyzer$'; then
    echo -e "${GREEN}Container started successfully!${NC}"
    echo -e "${GREEN}App is available at: http://$(hostname -I | awk '{print $1}'):5000${NC}"
    echo -e "${YELLOW}View logs with: docker logs stock-analyzer${NC}"
else
    echo -e "${RED}Failed to start the container.${NC}"
    echo -e "${YELLOW}Checking logs:${NC}"
    docker logs stock-analyzer
    exit 1
fi