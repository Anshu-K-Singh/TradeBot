import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime, timedelta
import time
import os

class LiveTradingBot:
    def __init__(self, symbol, stop_loss_percent=0.1, take_profit_percent=0.2, max_hold_minutes=5, interval='1m'):
        self.symbol = symbol
        self.stop_loss_percent = stop_loss_percent / 100
        self.take_profit_percent = take_profit_percent / 100
        self.max_hold_minutes = max_hold_minutes
        self.interval = interval  # '1m' or '15m'
        self.position = None
        self.entry_price = 0
        self.entry_time = None
        self.data = pd.DataFrame()
        self.buy_signals = []
        self.sell_signals = []
        self.trades = []
        self.is_running = False
        self.interval_minutes = 1 if interval == '1m' else 15
        
    def get_live_data(self):
        """Fetch latest data from yfinance"""
        try:
            stock = yf.Ticker(self.symbol)
            # Fetch 1 day of data to get enough history, take latest candles
            period = '1d'
            self.data = stock.history(period=period, interval=self.interval)
            if not self.data.empty:
                print(f"Fetched {len(self.data)} rows of {self.interval} data")
            return self.data
        except Exception as e:
            print(f"Data fetch error: {e}")
            return pd.DataFrame()

    def calculate_signals(self, current_price, timestamp):
        """Trading logic with fixed SL/TP and time-based exit"""
        if self.position is None:
            return 'BUY'
        elif self.position == 'LONG':
            if current_price <= self.entry_price * (1 - self.stop_loss_percent):
                return 'SELL'
            elif current_price >= self.entry_price * (1 + self.take_profit_percent):
                return 'SELL'
            hold_time = (timestamp - self.entry_time).total_seconds() / 60
            if hold_time >= self.max_hold_minutes * self.interval_minutes:
                return 'SELL'
            return 'HOLD'
        return 'HOLD'
    
    def execute_trade(self, signal, current_price, timestamp):
        """Execute trading decisions (simulated)"""
        if signal == 'BUY' and self.position is None:
            self.position = 'LONG'
            self.entry_price = current_price
            self.entry_time = timestamp
            self.buy_signals.append((timestamp, current_price))
            print(f"BUY executed at {current_price} on {timestamp}")
            self.trades.append({'type': 'BUY', 'price': current_price, 'timestamp': timestamp})
            
        elif signal == 'SELL' and self.position == 'LONG':
            profit = current_price - self.entry_price
            hold_time = (timestamp - self.entry_time).total_seconds() / 60
            if current_price >= self.entry_price * (1 + self.take_profit_percent):
                exit_reason = "Take Profit"
            elif current_price <= self.entry_price * (1 - self.stop_loss_percent):
                exit_reason = "Stop Loss"
            else:
                exit_reason = "Time Exit"
            self.position = None
            self.sell_signals.append((timestamp, current_price))
            print(f"SELL executed at {current_price} on {timestamp}, Profit: {profit}, Reason: {exit_reason}")
            self.trades.append({'type': 'SELL', 'price': current_price, 'timestamp': timestamp, 'profit': profit, 'reason': exit_reason})

    def plot_candlestick(self):
        """Generate live candlestick chart"""
        if self.data.empty:
            return
        
        plot_data = self.data.tail(50)  # Last 50 candles for visibility
        buy_plot = pd.Series(index=plot_data.index, dtype=float)
        sell_plot = pd.Series(index=plot_data.index, dtype=float)
        
        for timestamp, price in self.buy_signals[-10:]:  # Last 10 signals
            if timestamp in buy_plot.index:
                buy_plot.loc[timestamp] = price
        for timestamp, price in self.sell_signals[-10:]:
            if timestamp in sell_plot.index:
                sell_plot.loc[timestamp] = price
        
        ap = []
        if buy_plot.notna().any():
            ap.append(mpf.make_addplot(buy_plot, type='scatter', markersize=100, marker='^', color='green'))
        if sell_plot.notna().any():
            ap.append(mpf.make_addplot(sell_plot, type='scatter', markersize=100, marker='v', color='red'))
        
        plt.clf()
        mpf.plot(plot_data, 
                 type='candle',
                 style='yahoo',
                 title=f'{self.symbol} - {self.interval} Live (SL: {self.stop_loss_percent*100}%, TP: {self.take_profit_percent*100}%)',
                 ylabel='Price',
                 addplot=ap,
                 volume=True,
                 savefig=f'{self.symbol}_{self.interval}_live_chart.png')

    def run(self):
        """Main live trading loop"""
        self.is_running = True
        print(f"Starting live trading bot for {self.symbol} with {self.interval} interval")
        
        # CSV file for logging trades
        csv_filename = f"{self.symbol}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{self.interval}_trades.csv"
        
        while self.is_running:
            try:
                self.get_live_data()
                if not self.data.empty:
                    current_price = self.data['Close'].iloc[-1]
                    current_time = self.data.index[-1]
                    
                    signal = self.calculate_signals(current_price, current_time)
                    self.execute_trade(signal, current_price, current_time)
                    
                    self.plot_candlestick()
                    
                    print(f"Time: {datetime.now()}, Price: {current_price}, Position: {self.position}, Trades: {len([t for t in self.trades if t['type'] == 'SELL'])}")
                    
                    # Append trades to CSV
                    trades_df = pd.DataFrame(self.trades)
                    trades_df.to_csv(csv_filename, index=False)
                
                # Sleep for interval duration (60s for 1m, 900s for 15m)
                sleep_time = 60 if self.interval == '1m' else 900
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)  # Retry after 1 minute on error

    def stop(self):
        """Stop the bot and close open position"""
        self.is_running = False
        if self.position == 'LONG' and not self.data.empty:
            current_price = self.data['Close'].iloc[-1]
            profit = current_price - self.entry_price
            self.position = None
            self.sell_signals.append((datetime.now(), current_price))
            print(f"SELL executed at {current_price} on {datetime.now()}, Profit: {profit}, Reason: Manual Stop")
            self.trades.append({'type': 'SELL', 'price': current_price, 'timestamp': datetime.now(), 'profit': profit, 'reason': 'Manual Stop'})

# Example usage
if __name__ == "__main__":
    # Choose interval: '1m' or '15m'
    bot = LiveTradingBot("RELIANCE.NS", stop_loss_percent=0.1, take_profit_percent=0.2, max_hold_minutes=5, interval='1m')
    
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
        print("Bot stopped by user")