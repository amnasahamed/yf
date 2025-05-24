import sys
import os
import psycopg2
import pandas as pd
import yfinance as yf
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, 
                           QProgressBar, QMessageBox, QCheckBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QTime, QCoreApplication
from PyQt5 import QtGui
from ta.momentum import RSIIndicator
from ta.trend import MACD
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Validate required environment variables
required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    error_msg = f"Error: Missing required environment variables: {', '.join(missing_vars)}"
    print(error_msg)
    sys.exit(1)

class StockDatabase:
    def __init__(self):
        try:
            self.conn_params = {
                'host': os.getenv('DB_HOST'),
                'port': os.getenv('DB_PORT'),
                'database': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD')
            }
            self.conn = None
            self.connect()
            print("Successfully connected to PostgreSQL database")
        except Exception as e:
            print(f"Failed to connect to database: {e}")
            raise
    
    def connect(self):
        """Establish a connection to the database"""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            self.conn = None
            return False
    
    def get_todays_stocks(self):
        """Fetch stocks for the current date from the pelago table"""
        if not self.conn or self.conn.closed != 0:
            if not self.connect():
                return []
        
        try:
            query = """
                SELECT DISTINCT stock, MAX(date) as last_trade_date
                FROM public.pelago 
                WHERE date = %s
                GROUP BY stock
                ORDER BY stock
            """
            
            with self.conn.cursor() as cur:
                cur.execute(query, (date.today(),))
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                
                # Convert to list of dicts
                result = []
                for row in rows:
                    result.append(dict(zip(columns, row)))
                
                print(f"Fetched {len(result)} stocks from database")
                return result
                
        except Exception as e:
            print(f"Error fetching today's stocks: {e}")
            return []
    
    def get_stock_history(self, symbol, days=30):
        """Fetch historical data for a specific stock"""
        if not self.conn or self.conn.closed != 0:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            query = """
                SELECT date, open, high, low, close, volume
                FROM public.pelago
                WHERE stock = %s
                ORDER BY date DESC
                LIMIT %s
            """
            
            with self.conn.cursor() as cur:
                cur.execute(query, (symbol, days))
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                
                if not rows:
                    print(f"No data found for {symbol}")
                    return pd.DataFrame()
                    
                # Convert to DataFrame
                df = pd.DataFrame(rows, columns=columns)
                df.set_index('date', inplace=True)
                df.sort_index(inplace=True)  # Ensure chronological order
                print(f"Fetched {len(df)} days of data for {symbol}")
                return df
                
        except Exception as e:
            print(f"Error fetching history for {symbol}: {e}")
            return pd.DataFrame()
    
    def close(self):
        """Close the database connection"""
        if self.conn and self.conn.closed == 0:
            self.conn.close()

class StockDataFetcher(QThread):
    """Worker thread for fetching stock data"""
    data_ready = pyqtSignal(dict)
    
    def __init__(self, symbol, db):
        super().__init__()
        self.symbol = symbol
        self.db = db
    
    def run(self):
        try:
            # Get historical data from database
            history = self.db.get_stock_history(self.symbol, days=30)
            
            if history.empty:
                # Fallback to yfinance if no data in database
                stock = yf.Ticker(f"{self.symbol}.NS")
                history = stock.history(period="30d")
                
                if history.empty:
                    raise ValueError(f"No data available for {self.symbol}")
            
            # Calculate RSI
            rsi_indicator = RSIIndicator(close=history['close'] if 'close' in history else history['Close'])
            rsi = rsi_indicator.rsi()
            current_rsi = rsi.iloc[-1]
            
            # Calculate MACD
            macd = MACD(close=history['close'] if 'close' in history else history['Close'])
            current_macd = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]
            macd_hist = macd.macd_diff().iloc[-1]
            
            # Get current price
            current_price = (history['close'] if 'close' in history else history['Close']).iloc[-1]
            
            # Prepare result
            result = {
                'symbol': self.symbol,
                'price': current_price,
                'rsi': current_rsi,
                'macd': current_macd,
                'macd_signal': macd_signal,
                'macd_hist': macd_hist,
                'timestamp': datetime.now(),
                'error': None
            }
            
        except Exception as e:
            result = {
                'symbol': self.symbol,
                'error': str(e)
            }
        
        self.data_ready.emit(result)

class StockDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📈 Stock RSI & MACD Analyzer (PostgreSQL)")
        self.setGeometry(100, 100, 1200, 900)
        
        # Database connection
        self.db = StockDatabase()
        self.stocks = []
        self.workers = []
        self.last_update_time = None
        self.sort_column = 2  # Default sort by RSI
        self.sort_order = Qt.DescendingOrder  # Default sort order
        
        # Initialize UI
        self.init_ui()
        
        # Load initial data
        self.load_todays_stocks()
        
        # Set up auto-refresh timer (3 seconds)
        self.refresh_interval = 3000  # 3 seconds in milliseconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh_data)
        self.refresh_timer.start(self.refresh_interval)
        self.next_refresh_time = QTime.currentTime().addMSecs(self.refresh_interval)
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Status bar
        status_bar = QHBoxLayout()
        self.status_label = QLabel("Last update: Never")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        status_bar.addWidget(self.status_label)
        status_bar.addStretch()
        
        # Auto-refresh toggle
        self.auto_refresh_check = QCheckBox("Auto-refresh (30s)")
        self.auto_refresh_check.setChecked(True)
        self.auto_refresh_check.stateChanged.connect(self.toggle_auto_refresh)
        status_bar.addWidget(self.auto_refresh_check)
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh Now")
        self.refresh_btn.clicked.connect(self.manual_refresh)
        status_bar.addWidget(self.refresh_btn)
        
        layout.addLayout(status_bar)
        
        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(6)  # Removed Hist column
        self.table.setHorizontalHeaderLabels(["Symbol", "Price", "RSI", "RSI Signal", "MACD", "Signal"])
        self.table.setSortingEnabled(True)
        
        # Enable sorting with custom handler
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        
        # Set column widths and properties
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, header.Stretch)  # Symbol
        header.setSectionResizeMode(1, header.ResizeToContents)  # Price
        header.setSectionResizeMode(2, header.ResizeToContents)  # RSI
        header.setSectionResizeMode(3, header.ResizeToContents)  # RSI Signal
        header.setSectionResizeMode(4, header.ResizeToContents)  # MACD
        header.setSectionResizeMode(5, header.ResizeToContents)  # Signal
        
        layout.addWidget(self.table)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # Error log
        self.error_log = QTextEdit()
        self.error_log.setReadOnly(True)
        self.error_log.setMaximumHeight(100)
        self.error_log.setStyleSheet("background: #f8f9fa; color: #dc3545; font-family: monospace;")
        layout.addWidget(self.error_log)
        
        self.setLayout(layout)
        
    def on_header_clicked(self, column):
        """Handle header click for sorting"""
        if self.sort_column == column:
            # Toggle sort order if clicking the same column
            self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            # Default to descending for RSI, ascending for others
            self.sort_order = Qt.DescendingOrder if column == 2 else Qt.AscendingOrder
            self.sort_column = column
        
        self.sort_table()
    
    def sort_table(self):
        """Sort the table based on the current sort column and order"""
        if self.table.rowCount() == 0:
            return
            
        self.table.sortItems(self.sort_column, self.sort_order)
    
    def toggle_auto_refresh(self, state):
        """Toggle auto-refresh on/off"""
        if state == Qt.Checked:
            self.refresh_timer.start(self.refresh_interval)
            self.next_refresh_time = QTime.currentTime().addMSecs(self.refresh_interval)
            self.refresh_btn.setText("🔄 Refresh Now")
            self.status_label.setText("Auto-refresh enabled")
        else:
            self.refresh_timer.stop()
            self.refresh_btn.setText("🔄 Manual Refresh")
            self.status_label.setText("Auto-refresh disabled")
            
        QCoreApplication.processEvents()  # Update UI immediately
    
    def manual_refresh(self):
        """Handle manual refresh button click"""
        if self.auto_refresh_check.isChecked():
            # If auto-refresh is on, just force an immediate refresh
            self.refresh_timer.stop()
            self.auto_refresh_data()
            self.refresh_timer.start(self.refresh_interval)
        else:
            # If auto-refresh is off, just do a single refresh
            self.load_todays_stocks()
    
    def auto_refresh_data(self):
        """Handle auto-refresh timer timeout"""
        if not self.auto_refresh_check.isChecked():
            return
            
        current_time = QTime.currentTime()
        if current_time >= self.next_refresh_time:
            print(f"Auto-refreshing data at {current_time.toString('hh:mm:ss')}...")
            self.next_refresh_time = current_time.addMSecs(self.refresh_interval)
            self.load_todays_stocks()
            
            # Update status with next refresh time
            if hasattr(self, 'last_update_time') and self.last_update_time:
                next_refresh = current_time.addMSecs(self.refresh_interval)
                self.status_label.setText(
                    f"Last update: {self.last_update_time.strftime('%H:%M:%S')} | "
                    f"Next refresh: {next_refresh.toString('hh:mm:ss')}"
                )
                
            QCoreApplication.processEvents()  # Keep UI responsive
    
    def load_todays_stocks(self, force_full_refresh=False):
        """Load stocks for today from the database"""
        try:
            self.refresh_btn.setEnabled(False)
            self.progress.show()
            
            if force_full_refresh:
                self.error_log.clear()
            
            # Get current sort state
            if not force_full_refresh and hasattr(self, 'sort_column'):
                prev_sort_column = self.sort_column
                prev_sort_order = self.sort_order
            
            # Clear existing workers
            for worker in self.workers:
                if worker.isRunning():
                    worker.terminate()
            self.workers = []
            
            # Force a database reconnection
            if self.db.conn:
                self.db.conn.close()
            self.db.connect()
            
            # Get today's stocks
            stocks = self.db.get_todays_stocks()
            
            if not stocks:
                self.error_log.append("No stocks found for today's date.")
                self.progress.hide()
                self.refresh_btn.setEnabled(True)
                return
            
            # Create a set of current symbols for faster lookup
            current_symbols = {stock['symbol'] for stock in self.stocks}
            new_stocks = []
            
            # Process new and existing stocks
            for i, stock in enumerate(stocks):
                symbol = stock['stock']
                
                if symbol not in current_symbols:
                    # Add new stock
                    row = len(self.stocks)
                    self.stocks.append({
                        'symbol': symbol,
                        'row': row,
                        'data': None
                    })
                    
                    # Add new row to table
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(symbol))
                    for col in range(1, 7):
                        self.table.setItem(row, col, QTableWidgetItem("Loading..."))
                    
                    new_stocks.append((row, symbol))
                else:
                    # Update existing stock
                    existing = next(s for s in self.stocks if s['symbol'] == symbol)
                    existing['data'] = None  # Mark for update
                    
                    # Update loading status
                    for col in range(1, 7):
                        if self.table.item(existing['row'], col):
                            self.table.item(existing['row'], col).setText("Updating...")
                    
                    new_stocks.append((existing['row'], symbol))
            
            # Start worker for each stock that needs updating
            for row, symbol in new_stocks:
                worker = StockDataFetcher(symbol, self.db)
                worker.data_ready.connect(self.update_stock_data)
                worker.start()
                self.workers.append(worker)
            
            self.status_label.setText(f"Updating {len(new_stocks)} stocks...")
            
            # Restore sort state if this is a refresh
            if not force_full_refresh and hasattr(self, 'sort_column'):
                self.sort_column = prev_sort_column
                self.sort_order = prev_sort_order
                QTimer.singleShot(100, self.sort_table)
            
        except Exception as e:
            error_msg = f"Error loading stocks: {str(e)}"
            self.error_log.append(error_msg)
            print(error_msg)
            self.progress.hide()
            self.refresh_btn.setEnabled(True)
    
    def update_stock_data(self, data):
        """Update the table with stock data"""
        try:
            symbol = data['symbol']
            
            # Find the stock in our list
            stock = next((s for s in self.stocks if s['symbol'] == symbol), None)
            if not stock:
                print(f"Stock {symbol} not found in current view")
                return
                
            row = stock['row']
            
            if 'error' in data and data['error']:
                # Show error in table (only 5 columns now)
                for col in range(1, 6):
                    if self.table.item(row, col):
                        self.table.item(row, col).setText("Error")
                        self.table.item(row, col).setForeground(Qt.red)
                error_msg = f"{symbol}: {data['error']}"
                self.error_log.append(error_msg)
                print(error_msg)
            else:
                # Update with data
                # Price
                self.table.item(row, 1).setText(f"{data['price']:.2f}")
                
                # RSI
                rsi = data['rsi']
                rsi_item = self.table.item(row, 2)
                rsi_item.setText(f"{rsi:.2f}")
                
                # RSI Signal
                rsi_signal = ""
                if rsi > 70:
                    rsi_signal = "⬇️ Overbought"
                    rsi_item.setForeground(Qt.red)
                elif rsi < 30:
                    rsi_signal = "⬆️ Oversold"
                    rsi_item.setForeground(Qt.darkGreen)
                else:
                    rsi_signal = "➡️ Neutral"
                    rsi_item.setForeground(Qt.black)
                
                self.table.item(row, 3).setText(rsi_signal)
                
                # MACD values (removed histogram)
                macd = data['macd']
                macd_signal = data['macd_signal']
                
                # Color MACD values based on signal line crossover
                macd_item = self.table.item(row, 4)
                signal_item = self.table.item(row, 5)
                
                macd_item.setText(f"{macd:.4f}")
                signal_item.setText(f"{macd_signal:.4f}")
                
                # Color based on MACD vs Signal line
                if macd > macd_signal:
                    macd_item.setForeground(Qt.darkGreen)
                    signal_item.setForeground(Qt.darkGreen)
                else:
                    macd_item.setForeground(Qt.red)
                    signal_item.setForeground(Qt.red)
                
                # Store the data
                stock['data'] = data
            
            # Check if all workers are done
            if all(s.get('data') is not None or 'error' in s for s in self.stocks):
                self.update_complete()
                
        except Exception as e:
            self.error_log.append(f"Error updating UI: {str(e)}")
    
    def update_complete(self):
        """Called when all stock data has been updated"""
        try:
            # Check if all workers are done
            if all(not worker.isRunning() for worker in self.workers):
                self.progress.hide()
                self.refresh_btn.setEnabled(True)
                self.last_update_time = datetime.now()
                update_time = self.last_update_time.strftime('%H:%M:%S')
                
                # Sort the table if we have data
                if self.table.rowCount() > 0 and self.table.columnCount() > self.sort_column:
                    self.sort_table()
                
                # Update status with next refresh time if auto-refresh is enabled
                if self.auto_refresh_check.isChecked():
                    next_refresh = QTime.currentTime().addMSecs(self.refresh_interval)
                    last_update = self.last_update_time.strftime('%H:%M:%S') if self.last_update_time else "Never"
                    self.status_label.setText(
                        f"Last update: {last_update} | "
                        f"Next refresh: {next_refresh.toString('hh:mm:ss')}"
                    )
                else:
                    last_update = self.last_update_time.strftime('%H:%M:%S') if self.last_update_time else "Never"
                    self.status_label.setText(f"Last update: {last_update}")
                
                print(f"Update completed at {update_time}")
                
                # Process any pending events to keep UI responsive
                QCoreApplication.processEvents()
        except Exception as e:
            error_msg = f"Error in update_complete: {str(e)}"
            print(error_msg)
            self.error_log.append(error_msg)
            self.progress.hide()
            self.refresh_btn.setEnabled(True)
    
    def closeEvent(self, event):
        """Clean up on window close"""
        for worker in self.workers:
            if worker.isRunning():
                worker.terminate()
        self.db.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show the main window
    window = StockDashboard()
    window.show()
    
    # Run the application
    sys.exit(app.exec_())
