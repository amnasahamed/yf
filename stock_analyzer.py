import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import yfinance as yf
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
                            QVBoxLayout, QMessageBox, QHBoxLayout, QPushButton, QLabel, 
                            QCheckBox, QHeaderView, QWidget)
from PyQt5.QtCore import Qt, QTimer, QThreadPool, QRunnable, pyqtSignal, QObject
from PyQt5.QtGui import QColor
from ta.momentum import RSIIndicator
from ta.trend import MACD

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
REFRESH_INTERVAL = 3  # seconds
MAX_WORKERS = 5
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


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    data_ready = pyqtSignal(dict)  # Emits stock data when fetched
    error_occurred = pyqtSignal(str, str)  # Emits (symbol, error) on error
    finished = pyqtSignal()  # Emitted when the worker is done


class StockFetcher(QRunnable):
    """Worker class for fetching stock data in a separate thread."""
    
    class WorkerSignals(QObject):
        data_ready = pyqtSignal(dict)
        error_occurred = pyqtSignal(str, str)
    
    def __init__(self, symbol: str):
        super().__init__()
        self.symbol = symbol
        self.signals = self.WorkerSignals()
        self._is_running = True
        self._is_finished = False
    
    def stop(self):
        """Stop the worker."""
        self._is_running = False
    
    def isFinished(self):
        """Check if worker has finished."""
        return self._is_finished
    
    def run(self):
        """Fetch stock data and emit signals."""
        try:
            if not self._is_running:
                self._is_finished = True
                return
                
            stock = yf.Ticker(self.symbol)
            hist = stock.history(period="1d", interval="1m")
            
            if hist.empty:
                self.signals.error_occurred.emit(self.symbol, "No data returned")
                self._is_finished = True
                return
            
            # Calculate RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Calculate MACD
            exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
            exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            macd_hist = macd - signal
            
            # Get latest values
            last_row = hist.iloc[-1]
            
            data = {
                'symbol': self.symbol,
                'price': last_row['Close'],
                'rsi': rsi,
                'macd': macd.iloc[-1],
                'macd_signal': signal.iloc[-1],
                'macd_hist': macd_hist.iloc[-1],
                'volume': int(last_row['Volume']),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if self._is_running:
                self.signals.data_ready.emit(data)
                
        except Exception as e:
            if self._is_running:
                self.signals.error_occurred.emit(self.symbol, str(e))
        finally:
            self._is_finished = True


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
        return DEFAULT_STOCKS
    finally:
        if conn:
            conn.close()

class StockAnalyzerApp(QMainWindow):
    """Main application window for stock analysis."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Analyzer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize data
        self.stocks: Dict[str, StockData] = {}
        self.workers = []
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(MAX_WORKERS)
        self.sort_rsi_ascending = True  # Default sort order
        self.is_sorting = False  # Flag to prevent reentrant sorting
        
        # Load stocks from database
        self.stocks_to_track = fetch_stocks_from_db()
        logger.info(f"Tracking {len(self.stocks_to_track)} stocks")
        
        # Setup UI
        self.init_ui()
        
        # Start data refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_data()  # Initial load
        self.refresh_timer.start(REFRESH_INTERVAL * 1000)  # Convert to milliseconds
    
    def init_ui(self):
        """Initialize the user interface."""
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_btn)
        
        self.auto_refresh_cb = QCheckBox("Auto-refresh")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)
        controls_layout.addWidget(self.auto_refresh_cb)
        
        # Sort button for RSI
        self.sort_rsi_btn = QPushButton("Sort by RSI")
        self.sort_rsi_btn.clicked.connect(self.sort_by_rsi)
        controls_layout.addWidget(self.sort_rsi_btn)
        
        controls_layout.addStretch()
        
        # Status label
        self.status_label = QLabel("Ready")
        controls_layout.addWidget(self.status_label)
        
        layout.addLayout(controls_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Symbol", "Price", "RSI", "RSI Signal", 
            "MACD", "Crossover", "Histogram", "Volume"
        ])
        
        # Configure table properties
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        
        # Set initial column widths
        self.table.setColumnWidth(0, 100)  # Symbol
        self.table.setColumnWidth(1, 80)   # Price
        self.table.setColumnWidth(2, 60)   # RSI
        self.table.setColumnWidth(3, 90)   # RSI Signal
        self.table.setColumnWidth(4, 80)   # MACD
        self.table.setColumnWidth(5, 90)   # Crossover
        self.table.setColumnWidth(6, 80)   # Histogram
        self.table.setColumnWidth(7, 80)   # Volume
        
        layout.addWidget(self.table)
        
        # Set column widths
        self.table.setColumnWidth(0, 100)  # Symbol
        self.table.setColumnWidth(1, 80)   # Price
        self.table.setColumnWidth(2, 80)   # RSI
        self.table.setColumnWidth(3, 100)  # RSI Signal
        self.table.setColumnWidth(4, 100)  # MACD
        self.table.setColumnWidth(5, 100)  # Signal
        self.table.setColumnWidth(6, 100)  # Histogram
        self.table.setColumnWidth(7, 100)  # Volume
    
    def toggle_auto_refresh(self, state):
        """Toggle auto-refresh on/off."""
        if state == Qt.Checked:
            self.refresh_timer.start(REFRESH_INTERVAL * 1000)
            self.status_label.setText("Auto-refresh enabled")
        else:
            self.refresh_timer.stop()
            self.status_label.setText("Auto-refresh disabled")
    
    def refresh_data(self):
        """Refresh stock data for all symbols."""
        try:
            # Clear previous workers
            for worker in self.workers:
                try:
                    if hasattr(worker, 'stop'):
                        worker.stop()
                except Exception as e:
                    logger.error(f"Error stopping worker: {str(e)}")
            
            self.workers.clear()
            
            # Store current sort state
            was_sorted = hasattr(self, 'sort_rsi_ascending') and hasattr(self, 'is_sorting') and not self.is_sorting
            
            # Get current stocks from database
            stocks = fetch_stocks_from_db()
            
            # Create a worker for each stock
            for symbol in stocks:
                try:
                    worker = StockFetcher(symbol)
                    worker.signals.data_ready.connect(self.update_stock_data)
                    worker.signals.error_occurred.connect(self.handle_error)
                    self.workers.append(worker)
                    self.thread_pool.start(worker)
                except Exception as e:
                    logger.error(f"Error creating worker for {symbol}: {str(e)}")
            
            # Update status
            self.status_label.setText(f"Updated {len(stocks)} stocks")
            
            # Reapply sort if it was active
            if was_sorted:
                QTimer.singleShot(500, self._delayed_sort)  # Use the delayed sort wrapper
                
        except Exception as e:
            logger.error(f"Error in refresh_data: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
    
    def _delayed_sort(self):
        """Wrapper to ensure is_sorting is properly managed."""
        try:
            self._apply_rsi_sort()
        finally:
            self.is_sorting = False
    
    def sort_by_rsi(self):
        """Sort the table by RSI values."""
        if self.is_sorting:
            return
            
        self.is_sorting = True
        try:
            # Toggle sort order when manually triggered
            self.sort_rsi_ascending = not self.sort_rsi_ascending
            self._delayed_sort()
        except Exception as e:
            logger.error(f"Error in sort_by_rsi: {str(e)}")
            self.is_sorting = False
    
    def _apply_rsi_sort(self):
        """Apply the current RSI sort to the table."""
        try:
            if not hasattr(self, 'sort_rsi_ascending'):
                self.sort_rsi_ascending = True
                
            # Update button text
            sort_direction = "↑" if self.sort_rsi_ascending else "↓"
            self.sort_rsi_btn.setText(f"RSI {sort_direction}")
            
            # Get all rows data
            rows = []
            for row in range(self.table.rowCount()):
                try:
                    rsi_item = self.table.item(row, 2)  # RSI is in column 2
                    symbol_item = self.table.item(row, 0)  # Symbol is in column 0
                    
                    if rsi_item is None or symbol_item is None:
                        continue
                        
                    rsi_text = rsi_item.text()
                    if not rsi_text.strip():
                        continue
                        
                    rsi = float(rsi_text)
                    symbol = symbol_item.text()
                    rows.append((rsi, symbol, row))
                except (ValueError, AttributeError) as e:
                    continue
            
            if not rows:
                return
                
            # Sort based on RSI value
            rows.sort(key=lambda x: x[0], reverse=not self.sort_rsi_ascending)
        
            # Create a mapping of symbol to desired position
            symbol_pos = {symbol: idx for idx, (_, symbol, _) in enumerate(rows)}
            
            # Block signals to prevent UI updates during reordering
            self.table.blockSignals(True)
            
            try:
                # Create a list to store row data
                row_data = []
                for row in range(self.table.rowCount()):
                    symbol_item = self.table.item(row, 0)
                    if symbol_item is not None:
                        symbol = symbol_item.text()
                        if symbol in symbol_pos:
                            # Store all items in the row
                            items = []
                            for col in range(self.table.columnCount()):
                                item = self.table.takeItem(row, col)
                                if item is None:
                                    item = QTableWidgetItem("")
                                items.append(item)
                            row_data.append((symbol, items))
                
                # Clear the table
                self.table.setRowCount(0)
                
                # Sort the row data based on the desired order
                row_data.sort(key=lambda x: symbol_pos.get(x[0], float('inf')))
                
                # Rebuild the table in the correct order
                for row, (symbol, items) in enumerate(row_data):
                    self.table.insertRow(row)
                    for col, item in enumerate(items):
                        self.table.setItem(row, col, item)
                        
            finally:
                # Always unblock signals
                self.table.blockSignals(False)
                
        except Exception as e:
            logger.error(f"Error during sort: {str(e)}")
            # Ensure signals are unblocked even if an error occurs
            self.table.blockSignals(False)
    
    def update_stock_data(self, data: dict):
        """Update UI with new stock data with subtle refresh."""
        try:
            symbol = data['symbol']
            
            # Create or update stock data
            if symbol not in self.stocks:
                self.stocks[symbol] = StockData(symbol)
            
            stock = self.stocks[symbol]
            
            # Store current selection and scroll position
            current_row = self.table.currentRow()
            current_symbol = self.table.item(current_row, 0).text() if current_row >= 0 else None
            scroll_pos = self.table.verticalScrollBar().value()
            
            # Temporarily disable sorting while updating
            self.table.setSortingEnabled(False)
            
            # Update stock data
            price_changed = abs(stock.price - data['price']) > 0.01 if hasattr(stock, 'price') else True
            
            # Store previous MACD values for crossover detection
            if hasattr(stock, 'macd'):
                stock.update_macd_history()
            
            stock.price = data['price']
            stock.rsi = data['rsi']
            stock.macd = data['macd']
            stock.macd_signal = data['macd_signal']
            stock.macd_hist = data['macd_hist']
            stock.volume = data['volume']
            stock.timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
            
            # Find or create row
            row = -1
            for i in range(self.table.rowCount()):
                if self.table.item(i, 0).text() == symbol:
                    row = i
                    break
            
            row_created = False
            if row == -1:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(symbol))
                for col in range(1, 8):
                    self.table.setItem(row, col, QTableWidgetItem())
                row_created = True
            
            # Only update cells if the value changed or row was just created
            if row_created or price_changed:
                self.table.item(row, 1).setText(f"{stock.price:.2f}")
                self.table.item(row, 2).setText(f"{stock.rsi:.2f}")
                self.table.item(row, 3).setText(stock.rsi_signal)
                self.table.item(row, 4).setText(f"{stock.macd:.4f}")
                self.table.item(row, 5).setText(f"{stock.macd_signal:.4f}")
                self.table.item(row, 6).setText(f"{stock.macd_hist:.4f}")
                self.table.item(row, 7).setText(f"{stock.volume:,}")
                
                # Apply colors and update values
                # RSI Cell
                rsi_item = self.table.item(row, 2)
                if stock.rsi >= 70:
                    rsi_item.setBackground(QColor(255, 200, 200))  # Light red
                    rsi_item.setForeground(QColor(200, 0, 0))  # Dark red text
                elif stock.rsi >= 60:
                    rsi_item.setBackground(QColor(255, 230, 200))  # Light orange
                    rsi_item.setForeground(QColor(0, 0, 0))  # Black text
                elif stock.rsi <= 30:
                    rsi_item.setBackground(QColor(200, 255, 200))  # Light green
                    rsi_item.setForeground(QColor(0, 100, 0))  # Dark green text
                elif stock.rsi <= 40:
                    rsi_item.setBackground(QColor(230, 255, 200))  # Light yellow-green
                    rsi_item.setForeground(QColor(0, 0, 0))  # Black text
                else:
                    rsi_item.setBackground(QColor(240, 240, 240))  # Light gray
                    rsi_item.setForeground(QColor(0, 0, 0))  # Black text
                
                # MACD Crossover Cell
                crossover_item = self.table.item(row, 5)
                crossover_text = stock.macd_crossover
                crossover_item.setText(crossover_text)
                
                if "Bullish" in crossover_text:
                    crossover_item.setBackground(QColor(200, 255, 200))  # Light green
                    crossover_item.setForeground(QColor(0, 100, 0))  # Dark green text
                elif "Bearish" in crossover_text:
                    crossover_item.setBackground(QColor(255, 200, 200))  # Light red
                    crossover_item.setForeground(QColor(200, 0, 0))  # Dark red text
                elif "Above" in crossover_text:
                    crossover_item.setBackground(QColor(230, 255, 230))  # Very light green
                    crossover_item.setForeground(QColor(0, 100, 0))  # Dark green text
                elif "Below" in crossover_text:
                    crossover_item.setBackground(QColor(255, 230, 230))  # Very light red
                    crossover_item.setForeground(QColor(200, 0, 0))  # Dark red text
                else:
                    crossover_item.setBackground(QColor(240, 240, 240))  # Light gray
                    crossover_item.setForeground(QColor(0, 0, 0))  # Black text
                
                # MACD Histogram
                hist_item = self.table.item(row, 6)
                if stock.macd_hist > 0:
                    hist_item.setBackground(QColor(200, 255, 200))  # Light green
                    hist_item.setForeground(QColor(0, 100, 0))  # Dark green text
                else:
                    hist_item.setBackground(QColor(255, 200, 200))  # Light red
                    hist_item.setForeground(QColor(200, 0, 0))  # Dark red text
            
            # Don't re-enable sorting here to maintain our custom sort
            
            # Find and restore the previously selected symbol if it exists
            if current_symbol:
                for row in range(self.table.rowCount()):
                    if self.table.item(row, 0).text() == current_symbol:
                        self.table.selectRow(row)
                        break
            elif current_row >= 0 and current_row < self.table.rowCount():
                self.table.selectRow(min(current_row, self.table.rowCount() - 1))
                
            # Restore scroll position
            self.table.verticalScrollBar().setValue(scroll_pos)
            
            # Reapply sort if it was active
            if hasattr(self, 'sort_rsi_ascending') and not self.is_sorting:
                QTimer.singleShot(100, self._apply_rsi_sort)  # Small delay to allow UI to update
            
            # Update status less frequently to reduce flicker
            current_time = datetime.now()
            if not hasattr(self, 'last_status_update') or (current_time - self.last_status_update).total_seconds() >= 1:
                self.status_label.setText(f"Last update: {current_time.strftime('%H:%M:%S')}")
                self.last_status_update = current_time
            
        except Exception as e:
            logger.error(f"Error updating stock data: {e}")
    
    def handle_error(self, symbol: str, error: str):
        """Handle errors from worker threads."""
        error_msg = f"{symbol}: {error}"
        logger.error(error_msg)
        
        # Find or create row for the stock
        row = -1
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).text() == symbol:
                row = i
                break
        
        if row == -1:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(symbol))
            for col in range(1, 8):
                self.table.setItem(row, col, QTableWidgetItem("Error"))
        else:
            for col in range(1, 8):
                self.table.item(row, col).setText("Error")
        
        self.status_label.setText(f"Error updating {symbol}")
    
    def worker_finished(self):
        """Handle worker completion."""
        # Check if all workers are done
        if all(not worker.is_running for worker in self.workers):
            self.status_label.setText(f"Update complete at {datetime.now().strftime('%H:%M:%S')}")
    
    def closeEvent(self, event):
        """Handle application close."""
        # Stop all workers
        for worker in self.workers:
            worker.stop()
        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = StockAnalyzerApp()
    window.show()
    
    # Start event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()