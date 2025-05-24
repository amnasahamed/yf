# Deploying Stock Analyzer in Portainer

This guide will walk you through deploying the Stock Analyzer web application using Portainer on your VPS.

## Prerequisites

- Docker installed on your VPS
- Portainer installed and running
- Access to your VPS via SSH

## Deployment Steps

### 1. Upload Files to Your VPS

First, upload the entire `yfinance v3` directory to your VPS using SCP, SFTP, or any other file transfer method.

```bash
scp -r "yfinance v3" user@your-vps-ip:/path/to/destination/
```

### 2. Log in to Portainer

Open your web browser and navigate to Portainer:

```
http://your-vps-ip:9000/
```

Login with your credentials.

### 3. Deploy with Docker Compose

#### Using the Stacks Feature

1. In Portainer, select your environment (usually "local")
2. Click on "Stacks" in the left sidebar
3. Click "Add stack"
4. Name your stack (e.g., "stock-analyzer")
5. Under "Build method", select "Web editor"
6. Click "Repository" and enter the path to your docker-compose.yml file on your VPS:
   ```
   /path/to/yfinance v3/docker-compose.yml
   ```
7. Alternatively, copy the contents of the docker-compose.yml file and paste it into the web editor
8. Click "Deploy the stack"

### 4. Deploy as a Container (Alternative Method)

If you prefer to deploy as a standalone container:

1. In Portainer, select your environment
2. Click on "Containers" in the left sidebar
3. Click "Add container"
4. Fill in the form:
   - Name: `stock-analyzer`
   - Image: Click "Build a new image" and specify:
     - Path: `/path/to/yfinance v3/`
     - Dockerfile name: `Dockerfile`
   - Port mapping: `5000:5000`
   - Advanced container settings:
     - Under "Env", add your database variables from the `.env` file
5. Click "Deploy the container"

### 5. Verify Deployment

1. In Portainer, go to "Containers" to see your running container
2. Check logs for any errors by clicking on the container name and selecting the "Logs" tab
3. Access the web application by navigating to:
   ```
   http://your-vps-ip:5000/
   ```

## Managing Your Container

### Viewing Logs

1. Go to "Containers" in Portainer
2. Click on your "stock-analyzer" container
3. Select the "Logs" tab

### Stopping/Starting the Container

1. Go to "Containers" in Portainer
2. Find your "stock-analyzer" container
3. Use the controls in the "Actions" column to stop, start, or restart

### Updating the Application

To update the application after making changes:

1. If using Stacks:
   - Go to "Stacks"
   - Click on your stack
   - Click "Editor" to modify settings if needed
   - Click "Update the stack"

2. If using individual container:
   - Remove the existing container
   - Create a new container following the steps above

## Troubleshooting

### Container Not Starting

Check logs for errors:
1. Go to "Containers"
2. Click on your container
3. Select "Logs"

Common issues:
- Database connection problems (check `.env` file)
- Port conflicts (ensure port 5000 is available)
- Missing dependencies (verify requirements.txt)

### Application Not Accessible

- Ensure port 5000 is open in your VPS firewall
- Check if the container is running
- Verify network settings in Portainer