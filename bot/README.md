

## Overview


The bot operates on a simple strategy:
- **Buy**: When no position is held, it buys at the current price.
- **Sell**: Exits the position based on stop-loss, take-profit, or a time limit.

## How It Works

### Key Features
- **Real-Time Data**: Fetches the latest 1-day price history at a specified interval (`1m` or `15m`).
- **Trading Logic**:
  - **Stop Loss**: Sells if the price drops 0.1% below the entry price (configurable).
  - **Take Profit**: Sells if the price rises 0.2% above the entry price (configurable).
  - **Time Exit**: Sells after a set time (default: 5 minutes, adjustable).
- **Visualization**: Plots a candlestick chart with buy/sell signals.
- **Logging**: Outputs trade details and status updates to the terminal and saves trades to a CSV file.

### Running the Bot
1. **Setup**: Install required libraries:
   ```bash
   pip install yfinance pandas matplotlib mplfinance
   ```
2. **Execution**: Run the script:
   ```bash
   cd bot
   python trade.py
   ```
3. **Stopping**: Press `Ctrl+C` to stop the bot and close any open position.

### Parameters
- `symbol`: Stock ticker (e.g., "RELIANCE.NS"). you can change in code 
- `stop_loss_percent`: Percentage drop to trigger a sell (default: 0.1%).
- `take_profit_percent`: Percentage gain to trigger a sell (default: 0.2%).
- `max_hold_minutes`: Maximum hold time before selling (default: 5 minutes).
- `interval`: Data fetch frequency (`1m` for 1-minute, `15m` for 15-minute).

i put these conditions so that more trades happens while testing 

## Output Logs
The bot logs its activity to the terminal in real-time. Here’s what you’ll see:

### Initial Start
```
Starting live trading bot for RELIANCE.NS with 1m interval
```
- Indicates the bot has begun monitoring the specified stock and interval.

### Data Fetch
```
Fetched 390 rows of 1m data
```
- Shows successful retrieval of price data (number of rows varies based on market hours).

### Status Updates
```
Time: 2025-03-19 14:30:45.123456, Price: 2850.25, Position: None, Trades: 0
```
- Updates every interval (60s for 1m, 900s for 15m).
- **Time**: Current system time.
- **Price**: Latest closing price.
- **Position**: `None` (no position) or `LONG` (holding a position).
- **Trades**: Number of completed sell trades.

### Buy Signal
```
BUY executed at 2850.25 on 2025-03-19 14:30:00+05:30
```
- Triggered when no position is held.
- Logs the entry price and timestamp from the data.

### Sell Signal
```
SELL executed at 2847.40 on 2025-03-19 14:32:00+05:30, Profit: -2.85, Reason: Stop Loss
```
- Triggered by one of three conditions:
  - **Stop Loss**: Price drops below entry price by 0.1% (e.g., 2850.25 * 0.999 = 2847.40).
  - **Take Profit**: Price rises above entry price by 0.2% (e.g., 2850.25 * 1.002 = 2855.95).
  - **Time Exit**: Held for 5 minutes (or configured `max_hold_minutes`).
- Logs exit price, profit/loss, and reason.

### Manual Stop (Ctrl+C)
```
SELL executed at 2852.10 on 2025-03-19 14:35:00.123456, Profit: 1.85, Reason: Manual Stop
Bot stopped by user
```
- Closes any open position when interrupted, logging the final trade.



## Stop Loss Mechanism
The stop-loss feature ensures the bot exits a position if the price falls too far, limiting losses. Here’s how it works:
- **Default**: Set to 0.1% (e.g., if you buy at 100, it sells at 99.90 or below).
- **Calculation**: `entry_price * (1 - stop_loss_percent)`.
- **Example**:
  - Buy at 2850.25.
  - Stop-loss level: 2850.25 * 0.999 = 2847.40.
  - If the price hits 2847.40 or lower, it sells, logging "Stop Loss" as the reason.
- **Configurable**: Adjust `stop_loss_percent` in the bot initialization (e.g., 0.5 for 0.5%).

## Candlestick Chart
- **Output**: Saved as `<symbol>_<interval>_live_chart.png` (e.g., `RELIANCE.NS_1m_live_chart.png`).
- **Details**:
  - Shows the last 50 candles.
  - Green `^` markers for buy signals (up to 10 recent).
  - Red `v` markers for sell signals (up to 10 recent).
  - Title includes symbol, interval, SL, and TP percentages.
  - Volume bars below the chart.

## Trade Log (CSV)
- **File**: `<symbol>_<datetime>_<interval>_trades.csv` (e.g., `RELIANCE.NS_2025-03-19_14-30-45_1m_trades.csv`).
- **Columns**:
  - `type`: "BUY" or "SELL".
  - `price`: Trade price.
  - `timestamp`: Trade time.
  - `profit`: Profit/loss (for SELL trades only).
  - `reason`: Exit reason (for SELL trades: "Stop Loss", "Take Profit", "Time Exit", "Manual Stop").

## Example Workflow
1. Bot starts: "Starting live trading bot..."
2. Fetches data: "Fetched 390 rows..."
3. No position: Buys at 2850.25.
4. Price drops to 2847.40: Sells with "Stop Loss", profit -2.85.
5. Updates: "Price: 2847.40, Position: None, Trades: 1".
6. Chart saved with buy/sell markers.
7. CSV logs the trade.

## Notes
- **Simulation**: Trades are simulated, not real.
- **Interval**: 1-minute (`1m`) updates every 60s; 15-minute (`15m`) every 900s.
- **Error Recovery**: Retries after 60s on failure.

This bot provides a clear view of trading activity through logs, charts, and CSV files, with a reliable stop-loss to manage risk.
