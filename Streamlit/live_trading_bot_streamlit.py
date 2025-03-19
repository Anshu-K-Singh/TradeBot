import streamlit as st
import backtrader as bt
from datetime import datetime
import yfinance as yf
import pandas as pd
from pytz import timezone
import plotly.graph_objects as go

# -----------------------
# 📊 Enhanced Strategy Class
# -----------------------
class EnhancedStrategy(bt.Strategy):
    params = (
        ('short_ema', 10),
        ('long_ema', 50),
        ('rsi_period', 14),
        ('atr_period', 14),
        ('atr_multiplier', 2.0),
        ('max_hold_minutes', 60),  
        ('trailing_percent', 0.01),  # 1% trailing stop-loss
    )

    def __init__(self):
        self.order = None
        self.trades = []
        self.buy_signals = []
        self.sell_signals = []

        # Indicators
        self.ema_short = bt.indicators.ExponentialMovingAverage(self.data.close, period=self.params.short_ema)
        self.ema_long = bt.indicators.ExponentialMovingAverage(self.data.close, period=self.params.long_ema)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)

        # Trailing Stop-Loss
        self.trailing_stop = None

    def log(self, txt):
        """Log messages in IST timezone."""
        dt_utc = self.datas[0].datetime.datetime(0).replace(tzinfo=timezone('UTC'))
        dt_ist = dt_utc.astimezone(timezone('Asia/Kolkata'))
        st.session_state.logs.append(f'{dt_ist}: {txt}')

    def next(self):
        ist = timezone('Asia/Kolkata')

        if not self.position:
            # Buy condition: EMA crossover + RSI confirmation
            if self.ema_short > self.ema_long and self.rsi < 30:
                self.order = self.buy()

                # Store Entry Price and Time
                self.entry_price = self.data.close[0]
                dt_utc = self.datas[0].datetime.datetime(0).replace(tzinfo=timezone('UTC'))
                self.entry_time = dt_utc.astimezone(ist)

                # Set dynamic SL/TP based on ATR
                self.stop_loss = self.entry_price - self.atr[0] * self.params.atr_multiplier
                self.take_profit = self.entry_price + self.atr[0] * self.params.atr_multiplier
                self.trailing_stop = self.entry_price * (1 - self.params.trailing_percent)

                self.buy_signals.append((self.entry_time, self.entry_price))
                self.log(f'BUY at {self.entry_price} (SL: {self.stop_loss}, TP: {self.take_profit})')

        else:
            current_price = self.data.close[0]
            dt_utc = self.datas[0].datetime.datetime(0).replace(tzinfo=timezone('UTC'))
            current_time_ist = dt_utc.astimezone(ist)

            # Trailing Stop-Loss Adjustment
            if current_price > self.entry_price and current_price > self.trailing_stop:
                self.trailing_stop = max(self.trailing_stop, current_price * (1 - self.params.trailing_percent))

            # Exit conditions
            exit_reason = None

            # Stop-Loss
            if current_price <= self.stop_loss:
                exit_reason = "Stop Loss"

            # Take-Profit
            elif current_price >= self.take_profit:
                exit_reason = "Take Profit"

            # Trailing Stop-Loss Hit
            elif current_price <= self.trailing_stop:
                exit_reason = "Trailing Stop"

            # Max Hold Time Exit
            hold_time = (current_time_ist - self.entry_time).total_seconds() / 60
            if hold_time >= self.params.max_hold_minutes:
                exit_reason = "Time Exit"

            if exit_reason:
                self.sell_signals.append((current_time_ist, current_price))
                self.order = self.sell()

                self.trades.append({
                    'buy_time': self.entry_time,
                    'buy_price': self.entry_price,
                    'sell_time': current_time_ist,
                    'sell_price': current_price,
                    'reason': exit_reason
                })

                self.log(f'SELL at {current_price} ({exit_reason})')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED at {order.executed.price}')
            elif order.issell():
                self.log(f'SELL EXECUTED at {order.executed.price}, Profit: {order.executed.pnl}')
            self.order = None


# -----------------------
# 📈 Fetch Data from Yahoo Finance
# -----------------------
def get_data(symbol, start_date, end_date, interval='1m'):
    stock = yf.Ticker(symbol)
    df = stock.history(start=start_date, end=end_date, interval=interval)

    if df.empty:
        st.warning(f"No data fetched for {symbol} from {start_date} to {end_date}")
        return None, None

    ist = timezone('Asia/Kolkata')
    df.index = df.index.tz_convert(ist) if df.index.tz else df.index.tz_localize('UTC').tz_convert(ist)
    
    return bt.feeds.PandasData(dataname=df), df


# -----------------------
# 📊 Plot Candlestick Chart
# -----------------------
def plot_candlestick_chart(df, buy_signals, sell_signals):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Candlesticks"
    ))

    if buy_signals:
        buy_times, buy_prices = zip(*buy_signals)
        fig.add_trace(go.Scatter(
            x=buy_times,
            y=buy_prices,
            mode='markers',
            marker=dict(color='green', size=10, symbol='triangle-up'),
            name='Buy Signals'
        ))

    if sell_signals:
        sell_times, sell_prices = zip(*sell_signals)
        fig.add_trace(go.Scatter(
            x=sell_times,
            y=sell_prices,
            mode='markers',
            marker=dict(color='red', size=10, symbol='triangle-down'),
            name='Sell Signals'
        ))

    fig.update_layout(
        title="Enhanced Candlestick Chart with Buy/Sell Signals",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark"
    )

    st.plotly_chart(fig)


# -----------------------
# 📊 Streamlit UI
# -----------------------
st.title("📊 Advanced Trading Bot with Candlestick Chart (IST)")

symbol = st.sidebar.text_input("Stock Symbol", "RELIANCE.NS")
start_date = st.sidebar.date_input("Start Date", datetime(2025, 3, 19))
end_date = st.sidebar.date_input("End Date", datetime(2025, 3, 20))

if "logs" not in st.session_state:
    st.session_state.logs = []

if st.button("▶️ Run Backtest"):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(EnhancedStrategy)

    data_feed, raw_data = get_data(symbol, start_date, end_date, '1m')

    if raw_data is not None:
        cerebro.adddata(data_feed)
        cerebro.broker.setcash(100000.0)
        results = cerebro.run()

        strat = results[0]
        plot_candlestick_chart(raw_data, strat.buy_signals, strat.sell_signals)
