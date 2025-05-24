# Stock Analyzer Web Application

A web-based application for analyzing stocks using RSI and MACD indicators with data from Yahoo Finance.

![Stock Analyzer Screenshot](https://i.imgur.com/e9MZJfL.jpg)

## Features

- Real-time stock data from Yahoo Finance API
- RSI (Relative Strength Index) calculations and visualization
- MACD (Moving Average Convergence Divergence) analysis
- Responsive web interface with Bootstrap
- Auto-refresh functionality
- Filtering by technical indicator states
- Sortable data tables
- PostgreSQL database integration

## Technology Stack

- **Backend**: Python, Flask
- **Data Analysis**: Pandas, NumPy, TA-Lib (Technical Analysis)
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Deployment**: Docker, Docker Compose

## Installation and Deployment

### Prerequisites

- Docker and Docker Compose
- PostgreSQL database with stock data in `pelago` table

### Quick Start with Docker

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/stock-analyzer.git
   cd stock-analyzer
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. Build and run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Access the application at:
   ```
   http://localhost:5000
   ```

### Manual Deployment

For manual deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

## Database Schema

The application expects a PostgreSQL database with a table named `pelago` that contains stock information with the following schema:

- `stock` (text): Stock symbol
- `date` (date): Date of the data point
- `open` (numeric): Opening price
- `high` (numeric): Highest price
- `low` (numeric): Lowest price
- `close` (numeric): Closing price
- `volume` (numeric): Trading volume

## Usage

- The application displays a table of stocks with their current prices and technical indicators
- Use the "Refresh Data" button to manually update all stock data
- Toggle auto-refresh with the checkbox
- Click on column headers to sort by that column
- Use the filter buttons to show only stocks with specific conditions (Overbought, Oversold, etc.)

## Development

1. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the Flask development server:
   ```bash
   python app.py
   ```

## License

MIT

## Acknowledgements

- [yfinance](https://github.com/ranaroussi/yfinance) for Yahoo Finance API access
- [TA-Lib](https://github.com/mrjbq7/ta-lib) for technical analysis functions
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Bootstrap](https://getbootstrap.com/) for the frontend UI components