import yfinance as yf
import pandas as pd
import mplfinance as mpf
from datetime import datetime, timedelta
import time
import os

# File paths for logs and trades
LOG_FILE = "live_log.txt"
TRADES_FILE = "trades.csv"

# Initialize log file
with open(LOG_FILE, "w") as f:
    f.write("Starting Live Trading Bot...\n")

class LiveTradingBot:
    def __init__(self, symbol, stop_loss_percent=0.1, take_profit_percent=0.2, max_hold_minutes=5, interval='1m'):
        self.symbol = symbol
        self.stop_loss_percent = stop_loss_percent / 100
        self.take_profit_percent = take_profit_percent / 100
        self.max_hold_minutes = max_hold_minutes
        self.interval = interval  
        self.position = None
        self.entry_price = 0
        self.entry_time = None
        self.data = pd.DataFrame()
        self.buy_signals = []
        self.sell_signals = []
        self.trades = []
        self.is_running = False

    def log(self, message):
        """Log messages to the log file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"
        print(log_message)
        with open(LOG_FILE, "a") as f:
            f.write(log_message)

    def get_live_data(self):
        """Fetch latest data from yfinance"""
        try:
            stock = yf.Ticker(self.symbol)
            period = '1d'
            self.data = stock.history(period=period, interval=self.interval)
            if not self.data.empty:
                self.log(f"Fetched {len(self.data)} rows of {self.interval} data")
        except Exception as e:
            self.log(f"Data fetch error: {e}")

    def calculate_signals(self, current_price, timestamp):
        """Trading logic with SL/TP"""
        if self.position is None:
            return 'BUY'
        elif self.position == 'LONG':
            if current_price <= self.entry_price * (1 - self.stop_loss_percent):
                return 'SELL'
            elif current_price >= self.entry_price * (1 + self.take_profit_percent):
                return 'SELL'
            
            hold_time = (timestamp - self.entry_time).total_seconds() / 60
            if hold_time >= self.max_hold_minutes:
                return 'SELL'
            return 'HOLD'
        return 'HOLD'

    def execute_trade(self, signal, current_price, timestamp):
        """Execute trades"""
        if signal == 'BUY' and self.position is None:
            self.position = 'LONG'
            self.entry_price = current_price
            self.entry_time = timestamp
            self.buy_signals.append((timestamp, current_price))
            self.log(f"BUY executed at {current_price} on {timestamp}")
            self.trades.append({'type': 'BUY', 'price': current_price, 'timestamp': timestamp})

        elif signal == 'SELL' and self.position == 'LONG':
            profit = current_price - self.entry_price
            exit_reason = "Take Profit" if current_price >= self.entry_price * (1 + self.take_profit_percent) else "Stop Loss"
            self.position = None
            self.sell_signals.append((timestamp, current_price))
            self.log(f"SELL executed at {current_price} on {timestamp}, Profit: {profit}, Reason: {exit_reason}")
            self.trades.append({'type': 'SELL', 'price': current_price, 'timestamp': timestamp, 'profit': profit, 'reason': exit_reason})

            # Save trades to CSV
            pd.DataFrame(self.trades).to_csv(TRADES_FILE, index=False)

    def run(self):
        """Main live trading loop"""
        self.is_running = True
        self.log(f"Starting bot for {self.symbol} with {self.interval} interval")

        while self.is_running:
            self.get_live_data()
            
            if not self.data.empty:
                current_price = self.data['Close'].iloc[-1]
                current_time = self.data.index[-1]

                signal = self.calculate_signals(current_price, current_time)
                self.execute_trade(signal, current_price, current_time)

            time.sleep(60 if self.interval == '1m' else 900)

    def stop(self):
        """Stop the bot"""
        self.is_running = False
        self.log("Bot stopped manually")
