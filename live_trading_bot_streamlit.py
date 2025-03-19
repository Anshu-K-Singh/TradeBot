import streamlit as st
import backtrader as bt
from datetime import datetime
import yfinance as yf
import pandas as pd
from pytz import timezone
import plotly.graph_objects as go

# -----------------------
# 📊 Strategy Class
# -----------------------
class FixedExitStrategy(bt.Strategy):
    params = (
        ('stop_loss_percent', 0.001),  # 0.1%
        ('take_profit_percent', 0.002),  # 0.2%
        ('max_hold_minutes', 60),  # Max hold time in minutes
    )

    def __init__(self):
        self.order = None
        self.entry_price = None
        self.entry_time = None
        self.trades = []
        self.buy_signals = []
        self.sell_signals = []

    def log(self, txt):
        """Log messages in IST timezone."""
        dt_utc = self.datas[0].datetime.datetime(0).replace(tzinfo=timezone('UTC'))
        dt_ist = dt_utc.astimezone(timezone('Asia/Kolkata'))
        st.session_state.logs.append(f'{dt_ist}: {txt}')
    
    def next(self):
        """Logic for Buy/Sell Execution"""
        ist = timezone('Asia/Kolkata')

        if not self.position:
            # Place Buy Order
            self.order = self.buy()
            self.entry_price = self.datas[0].close[0]

            # Convert to IST
            dt_utc = self.datas[0].datetime.datetime(0).replace(tzinfo=timezone('UTC'))
            self.entry_time = dt_utc.astimezone(ist)

            self.buy_signals.append((self.entry_time, self.entry_price))
            self.log(f'BUY at {self.entry_price}')

        else:
            current_price = self.datas[0].close[0]

            # Ensure both datetimes are timezone-aware
            dt_utc = self.datas[0].datetime.datetime(0).replace(tzinfo=timezone('UTC'))
            current_time_ist = dt_utc.astimezone(ist)

            # Calculate hold time
            hold_time = (current_time_ist - self.entry_time).total_seconds() / 60
            exit_reason = None

            # Stop Loss Exit
            if current_price <= self.entry_price * (1 - self.params.stop_loss_percent):
                self.order = self.sell()
                exit_reason = "Stop Loss"

            # Take Profit Exit
            elif current_price >= self.entry_price * (1 + self.params.take_profit_percent):
                self.order = self.sell()
                exit_reason = "Take Profit"

            # Max Hold Time Exit
            elif hold_time >= self.params.max_hold_minutes:
                self.order = self.sell()
                exit_reason = "Time Exit"

            # Record the trade
            if exit_reason:
                self.sell_signals.append((current_time_ist, current_price))
                self.log(f'SELL at {current_price} ({exit_reason})')

                self.trades.append({
                    'buy_time': self.entry_time,
                    'buy_price': self.entry_price,
                    'sell_time': current_time_ist,
                    'sell_price': current_price,
                    'reason': exit_reason
                })

    def notify_order(self, order):
        """Notify on Order Execution"""
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
    """Fetch stock data using yfinance with IST timezone."""
    stock = yf.Ticker(symbol)
    df = stock.history(start=start_date, end=end_date, interval=interval)
    
    if df.empty:
        st.warning(f"No data fetched for {symbol} from {start_date} to {end_date}")
        return None, None

    # Convert to IST timezone
    ist = timezone('Asia/Kolkata')
    df.index = df.index.tz_convert(ist) if df.index.tz else df.index.tz_localize('UTC').tz_convert(ist)
    
    return bt.feeds.PandasData(dataname=df), df

# -----------------------
# 📊 Plot Candlestick Chart
# -----------------------
def plot_candlestick_chart(df, buy_signals, sell_signals):
    """Display Candlestick Chart with Buy and Sell signals."""
    fig = go.Figure()

    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Candlesticks"
    ))

    # Plot Buy signals
    if buy_signals:
        buy_times, buy_prices = zip(*buy_signals)
        fig.add_trace(go.Scatter(
            x=buy_times,
            y=buy_prices,
            mode='markers',
            marker=dict(color='green', size=10, symbol='triangle-up'),
            name='Buy Signals'
        ))

    # Plot Sell signals
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
        title="Candlestick Chart with Buy/Sell Signals",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark"
    )

    st.plotly_chart(fig)

# -----------------------
# 📊 Streamlit UI
# -----------------------
st.title("📊 Backtrader Backtesting Bot with Candlestick Chart (IST)")

# Sidebar for parameters
symbol = st.sidebar.text_input("Stock Symbol", "RELIANCE.NS")
stop_loss = st.sidebar.number_input("Stop Loss (%)", min_value=0.1, value=0.1)
take_profit = st.sidebar.number_input("Take Profit (%)", min_value=0.1, value=0.2)
interval = st.sidebar.selectbox("Interval", ['1m', '15m'])
start_date = st.sidebar.date_input("Start Date", datetime(2025, 3, 19))
end_date = st.sidebar.date_input("End Date", datetime(2025, 3, 20))

# Logs
if "logs" not in st.session_state:
    st.session_state.logs = []

# -----------------------
# 🚀 Run Backtest
# -----------------------
if st.button("▶️ Run Backtest"):
    cerebro = bt.Cerebro()
    strat = FixedExitStrategy

    cerebro.addstrategy(strat, 
                        stop_loss_percent=stop_loss / 100, 
                        take_profit_percent=take_profit / 100, 
                        max_hold_minutes=5)

    # Fetch data
    data_feed, raw_data = get_data(symbol, start_date, end_date, interval)

    if raw_data is not None:
        cerebro.adddata(data_feed)
        cerebro.broker.setcash(100000.0)
        results = cerebro.run()

        # Display Summary
        strat = results[0]
        total_trades = len(strat.trades)
        total_profit = sum(trade['sell_price'] - trade['buy_price'] for trade in strat.trades)

        st.subheader("📊 Backtest Results")
        st.write(f"**Total Trades:** {total_trades}")
        st.write(f"**Total Profit:** ₹{total_profit:.2f}")

        # Display Trades Summary
        if strat.trades:
            trades_df = pd.DataFrame(strat.trades)
            trades_df['Profit'] = trades_df['sell_price'] - trades_df['buy_price']
            st.dataframe(trades_df)

        # Plot Candlestick Chart
        plot_candlestick_chart(raw_data, strat.buy_signals, strat.sell_signals)

# Display logs
st.subheader("📝 Logs")
st.text_area("Logs", value="\n".join(st.session_state.logs), height=300)
