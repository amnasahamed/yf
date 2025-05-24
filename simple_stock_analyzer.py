import sys
import logging
import pandas as pd
import yfinance as yf
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
                           QVBoxLayout, QWidget, QHeaderView, QLabel, QPushButton,
                           QHBoxLayout, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor
from ta.momentum import RSIIndicator
from ta.trend import MACD
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class StockDataFetcher(QThread):
    """Worker thread for fetching stock data."""
    data_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str, str)
    progress = pyqtSignal(int)
    
    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol
        self._is_running = True
    
    def run(self):
        """Fetch data from yfinance and calculate indicators."""
        try:
            self.progress.emit(25)
            
            # Fetch data from yfinance
            stock = yf.Ticker(self.symbol)
            df = stock.history(period="1d", interval="1m")
            
            if df.empty:
                raise ValueError(f"No data found for {self.symbol}")
            
            self.progress.emit(50)
            
            # Calculate indicators
            close_prices = df['Close']
            
            # RSI
            rsi_indicator = RSIIndicator(close=close_prices, window=14)
            current_rsi = round(float(rsi_indicator.rsi().iloc[-1]), 2)
            
            # MACD
            macd_indicator = MACD(close=close_prices, window_fast=12, window_slow=26, window_sign=9)
            macd_line = macd_indicator.macd()
            signal_line = macd_indicator.macd_signal()
            
            current_macd = round(float(macd_line.iloc[-1]), 4)
            current_signal = round(float(signal_line.iloc[-1]), 4)
            current_hist = round(current_macd - current_signal, 4)
            
            self.progress.emit(75)
            
            # Prepare result
            result = {
                'symbol': self.symbol,
                'price': round(float(df['Close'].iloc[-1]), 2),
                'rsi': current_rsi,
                'macd': current_macd,
                'macd_signal': current_signal,
                'macd_hist': current_hist,
                'volume': int(df['Volume'].iloc[-1]),
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            
            self.progress.emit(100)
            self.data_ready.emit(result)
            
        except Exception as e:
            error_msg = f"Error processing {self.symbol}: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(self.symbol, error_msg)
        
    def stop(self):
        """Stop the thread."""
        self._is_running = False


class StockAnalyzerApp(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Analyzer")
        self.setGeometry(100, 100, 1000, 600)
        
        # List of stocks to track (NSE symbols with .NS suffix)
        self.stocks = ["INFY.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", 
                      "HINDUNILVR.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS"]
        
        # Track active workers
        self.workers = {}
        self.stock_data = {}
        
        self.init_ui()
        self.refresh_data()
        
        # Set up auto-refresh timer (every 30 seconds)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(30000)  # 30 seconds
    
    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("<h2>Stock Analyzer</h2>")
        header.addWidget(title)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        header.addWidget(self.refresh_btn)
        
        # Status label
        self.status_label = QLabel("Ready")
        header.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.hide()
        
        layout.addLayout(header)
        layout.addWidget(self.progress)
        
        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Price", "RSI", "MACD", "Signal", "Histogram", "Volume", "Last Updated"
        ])
        
        # Stretch columns
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        layout.addWidget(self.table)
    
    def refresh_data(self):
        """Refresh data for all stocks."""
        self.status_label.setText("Updating data...")
        self.progress.show()
        self.progress.setValue(0)
        
        # Clear existing workers
        for worker in self.workers.values():
            if worker.isRunning():
                worker.terminate()
        self.workers = {}
        
        # Start new workers for each stock
        for i, symbol in enumerate(self.stocks):
            worker = StockDataFetcher(symbol)
            worker.data_ready.connect(self.update_stock_data)
            worker.error_occurred.connect(self.handle_error)
            worker.progress.connect(self.update_progress)
            self.workers[symbol] = worker
            worker.start()
    
    def update_progress(self, value):
        """Update progress bar."""
        self.progress.setValue(value)
        if value == 100:
            self.status_label.setText("Ready")
            self.progress.hide()
    
    def update_stock_data(self, data):
        """Update the table with new stock data."""
        symbol = data['symbol']
        self.stock_data[symbol] = data
        
        # Find or create row for this stock
        row = self.stocks.index(symbol)
        
        # Update or add row
        if self.table.rowCount() <= row:
            self.table.insertRow(row)
            for col in range(self.table.columnCount()):
                self.table.setItem(row, col, QTableWidgetItem())
        
        # Set data
        self.table.item(row, 0).setText(symbol.replace(".NS", ""))
        self.table.item(row, 1).setText(f"₹{data['price']:,.2f}")
        self.table.item(row, 2).setText(f"{data['rsi']:.2f}")
        self.table.item(row, 3).setText(f"{data['macd']:.4f}")
        self.table.item(row, 4).setText(f"{data['macd_signal']:.4f}")
        self.table.item(row, 5).setText(f"{data['macd_hist']:+.4f}")
        self.table.item(row, 6).setText(f"{data['volume']:,}")
        self.table.item(row, 7).setText(data['timestamp'])
        
        # Color code RSI
        rsi = data['rsi']
        if rsi < 30:
            self.table.item(row, 2).setBackground(QColor(255, 220, 220))  # Light red for oversold
        elif rsi > 70:
            self.table.item(row, 2).setBackground(QColor(220, 255, 220))  # Light green for overbought
        else:
            self.table.item(row, 2).setBackground(Qt.white)
        
        # Color code MACD histogram
        hist = data['macd_hist']
        if hist > 0:
            self.table.item(row, 5).setBackground(QColor(220, 255, 220))  # Light green for positive
        else:
            self.table.item(row, 5).setBackground(QColor(255, 220, 220))  # Light red for negative
    
    def handle_error(self, symbol, error_msg):
        """Handle errors from worker threads."""
        logger.error(f"Error for {symbol}: {error_msg}")
        self.status_label.setText(f"Error updating {symbol}")
        
        # Show error in the table
        if symbol in self.stocks:
            row = self.stocks.index(symbol)
            if row < self.table.rowCount():
                for col in range(1, self.table.columnCount()):
                    if self.table.item(row, col):
                        self.table.item(row, col).setText("Error")
                        self.table.item(row, col).setBackground(QColor(255, 200, 200))
    
    def closeEvent(self, event):
        """Clean up on window close."""
        for worker in self.workers.values():
            if worker.isRunning():
                worker.terminate()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = StockAnalyzerApp()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
