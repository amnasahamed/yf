# Minimal Setup Guide for Stock Analyzer Web App

This guide provides the bare minimum steps to get the Stock Analyzer web application running on your VPS with Docker and Portainer.

## 1. Upload Files

Upload all files from the "yfinance v3" folder to your VPS:

```bash
# From your local machine
scp -r "yfinance v3/"* username@your-vps-ip:/opt/stock-analyzer/
```

## 2. Set Database Credentials

Ensure the `.env` file in the upload directory contains:

```
DB_HOST=your_database_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_SCHEMA=public
```

## 3. Deploy Using Portainer

### Option A: Stack Deployment (Recommended)

1. Log in to Portainer (http://your-vps-ip:9000)
2. Go to Stacks → Add stack
3. Name it "stock-analyzer"
4. Use Web editor
5. Path to compose file: `/opt/stock-analyzer/docker-compose.yml`
6. Click "Deploy the stack"

### Option B: Manual Container (Alternative)

1. SSH into your VPS
2. Run:
   ```bash
   cd /opt/stock-analyzer
   docker build -t stock-analyzer .
   docker run -d --name stock-analyzer -p 5000:5000 --restart unless-stopped --env-file .env stock-analyzer
   ```

## 4. Access the Application

Open your browser and go to:
```
http://your-vps-ip:5000
```

## 5. Troubleshooting

If the app doesn't work:

1. Check container logs:
   ```bash
   docker logs stock-analyzer
   ```

2. Verify port is open:
   ```bash
   sudo ufw status
   # If needed: sudo ufw allow 5000/tcp
   ```

3. Test database connection:
   ```bash
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME
   ```

## 6. Restart or Update

```bash
# Restart container
docker restart stock-analyzer

# Update after code changes
docker build -t stock-analyzer /opt/stock-analyzer
docker stop stock-analyzer
docker rm stock-analyzer
docker run -d --name stock-analyzer -p 5000:5000 --restart unless-stopped --env-file /opt/stock-analyzer/.env stock-analyzer
```