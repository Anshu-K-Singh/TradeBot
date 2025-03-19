import backtrader as bt
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from pytz import timezone

# Define the strategy
class FixedExitStrategy(bt.Strategy):
    params = (
        ('stop_loss_percent', 0.001),  # 0.1%
        ('take_profit_percent', 0.002),  # 0.2%
        ('max_hold_minutes', 5),  # Max hold time in minutes
    )

    def __init__(self):
        self.order = None
        self.entry_price = None
        self.entry_time = None
        self.trades = []

    def log(self, txt):
        dt_utc = self.datas[0].datetime.datetime(0)
    
    # Convert to IST
        ist = timezone('Asia/Kolkata')
        dt_ist = dt_utc.replace(tzinfo=timezone('UTC')).astimezone(ist)
    
        print(f'{dt_ist}: {txt}')
    def next(self):
        if not self.position:
            self.order = self.buy()
            self.entry_price = self.datas[0].close[0]
            self.entry_time = self.datas[0].datetime.datetime(0)
            self.log(f'BUY at {self.entry_price}')
        else:
            current_price = self.datas[0].close[0]
            hold_time = (self.datas[0].datetime.datetime(0) - self.entry_time).total_seconds() / 60
            exit_reason = None

            if current_price <= self.entry_price * (1 - self.params.stop_loss_percent):
                self.order = self.sell()
                exit_reason = "Stop Loss"
            elif current_price >= self.entry_price * (1 + self.params.take_profit_percent):
                self.order = self.sell()
                exit_reason = "Take Profit"
            elif hold_time >= self.params.max_hold_minutes:
                self.order = self.sell()
                exit_reason = "Time Exit"

            if exit_reason:
                self.log(f'SELL at {current_price} ({exit_reason})')
                self.trades.append({
                    'buy_time': self.entry_time,
                    'buy_price': self.entry_price,
                    'sell_time': self.datas[0].datetime.datetime(0),
                    'sell_price': current_price,
                    'reason': exit_reason
                })

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED at {order.executed.price}')
            elif order.issell():
                self.log(f'SELL EXECUTED at {order.executed.price}, Profit: {order.executed.pnl}')
            self.order = None

# Fetch data using yfinance
def get_data(symbol, start_date, end_date, interval='1m'):
    stock = yf.Ticker(symbol)
    df = stock.history(start=start_date, end=end_date, interval=interval)
    if df.empty:
        print(f"No data fetched for {symbol} from {start_date} to {end_date}")
    else:
        # Ensure IST timezone
        ist = timezone('Asia/Kolkata')
        df.index = df.index.tz_convert(ist) if df.index.tz else df.index.tz_localize('UTC').tz_convert(ist)
        print(f"Fetched {len(df)} rows for {symbol}, Timezone: {df.index.tz}")
    return bt.feeds.PandasData(dataname=df), df

# Custom plotting function
def plot_trades(data, trades, symbol, interval):
    if not trades:
        print("No trades to plot.")
        return

    trade = trades[0]
    tz = timezone('Asia/Kolkata')  # Force IST
    buy_time = trade['buy_time'] if trade['buy_time'].tzinfo else tz.localize(trade['buy_time'])
    sell_time = trade['sell_time'] if trade['sell_time'].tzinfo else tz.localize(trade['sell_time'])

    # Find closest index
    try:
        start_idx = data.index.get_loc(buy_time)
    except KeyError:
        start_idx = data.index.get_indexer([buy_time], method='nearest')[0]
    try:
        end_idx = data.index.get_loc(sell_time)
    except KeyError:
        end_idx = data.index.get_indexer([sell_time], method='nearest')[0]

    start_idx = max(0, start_idx - 25)
    end_idx = min(len(data), end_idx + 25)
    plot_data = data.iloc[start_idx:end_idx]

    # Buy and sell signals as Series
    buy_plot = pd.Series(index=plot_data.index, dtype=float)
    sell_plot = pd.Series(index=plot_data.index, dtype=float)
    buy_plot[buy_time] = trade['buy_price']
    sell_plot[sell_time] = trade['sell_price']

    # Stop-loss and take-profit lines
    sl_price = trade['buy_price'] * (1 - 0.001)
    tp_price = trade['buy_price'] * (1 + 0.002)
    sl_line = pd.Series(sl_price, index=plot_data.index)
    tp_line = pd.Series(tp_price, index=plot_data.index)

    # Additional plots
    ap = [
        mpf.make_addplot(buy_plot, type='scatter', markersize=150, marker='^', color='green', label='Buy'),
        mpf.make_addplot(sell_plot, type='scatter', markersize=150, marker='v', color='red', label='Sell'),
        mpf.make_addplot(sl_line, type='line', color='red', linestyle='--', label='Stop Loss (0.1%)'),
        mpf.make_addplot(tp_line, type='line', color='green', linestyle='--', label='Take Profit (0.2%)')
    ]

    # Plot
    profit = trade['sell_price'] - trade['buy_price']
    fig, ax = mpf.plot(
        plot_data,
        type='candle',
        style='yahoo',
        title=f'{symbol} - {interval} Backtest (IST)\nSL: 0.1%, TP: 0.2%, Max Hold: 5min\nProfit: {profit:.2f} ({trade["reason"]})',
        ylabel='Price',
        addplot=ap,
        volume=True,
        returnfig=True
    )
    plt.legend()
    plt.savefig(f'{symbol}_{interval}_enhanced_chart.png')
    plt.show()

# Run the backtest
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(FixedExitStrategy, 
                        stop_loss_percent=0.001, 
                        take_profit_percent=0.002, 
                        max_hold_minutes=5)
    
    symbol = "RELIANCE.NS"
    start_date = datetime(2025, 3, 19)  # Using March 11, 2024 (past data)
    end_date = start_date + timedelta(days=1)
    data_feed, raw_data = get_data(symbol, start_date, end_date, interval='1m')
    
    if raw_data.empty:
        print("Exiting due to no data.")
        exit()
    
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(100000.0)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    print(f'Ending Portfolio Value: {cerebro.broker.getvalue():.2f}')
    
    strat = results[0]
    trade_analyzer = strat.analyzers.trade_analyzer.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    
    print('\nTrade Analysis:')
    if trade_analyzer.total.closed > 0:
        print(f'Total Trades: {trade_analyzer.total.closed}')
        print(f'Won: {trade_analyzer.won.total} | Lost: {trade_analyzer.lost.total}')
        print(f'Win Rate: {trade_analyzer.won.total / trade_analyzer.total.closed * 100:.2f}%')
        print(f'Total PnL: {trade_analyzer.pnl.net.total:.2f}')
    else:
        print("No trades executed.")
    
    print('\nReturns:')
    if returns.get('rtot', 0) != 0:
        print(f'Total Return: {returns["rtot"]*100:.2f}%')
    else:
        print("No returns calculated.")
    
    plot_trades(raw_data, strat.trades, symbol, '1m')