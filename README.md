# Stock RSI & MACD Analyzer

A Python application that fetches stock data from a PostgreSQL database and performs technical analysis using RSI and MACD indicators.

## Features

- Fetches stock data from PostgreSQL database
- Calculates RSI (Relative Strength Index)
- Calculates MACD (Moving Average Convergence Divergence)
- Displays color-coded indicators
- Auto-refreshes every 5 minutes
- Sortable table view

## Prerequisites

- Python 3.7+
- PostgreSQL database with stock data in the `public.pelago` table
- Required Python packages (install using `pip install -r requirements.txt`)

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your database credentials:
   ```
   DB_HOST=your_database_host
   DB_PORT=5432
   DB_NAME=your_database_name
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_SCHEMA=public
   ```

## Database Schema

The application expects a table named `pelago` in the specified schema with at least these columns:
- `stock` (text): Stock symbol
- `date` (date): Date of the data point
- `open` (numeric): Opening price
- `high` (numeric): Highest price
- `low` (numeric): Lowest price
- `close` (numeric): Closing price
- `volume` (numeric): Trading volume

## Running the Application

```bash
python stock_analyzer.py
```

## Usage

- The application will automatically load today's stocks from the database
- Click on column headers to sort the table
- Use the "Refresh Data" button to manually update the information
- The table updates automatically every 5 minutes

## Indicators

- **RSI (Relative Strength Index)**: 
  - Above 70: Overbought (shown in red)
  - Below 30: Oversold (shown in green)
  - Between 30-70: Neutral (shown in black)

- **MACD (Moving Average Convergence Divergence)**:
  - Positive histogram: Bullish (green)
  - Negative histogram: Bearish (red)

## Troubleshooting

- If you see connection errors, verify your database credentials in the `.env` file
- Make sure the PostgreSQL server is running and accessible
- Check the error log at the bottom of the application window for specific error messages
