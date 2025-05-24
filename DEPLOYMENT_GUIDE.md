# Comprehensive Deployment Guide for Stock Analyzer Web Application

This step-by-step guide will walk you through deploying the Stock Analyzer web application on your VPS using Docker and Portainer. Follow these instructions carefully to ensure a smooth deployment without errors.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Preparing Your VPS](#preparing-your-vps)
3. [Uploading Files](#uploading-files)
4. [Configuring Environment Variables](#configuring-environment-variables)
5. [Deploying with Portainer](#deploying-with-portainer)
6. [Accessing the Application](#accessing-the-application)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

Before starting, ensure you have:
- A VPS with Docker installed
- Portainer installed and running
- SSH access to your VPS
- Basic knowledge of Linux commands
- PostgreSQL database with the required schema (as per original application)

## Preparing Your VPS

1. **SSH into your VPS**:
   ```
   ssh username@your-vps-ip
   ```

2. **Create a directory for the application**:
   ```
   mkdir -p /opt/stock-analyzer
   cd /opt/stock-analyzer
   ```

3. **Ensure Docker is running**:
   ```
   sudo systemctl status docker
   ```
   If it's not running, start it:
   ```
   sudo systemctl start docker
   ```

4. **Check Portainer status**:
   Access Portainer at http://your-vps-ip:9000 to verify it's running.

## Uploading Files

### Option 1: Using SCP (from your local machine)

1. **Open a terminal on your local machine** and navigate to the directory containing the "yfinance v3" folder.

2. **Upload the files**:
   ```
   scp -r "yfinance v3/"* username@your-vps-ip:/opt/stock-analyzer/
   ```

### Option 2: Using Git (if you've stored the files in a repository)

1. **On your VPS**, navigate to the application directory:
   ```
   cd /opt/stock-analyzer
   ```

2. **Clone the repository**:
   ```
   git clone https://your-repository-url.git .
   ```

### Option 3: Manual upload using SFTP

Use an SFTP client like FileZilla to upload the "yfinance v3" folder contents to `/opt/stock-analyzer/` on your VPS.

## Configuring Environment Variables

1. **Check if the .env file exists**:
   ```
   ls -la /opt/stock-analyzer/.env
   ```

2. **If it doesn't exist or you need to modify it**, create/edit the .env file:
   ```
   nano /opt/stock-analyzer/.env
   ```

3. **Add the following content**, replacing with your actual database credentials:
   ```
   DB_HOST=your_database_host
   DB_PORT=5432
   DB_NAME=your_database_name
   DB_USER=your_database_username
   DB_PASSWORD=your_database_password
   DB_SCHEMA=public
   ```

4. **Save the file** (in nano: press Ctrl+O, then Enter, then Ctrl+X).

5. **Set proper permissions**:
   ```
   chmod 600 /opt/stock-analyzer/.env
   ```

## Deploying with Portainer

### Method 1: Using Docker Compose (Recommended)

1. **Log in to Portainer** at http://your-vps-ip:9000

2. **Navigate to Stacks**:
   - Click on "Stacks" in the left sidebar
   - Click "Add stack"

3. **Configure the stack**:
   - Name: `stock-analyzer`
   - Build method: Select "Repository"
   - Repository URL: Leave blank if using local files
   - Repository reference: Leave blank
   - Compose path: `/opt/stock-analyzer/docker-compose.yml`

4. **Enable "Access Control"** if you want to restrict access to the stack

5. **Click "Deploy the stack"**

6. **Wait for deployment** to complete (monitor the stack creation progress)

### Method 2: Manual Container Creation

1. **Log in to Portainer** at http://your-vps-ip:9000

2. **Navigate to Containers**:
   - Click on "Containers" in the left sidebar
   - Click "Add container"

3. **Configure the container**:
   - Name: `stock-analyzer`
   - Image: Leave blank for now (we'll build locally)
   - Port mapping: Add a new port mapping
     - Host: `5000`
     - Container: `5000`
     - Protocol: `TCP`

4. **Add environment variables**:
   - Click on "Advanced container settings"
   - Go to the "Env" tab
   - Add variables for DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA with their respective values

5. **Configure volumes**:
   - Go to the "Volumes" tab
   - Add a new volume
     - Container path: `/app/logs`
     - Host path: `/opt/stock-analyzer/logs`
     - Access control: Read/Write

6. **Configure restart policy**:
   - Go to the "Restart policy" tab
   - Select "Unless stopped"

7. **Set up the build**:
   - Go to the "Advanced container settings"
   - Go to the "Command & logging" tab
   - For "Working dir", enter: `/app`
   - Click "Deploy the container"

8. **Build the image**:
   - After deployment, go to "Images"
   - Click "Build a new image"
   - Path: `/opt/stock-analyzer`
   - Image name: `stock-analyzer`
   - Click "Build the image"

9. **Update the container** to use the new image:
   - Go back to "Containers"
   - Stop the container if it's running
   - Click on the container name
   - Click "Duplicate/Edit"
   - Update the Image field to `stock-analyzer:latest`
   - Click "Deploy the container"

## Accessing the Application

1. **Open your web browser** and navigate to:
   ```
   http://your-vps-ip:5000
   ```

2. **Verify the application is working** by checking:
   - Stock data is loading
   - RSI and MACD indicators are displayed
   - The auto-refresh feature is working

## Monitoring and Maintenance

### Checking Logs

1. **In Portainer**:
   - Go to "Containers"
   - Click on your "stock-analyzer" container
   - Select the "Logs" tab

2. **From command line**:
   ```
   docker logs stock-analyzer
   ```

### Updating the Application

When you need to update the application:

1. **Upload the new files** to your VPS

2. **If using Stacks**:
   - Go to "Stacks" in Portainer
   - Select your stack
   - Click "Editor"
   - Click "Update the stack"

3. **If using individual container**:
   - Rebuild the image:
     ```
     docker build -t stock-analyzer:latest /opt/stock-analyzer
     ```
   - Restart the container in Portainer

### Creating a Backup

1. **Backup the application files**:
   ```
   tar -czf /backup/stock-analyzer-$(date +%Y%m%d).tar.gz /opt/stock-analyzer
   ```

2. **Backup database** (if needed):
   ```
   pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > /backup/db-backup-$(date +%Y%m%d).sql
   ```

## Troubleshooting

### Application Not Starting

1. **Check container logs** in Portainer or using:
   ```
   docker logs stock-analyzer
   ```

2. **Verify database connection**:
   - Ensure the database credentials in .env are correct
   - Try connecting to the database manually to verify access:
     ```
     psql -h $DB_HOST -U $DB_USER -d $DB_NAME
     ```

3. **Check for port conflicts**:
   ```
   netstat -tuln | grep 5000
   ```
   If another service is using port 5000, edit docker-compose.yml to use a different port.

### No Stock Data Appears

1. **Verify database schema**:
   - Connect to your database
   - Verify the `pelago` table exists and has data:
     ```sql
     SELECT COUNT(*) FROM pelago;
     ```

2. **Check for network issues**:
   - Ensure your VPS can access external services (Yahoo Finance API)
   - Test with:
     ```
     curl -I https://query1.finance.yahoo.com
     ```

### Web Interface Not Accessible

1. **Check if container is running**:
   ```
   docker ps | grep stock-analyzer
   ```

2. **Verify port mapping**:
   ```
   docker port stock-analyzer
   ```

3. **Check firewall settings**:
   ```
   sudo ufw status
   ```
   If UFW is active, allow port 5000:
   ```
   sudo ufw allow 5000/tcp
   ```

---

If you encounter any issues not covered in this guide, please check the container logs for specific error messages, which will provide more details about the problem.