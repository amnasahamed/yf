# Troubleshooting Deployment Errors

## Common Deployment Errors and Solutions

### 1. Requirements Installation Error

**Error Message:**
```
Failed to deploy a stack: compose build operation failed: failed to solve: process "/bin/sh -c pip install --no-cache-dir -r requirements.txt" did not complete successfully: exit code: 1
```

**Solution:**
This error occurs when there are issues with the package versions in requirements.txt. To fix:

1. **Update requirements.txt** with compatible versions:
   ```
   numpy>=1.24.0,<2.0.0
   pandas>=1.5.0,<2.0.0
   psycopg2-binary>=2.9.6
   python-dotenv>=1.0.0
   ta>=0.10.0
   yfinance>=0.2.30
   Flask>=2.0.0
   gunicorn>=21.0.0
   Werkzeug>=2.0.0
   requests>=2.28.0
   ```

2. **Rebuild the image** with the updated requirements:
   ```bash
   # If using docker directly
   docker build -t stock-analyzer .
   
   # If using Portainer Stacks
   # Re-deploy the stack with the updated requirements
   ```

### 2. Database Connection Error

**Error in Logs:**
```
Database connection error: could not connect to server: Connection refused
```

**Solution:**
1. Verify your `.env` file has correct database settings
2. Ensure your database server is running and accessible from your VPS
3. Check if your database server allows remote connections
4. If using a firewall, make sure the database port (usually 5432 for PostgreSQL) is open

### 3. Port Already in Use

**Error:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:5000: bind: address already in use
```

**Solution:**
1. Check what's using port 5000:
   ```bash
   sudo netstat -tulpn | grep 5000
   ```

2. Either stop the conflicting service or change the port in `docker-compose.yml`:
   ```yaml
   ports:
     - "5001:5000"  # Change 5000 to another port like 5001
   ```

### 4. Container Exits Immediately

**Error:**
Container starts and then immediately stops.

**Solution:**
1. Check container logs:
   ```bash
   docker logs stock-analyzer
   ```
   
2. Look for Python errors, especially ImportError or ModuleNotFoundError
   
3. If it's a missing package, add it to requirements.txt and rebuild

### 5. Health Check Failing

**Error:**
```
"curl" command not found in healthcheck
```

**Solution:**
Replace curl with wget in docker-compose.yml:
```yaml
healthcheck:
  test: ["CMD", "wget", "-q", "--spider", "http://localhost:5000"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 6. No Stock Data Appears

**Error:**
Application starts but no stock data is displayed.

**Solution:**
1. Check your database connection string in the `.env` file
2. Verify that your database has the expected table schema:
   ```sql
   SELECT COUNT(*) FROM pelago;
   ```
3. Check if the application can reach Yahoo Finance (network connectivity)
4. Look for specific errors in the container logs

### 7. Permission Errors for Logs

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/app/logs/...'
```

**Solution:**
1. Create the logs directory with proper permissions:
   ```bash
   mkdir -p logs
   chmod 777 logs
   ```
   
2. Rebuild and redeploy the container

### 8. Environment Variables Not Found

**Error:**
```
KeyError: 'DB_HOST'
```

**Solution:**
1. Make sure your `.env` file is properly mounted or loaded
2. For Portainer stacks, ensure the environment variables are properly defined
3. Verify the environment variables exist in the container:
   ```bash
   docker exec stock-analyzer env | grep DB_
   ```

## General Debugging Steps

1. **Check container logs**:
   ```bash
   docker logs stock-analyzer
   ```

2. **Inspect the container**:
   ```bash
   docker inspect stock-analyzer
   ```

3. **Enter the container for debugging**:
   ```bash
   docker exec -it stock-analyzer /bin/bash
   ```

4. **Test the database connection from inside the container**:
   ```bash
   docker exec -it stock-analyzer python -c "import psycopg2; conn = psycopg2.connect(dbname='your_db', user='your_user', password='your_password', host='your_host'); print('Connection successful')"
   ```

5. **Rebuild without cache**:
   ```bash
   docker build --no-cache -t stock-analyzer .
   ```