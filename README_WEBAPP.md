# Stock Analyzer Web Application

This is a web-based version of the Stock Analyzer application that provides real-time RSI and MACD indicators for stocks.

## Features

- Real-time stock data analysis with Yahoo Finance API
- RSI (Relative Strength Index) calculation
- MACD (Moving Average Convergence Divergence) analysis
- Responsive web interface with Bootstrap
- Auto-refresh functionality
- Filtering and sorting capabilities
- Docker containerization for easy deployment

## Prerequisites

- Docker installed on your server
- Portainer (as mentioned in your requirements)
- Access to your VPS
- PostgreSQL database with stock data (same as the desktop application)

## Deployment Instructions

### Option 1: Using Docker Compose (Recommended for Portainer)

1. Upload the entire `yfinance v3` directory to your VPS

2. Navigate to the directory:
   ```bash
   cd yfinance\ v3/
   ```

3. Make sure the `.env` file contains your database credentials:
   ```
   DB_HOST=your_database_host
   DB_PORT=5432
   DB_NAME=your_database_name
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_SCHEMA=public
   ```

4. In Portainer:
   - Go to "Stacks" in the sidebar
   - Click "Add stack"
   - Name your stack (e.g., "stock-analyzer")
   - In the "Web editor" tab, either:
     - Upload the docker-compose.yml file, or
     - Copy and paste the contents of the docker-compose.yml file
   - Click "Deploy the stack"

### Option 2: Building and Running with Docker CLI

1. Upload the entire `yfinance v3` directory to your VPS

2. Navigate to the directory:
   ```bash
   cd yfinance\ v3/
   ```

3. Build the Docker image:
   ```bash
   docker build -t stock-analyzer .
   ```

4. Run the container:
   ```bash
   docker run -d \
     --name stock-analyzer \
     -p 5000:5000 \
     --restart unless-stopped \
     --env-file .env \
     stock-analyzer
   ```

## Accessing the Application

Once deployed, access the Stock Analyzer web application by navigating to:

```
http://your-server-ip:5000
```

Replace `your-server-ip` with the IP address or hostname of your VPS.

## Features and Usage

- **Auto-refresh**: The application automatically refreshes stock data every 30 seconds. This can be toggled on/off.
- **Manual Refresh**: Click the "Refresh Data" button to manually update all stock data.
- **Sorting**: Click on column headers to sort by that column (e.g., sort by RSI value).
- **Filtering**: Use the filter buttons to show only stocks with specific conditions:
  - Overbought (RSI > 70)
  - Oversold (RSI < 30)
  - Bullish (MACD crossed above signal)
  - Bearish (MACD crossed below signal)

## Troubleshooting

- **Application not accessible**: Ensure port 5000 is open on your VPS firewall.
- **Database connection error**: Verify the database credentials in the `.env` file.
- **Data not loading**: Check if your database has the correct schema and table (`pelago`).

## Logs

Container logs can be viewed in Portainer by:
1. Going to "Containers" in the sidebar
2. Finding and clicking on the "stock-analyzer" container
3. Selecting the "Logs" tab