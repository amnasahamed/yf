import os
import logging
import json
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD
from flask import Flask, render_template, jsonify, request

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
REFRESH_INTERVAL = 30  # seconds
DEFAULT_STOCKS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS"]

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'options': f'-c search_path={os.getenv("DB_SCHEMA", "public")}'
}


class StockData:
    """Class to hold stock data and calculate indicators."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.price = 0.0
        self.rsi = 0.0
        self.macd = 0.0
        self.macd_signal = 0.0
        self.macd_hist = 0.0
        self.volume = 0
        self.timestamp = datetime.now()
        self.prev_macd = 0.0
        self.prev_signal = 0.0
        self.error = None

    @property
    def rsi_signal(self) -> str:
        """Get RSI signal (Overbought/Oversold/Neutral)."""
        if self.rsi >= 70:
            return "Overbought"
        elif self.rsi <= 30:
            return "Oversold"
        return "Neutral"

    @property
    def macd_crossover(self) -> str:
        """Get MACD crossover signal."""
        if not hasattr(self, 'prev_macd') or not hasattr(self, 'prev_signal'):
            return "-"
            
        # Bullish crossover: MACD crosses above signal line
        if (self.prev_macd <= self.prev_signal and 
            self.macd > self.macd_signal):
            return "↑ Bullish"
        # Bearish crossover: MACD crosses below signal line
        elif (self.prev_macd >= self.prev_signal and 
              self.macd < self.macd_signal):
            return "↓ Bearish"
        # No crossover but MACD is above signal line
        elif self.macd > self.macd_signal:
            return "↑ Above"
        # No crossover but MACD is below signal line
        elif self.macd < self.macd_signal:
            return "↓ Below"
        return "-"
        
    def update_macd_history(self):
        """Update previous values for crossover detection."""
        self.prev_macd = self.macd
        self.prev_signal = self.macd_signal
        
    def to_dict(self):
        """Convert stock data to dictionary."""
        return {
            'symbol': self.symbol,
            'price': round(self.price, 2),
            'rsi': round(self.rsi, 2),
            'rsi_signal': self.rsi_signal,
            'macd': round(self.macd, 4),
            'macd_signal': round(self.macd_signal, 4),
            'macd_hist': round(self.macd_hist, 4),
            'macd_crossover': self.macd_crossover,
            'volume': self.volume,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'error': self.error
        }


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None


def ensure_nse_symbol(symbol: str) -> str:
    """Ensure the stock symbol has .NS suffix for NSE."""
    if not symbol.endswith('.NS'):
        return f"{symbol}.NS"
    return symbol


def fetch_stocks_from_db() -> List[str]:
    """Fetch unique stock symbols from the pelago table and ensure they're NSE symbols."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.warning("Could not connect to database, using default stocks")
            return [ensure_nse_symbol(s) for s in DEFAULT_STOCKS]
            
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT stock FROM pelago WHERE stock IS NOT NULL")
            stocks = [ensure_nse_symbol(row[0]) for row in cur.fetchall()]
            logger.info(f"Fetched {len(stocks)} stocks from database")
            return stocks if stocks else [ensure_nse_symbol(s) for s in DEFAULT_STOCKS]
    except Exception as e:
        logger.error(f"Error fetching stocks from database: {e}")
        return [ensure_nse_symbol(s) for s in DEFAULT_STOCKS]
    finally:
        if conn:
            conn.close()


def fetch_stock_data(symbol: str) -> Dict:
    """Fetch stock data and calculate indicators."""
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1d", interval="1m")
        
        if hist.empty:
            raise ValueError("No data returned")
        
        # Calculate RSI
        rsi_indicator = RSIIndicator(close=hist['Close'], window=14)
        rsi = rsi_indicator.rsi().iloc[-1]
        
        # Calculate MACD
        macd_indicator = MACD(close=hist['Close'], window_fast=12, window_slow=26, window_sign=9)
        macd = macd_indicator.macd().iloc[-1]
        signal = macd_indicator.macd_signal().iloc[-1]
        hist_value = macd - signal
        
        # Get latest values
        last_row = hist.iloc[-1]
        
        data = {
            'symbol': symbol,
            'price': last_row['Close'],
            'rsi': rsi,
            'macd': macd,
            'macd_signal': signal,
            'macd_hist': hist_value,
            'volume': int(last_row['Volume']),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return {
            'symbol': symbol,
            'error': str(e)
        }


# Flask application
app = Flask(__name__)

# Global data store
stock_data_store = {}


def background_update():
    """Background task to update stock data periodically."""
    while True:
        try:
            stocks = fetch_stocks_from_db()
            logger.info(f"Updating data for {len(stocks)} stocks")
            
            for symbol in stocks:
                try:
                    data = fetch_stock_data(symbol)
                    if 'error' in data:
                        if symbol in stock_data_store:
                            stock_data_store[symbol].error = data['error']
                    else:
                        if symbol not in stock_data_store:
                            stock_data_store[symbol] = StockData(symbol)
                        
                        stock = stock_data_store[symbol]
                        stock.update_macd_history()
                        stock.price = data['price']
                        stock.rsi = data['rsi']
                        stock.macd = data['macd']
                        stock.macd_signal = data['macd_signal']
                        stock.macd_hist = data['macd_hist']
                        stock.volume = data['volume']
                        stock.timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
                        stock.error = None
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    if symbol in stock_data_store:
                        stock_data_store[symbol].error = str(e)
            
            logger.info(f"Updated {len(stock_data_store)} stocks successfully")
        except Exception as e:
            logger.error(f"Error in background update: {str(e)}")
        
        time.sleep(REFRESH_INTERVAL)


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/api/stocks')
def get_stocks():
    """Return all stock data as JSON."""
    sort_by = request.args.get('sort_by', 'symbol')
    sort_order = request.args.get('sort_order', 'asc')
    
    # Convert stock data to list of dictionaries
    stocks_list = [stock.to_dict() for stock in stock_data_store.values()]
    
    # Sort the list
    reverse = sort_order.lower() == 'desc'
    if sort_by == 'symbol':
        stocks_list.sort(key=lambda x: x['symbol'], reverse=reverse)
    elif sort_by == 'price':
        stocks_list.sort(key=lambda x: x['price'], reverse=reverse)
    elif sort_by == 'rsi':
        stocks_list.sort(key=lambda x: x['rsi'], reverse=reverse)
    elif sort_by == 'macd':
        stocks_list.sort(key=lambda x: x['macd'], reverse=reverse)
    elif sort_by == 'volume':
        stocks_list.sort(key=lambda x: x['volume'], reverse=reverse)
    
    return jsonify({
        'stocks': stocks_list,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@app.route('/api/stock/<symbol>')
def get_stock(symbol):
    """Return data for a single stock."""
    symbol = ensure_nse_symbol(symbol)
    if symbol in stock_data_store:
        return jsonify(stock_data_store[symbol].to_dict())
    else:
        return jsonify({'error': f'Stock {symbol} not found'}), 404


@app.route('/api/refresh', methods=['POST'])
def refresh_stocks():
    """Manually trigger a refresh of all stock data."""
    try:
        stocks = fetch_stocks_from_db()
        
        for symbol in stocks:
            try:
                data = fetch_stock_data(symbol)
                if 'error' in data:
                    if symbol in stock_data_store:
                        stock_data_store[symbol].error = data['error']
                else:
                    if symbol not in stock_data_store:
                        stock_data_store[symbol] = StockData(symbol)
                    
                    stock = stock_data_store[symbol]
                    stock.update_macd_history()
                    stock.price = data['price']
                    stock.rsi = data['rsi']
                    stock.macd = data['macd']
                    stock.macd_signal = data['macd_signal']
                    stock.macd_hist = data['macd_hist']
                    stock.volume = data['volume']
                    stock.timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
                    stock.error = None
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                if symbol in stock_data_store:
                    stock_data_store[symbol].error = str(e)
        
        return jsonify({
            'success': True,
            'message': f'Refreshed {len(stock_data_store)} stocks',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        logger.error(f"Error in manual refresh: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 500


if __name__ == '__main__':
    # Start background update thread
    update_thread = threading.Thread(target=background_update, daemon=True)
    update_thread.start()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)