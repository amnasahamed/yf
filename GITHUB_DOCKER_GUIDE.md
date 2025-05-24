# GitHub and Docker Hub Push Guide

This guide will walk you through pushing your Stock Analyzer application to both GitHub and Docker Hub.

## GitHub Push Instructions

### 1. Initialize Git Repository (if not done already)

```bash
cd /path/to/yfinance\ v3/
git init
```

### 2. Rename README_GITHUB.md to README.md

```bash
mv README_GITHUB.md README.md
```

### 3. Add Files to Git

```bash
git add .
git status  # Check which files will be committed
```

### 4. Commit Your Changes

```bash
git commit -m "Initial commit of Stock Analyzer Web App"
```

### 5. Create a GitHub Repository

1. Go to [GitHub](https://github.com/) and sign in
2. Click the "+" icon in the upper right corner and select "New repository"
3. Name your repository (e.g., "stock-analyzer")
4. Leave it as a public repository if you want others to see it
5. Do NOT initialize with a README, .gitignore, or license as we already have these files
6. Click "Create repository"

### 6. Link and Push to GitHub

Replace `yourusername` with your actual GitHub username:

```bash
git remote add origin https://github.com/yourusername/stock-analyzer.git
git branch -M main
git push -u origin main
```

## Docker Hub Push Instructions

### 1. Create a Docker Hub Account

If you don't already have one, create an account at [Docker Hub](https://hub.docker.com/).

### 2. Log in to Docker Hub from Command Line

```bash
docker login
# Enter your Docker Hub username and password when prompted
```

### 3. Tag Your Docker Image

Replace `yourusername` with your Docker Hub username:

```bash
# Check if you already have the image built
docker images

# Tag the image for Docker Hub
docker tag stock-analyzer:latest yourusername/stock-analyzer:latest
```

### 4. Push to Docker Hub

```bash
docker push yourusername/stock-analyzer:latest
```

### 5. Verify Your Image on Docker Hub

1. Go to [Docker Hub](https://hub.docker.com/) and log in
2. Navigate to "Repositories"
3. You should see your "stock-analyzer" repository
4. Click on it to view details and documentation

## Using Your Docker Image

Once your image is on Docker Hub, others can use it with:

```bash
docker pull yourusername/stock-analyzer:latest
```

## Updating Your Code

When you make changes:

### GitHub Update

```bash
git add .
git commit -m "Description of your changes"
git push origin main
```

### Docker Hub Update

```bash
# Rebuild the image
docker build -t stock-analyzer .

# Retag it
docker tag stock-analyzer:latest yourusername/stock-analyzer:latest

# Push the updated image
docker push yourusername/stock-analyzer:latest
```

## Automating Builds with GitHub Actions

For advanced users, consider setting up GitHub Actions to automatically build and push your Docker image when you update your GitHub repository. This requires creating a workflow file in your repository.