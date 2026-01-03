# Cryptocurrency Trading System

A cryptocurrency trading system supporting both backtesting and live trading on Binance with multi-timeframe strategy.

## Features

- **Backtesting Engine** - Test strategies on historical data
- **Live Trading** - Execute strategies in real-time on Binance Testnet
- **Multi-Timeframe Analysis** - Combine multiple timeframes for better signals
- **Complete Order Logging** - Track every trade (BUY/SELL)
- **Performance Analytics** - Calculate PnL, win rate and other metrics
- **Testnet Support** - Safe testing environment

## Project Structure

```
Numatix/
├── config/                     
│   └── config.py               # API keys
├── src/
│   ├── backtesting/            
│   │   ├── backtest.py         # Core backtesting logic
│   ├── strategy/               
│   │   ├── base.py             # Abstract base strategy
│   │   ├── demo.py             # Testing demo strategy
│   │   └── multi_tf.py         # Multi-timeframe strategy
│   ├── trading/                
│   │   ├── exchange.py         # Binance API client
│   │   └── executor.py         # Trading executor
│   └── utils/                  
│       ├── data.py             # CSV data operations
│       ├── logger.py           # Logging utilities
│       ├── trade_tracker.py    # Order tracking
│       └── types.py            # Data structures
├── scripts/                    
│   ├── analyze_trades.py       # Trade analysis script
│   ├── prefill_data.py         # Download historical data script
│   └── test_order.py
├── data/                       
│   ├── backtest_trades.csv     # Backtest orders
│   └── live_trades.csv         # Live trading orders
└── logs/                       # Log files

```

## Setup

### 1. Install Dependencies

```
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit `config/config.py` with your own API Keys

## Usage

### 1. Download Historical Data

First, fetch historical 1-minute data from Binance for backtesting:

```bash
python scripts/download_data.py
```

**What it does:**
- Fetches 1-minute OHLCV data from Binance API
- Saves to `data/eth_1m.csv`
- Edit start_date and end_data in `scripts/download_data.py` for custom timerange

### 2. Backtesting

Run a backtest on past data:

```bash
python src/trading/executor.py --mode backtest --start "2025-12-29T16:00:00" --end "2025-12-29T21:30:00" --data-1m data/eth_1m.csv --logfile logs/backtest.log
```

**Options:**
- `--mode backtest` - Run in backtest mode
- `--start` - Start datetime (ISO format)
- `--end` - End datetime (ISO format)
- `--data-1m` - Path to 1-minute OHLCV CSV file
- `--logfile` - Log file path

**How it works:**
- Processes 1-minute bars sequentially (like live trading)
- Aggregates into 15m and 1h candles in real-time
- Strategy receives updated candles every minute

**Output:** Results saved to `data/backtest_trades.csv`

### 3. Live Trading

Run strategy in live trading mode:

```bash
python src/trading/executor.py --mode live --symbol ETHUSDT --logfile logs/live.log
```

**Options:**
- `--mode live` - Run in live trading mode
- `--symbol` - Trading symbol (default: ETHUSDT)
- `--logfile` - Log file path

**How it works:**
- Fetches latest 1h and 15m candles every 60 seconds
- Strategy generates signals on real-time data
- Places orders on Binance Testnet 
- Tracks all orders

**Output:** Results saved to `data/live_trades.csv`

### 4. Analyze Trades

Analyze backtest and live trading performance:

```bash
python scripts/analyze_trades.py
```

**What it does:**
- Loads orders from `data/backtest_trades.csv` and `data/live_trades.csv`
- Pairs BUY/SELL orders
- Calculates PnL for each completed trade
- Displays metrics: total trades, total PnL, average PnL, largest win/loss
- Compares backtest vs live performance

## Backtesting vs Live Trading

The backtesting pipeline is designed to match live trading behavior:

| Aspect | Live Trading | Backtesting |
|--------|--------------|-------------|
| **Data Update** | Every 60 seconds | Every 1-minute bar |
| **Order Tracking** | All BUY/SELL orders tracked | All BUY/SELL orders tracked |
| **Multiple Positions** | Allowed | Allowed |

This ensures backtesting results closely match what would happen in live trading.

## Data Format

### Order Logs (CSV)

Both `backtest_trades.csv` and `live_trades.csv` use the same format:

```csv
timestamp,side,symbol,price,size,order_id,status
2025-12-19T13:45:00,BUY,ETHUSDT,2828.59,0.033985,bt-2,FILLED
2025-12-19T13:45:00,SELL,ETHUSDT,2942.41,0.033985,bt-3,FILLED
```

**Fields:**
- `timestamp` - Order execution time
- `side` - BUY or SELL
- `symbol` - Trading pair
- `price` - Execution price
- `size` - Order quantity
- `order_id` - Unique order identifier
- `status` - Order status (FILLED, PARTIAL, etc.)

### Multi-Timeframe Strategy

See [`src/strategy/multi_tf.py`](src/strategy/multi_tf.py) for a complete example:
- Uses 1-hour bars for trend direction
- Uses 15-minute bars for entry timing
- MACD crossover signals on both timeframes for buy/sell orders
- Postion sizing capability using True Range and Risk Management

## Performance Metrics

The analysis tool calculates:

- **Total Trades** - Number of completed trade pairs (entry + exit)
- **Total PnL** - Sum of all profits and losses (USDT)
- **Average PnL** - Mean PnL per trade
- **Largest Win** - Best performing trade
- **Largest Loss** - Worst performing trade

## Architecture

```
User Request
     ↓
Executor (executor.py -> Backtest or Live Trade)
     ↓
Strategy (multi_tf.py)
     ↓
Signal Generation
     ↓
Order Placement
     ↓
TradeTracker (logs every order)
     ↓
CSV Files (data/)
     ↓
Analysis (analyze_trades.py)
```