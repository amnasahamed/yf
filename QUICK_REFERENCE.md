# Stock Analyzer Web App - Quick Reference Card

## Deployment Commands

### Initial Setup
```bash
# Create directory
mkdir -p /opt/stock-analyzer

# Upload files
scp -r "yfinance v3/"* username@your-vps-ip:/opt/stock-analyzer/

# Set permissions
chmod 600 /opt/stock-analyzer/.env
```

### Docker Commands
```bash
# Build the image
docker build -t stock-analyzer /opt/stock-analyzer

# Run container manually
docker run -d --name stock-analyzer -p 5000:5000 --env-file /opt/stock-analyzer/.env stock-analyzer

# View logs
docker logs stock-analyzer

# Restart container
docker restart stock-analyzer

# Stop and remove
docker stop stock-analyzer
docker rm stock-analyzer
```

## Portainer Quick Actions

1. **Deploy Stack**: Stacks → Add stack → Use web editor → Paste docker-compose.yml → Deploy
2. **View Logs**: Containers → stock-analyzer → Logs
3. **Restart Container**: Containers → ⟳ icon next to stock-analyzer
4. **Update Stack**: Stacks → stock-analyzer → Editor → Update

## Environment Variables
```
DB_HOST=your_database_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_SCHEMA=public
```

## Troubleshooting Checklist

- ✓ Container is running (`docker ps`)
- ✓ Port 5000 is open in firewall (`ufw status`)
- ✓ Database connection is working
- ✓ Environment variables are set correctly
- ✓ No error messages in logs

## URLs
- Web App: http://your-vps-ip:5000
- Portainer: http://your-vps-ip:9000

## Files to Check
- `/opt/stock-analyzer/.env` - Database credentials
- `/opt/stock-analyzer/app.py` - Main application
- `/opt/stock-analyzer/logs/` - Log files