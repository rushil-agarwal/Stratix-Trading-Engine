# Cryptocurrency Trading System

A cryptocurrency trading system supporting both backtesting and live trading on Binance with multi-timeframe strategy.

## Features

- **Backtesting Engine** - Test strategies on historical data
- **Live Trading** - Execute strategies in real-time on Binance Testnet
- **Multiple Strategies** - Run different strategies dynamically via CLI
- **Complete Order Logging** - Track every trade (BUY/SELL)
- **Performance Analytics** - Calculate PnL, win rate, return percentages, and comparative metrics
- **Testnet Support** - Safe testing environment

## Project Structure

```
TradingEngine/
├── config/                     
│   └── config.py               # API keys
├── src/
│   ├── backtesting/            
│   │   ├── backtest.py         # Core backtesting logic
│   ├── strategy/               
│   │   ├── base.py             # Abstract base strategy
│   │   ├── demo.py             # Testing demo strategy
│   │   ├── multi_tf.py         # Multi-timeframe strategy
│   │   └── regime_aware.py     # Regime-Aware Momentum Strategy
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
│   ├── download_data.py        # Download historical data script (paginated)
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

First, fetch historical data from Binance for backtesting (supports paginated requests):

```bash
python scripts/download_data.py
```

**What it does:**
- Fetches 1-minute OHLCV data from Binance API (uses mainnet for reliable history)
- Saves to `data/eth_1m.csv`
- Default date range is pre-configured to 10 days of data for local strategy testing.

### 2. Backtesting

Run a backtest on past data:

```bash
python src/trading/executor.py --mode backtest --strategy regime_aware --start "2025-12-19T00:00:00" --end "2025-12-29T23:59:00" --data-1m data/eth_1m.csv --logfile logs/backtest.log
```

**Options:**
- `--mode backtest` - Run in backtest mode
- `--strategy` - Strategy to run (`multi_tf` or `regime_aware`, default: `multi_tf`)
- `--start` - Start datetime (ISO format)
- `--end` - End datetime (ISO format)
- `--data-1m` - Path to 1-minute OHLCV CSV file
- `--logfile` - Log file path

**How it works:**
- Processes 1-minute bars sequentially (like live trading)
- Aggregates into 15m and 1h candles in real-time
- Strategy receives updated candles every minute (updating incomplete candle rows in-place)

**Output:** Results saved to `data/backtest_trades.csv`

### 3. Live Trading

Run strategy in live trading mode:

```bash
python src/trading/executor.py --mode live --strategy regime_aware --symbol ETHUSDT --logfile logs/live.log
```

**Options:**
- `--mode live` - Run in live trading mode
- `--strategy` - Strategy to run (`multi_tf` or `regime_aware`, default: `multi_tf`)
- `--symbol` - Trading symbol (default: ETHUSDT)
- `--logfile` - Log file path

**How it works:**
- Fetches latest candles every 60 seconds (prefills memory on startup)
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
- Calculates PnL and return percentages for each completed trade
- Displays metrics: total trades, total PnL, average PnL, win rate, average return %, and best/worst trade performance
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

## Available Strategies

### 1. Multi-Timeframe Strategy (MACD / EMA)
Located in [`src/strategy/multi_tf.py`](src/strategy/multi_tf.py).
- Uses 1-hour bars for trend direction.
- Uses 15-minute bars for entry timing.
- MACD crossover signals on both timeframes for buy/sell orders.
- Position sizing capability using True Range and Risk Management.

### 2. Regime-Aware Momentum Strategy
Located in [`src/strategy/regime_aware.py`](src/strategy/regime_aware.py).
- **Momentum Signal**: Computes the 24-bar log return: `momentum = log(close[0] / close[24])` on the 1-hour timeframe. Long if positive, short if negative.
- **Realized Volatility**: Calculates the annualized 168-bar volatility (7 days window): `σ = std(log_returns[-168:]) * sqrt(8760)`.
- **Volatility Sizing**: Vol-scales the position: `scale = min(target_vol / σ, 2.0)` where `target_vol` is `40%`. Position notional is `base_notional * scale`, allocating larger sizes in low-vol regimes and smaller sizes in high-vol regimes automatically.
- **RSI Confirmation**: Filters noise with 14-period RSI. Long only if RSI > 50; Short only if RSI < 50.
- **Stop Loss & Exit**: Stops at `2.5 * ATR(14)` from entry price. Max holding duration of `72 bars` (3 days). Exits immediately if momentum sign flips.

## Performance Metrics

The analysis tool calculates:

- **Total Trades** - Number of completed trade pairs (entry + exit)
- **Total PnL** - Sum of all profits and losses (USDT)
- **Average PnL** - Mean PnL per trade
- **Largest Win & Loss PnL** - Best and worst PnL results in dollar terms
- **Win Rate** - Percentage of trades that were profitable
- **Average Return (%)** - Mean trade percentage return
- **Largest Win & Loss Return (%)** - Best and worst trade percentage returns

## Architecture

```
User Request
     ↓
Executor (executor.py -> Backtest or Live Trade)
     ↓
Strategy (e.g. multi_tf.py or regime_aware.py)
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