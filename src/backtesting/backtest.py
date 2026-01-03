from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy as BacktestStrategy

from src.utils.types import *
from src.utils.logger import *
from src.utils.data import load_ohlcv_csv, write_trades
from src.utils.types import AccountInfo
from src.utils.trade_tracker import TradeTracker
from src.trading.exchange import BinanceClient
from config.config import load_config


class StrategyAdapter(BacktestStrategy):
    
    def init(self):
        self.custom_strategy = self.custom_strategy_instance
        self.trade_tracker = self.trade_tracker_instance
        self.logger_instance = self.logger_instance_ref
        self.order_counter = 0
        
        self.account_balance = self._broker._cash
        
        self.last_1h_bar = None
        self.last_15m_bar = None
        self.all_bars_1m = self.all_bars_1m_data
    
    def next(self):
        current_time = self.data.index[-1]

        bar_1h = self._aggregate_bars(current_time, "1h")
        bar_15m = self._aggregate_bars(current_time, "15m")
        if bar_1h:
            if self.logger_instance:
                log_market_data(self.logger_instance, bar_1h)
            self.custom_strategy.on_bar(bar_1h)
            self.last_1h_bar = bar_1h
        
        if bar_15m:
            if self.logger_instance:
                log_market_data(self.logger_instance, bar_15m)
            self.custom_strategy.on_bar(bar_15m)
            self.last_15m_bar = bar_15m
        
        signals = self.custom_strategy.generate_signals()
        
        if signals and self.logger_instance:
            log_signal_generation(self.logger_instance, signals, bar_15m if bar_15m else bar_1h)
        
        for sig in signals:
            if sig.side == 0:
                continue
            
            account = AccountInfo(balance=self.account_balance, positions={})
            size = self.custom_strategy.position_size(sig, account)
            
            if size <= 0:
                continue
            
            sig.size = size
            
            order = self._submit_order_like_live(sig, bar_15m if bar_15m else bar_1h)
            
            order_record = self.trade_tracker.add_order(order)
            if self.logger_instance:
                log_trade(self.logger_instance, order_record)
            
            if order.side == "BUY":
                self.account_balance -= order.filled_size * order.price
            elif order.side == "SELL":
                self.account_balance += order.filled_size * order.price
    
    def _aggregate_bars(self, current_time, timeframe):
        if timeframe == "15m":
            interval_minutes = 15
        elif timeframe == "1h":
            interval_minutes = 60
        else:
            return None
        
        minutes_since_midnight = current_time.hour * 60 + current_time.minute
        interval_start_minutes = (minutes_since_midnight // interval_minutes) * interval_minutes
        interval_start = current_time.replace(
            hour=interval_start_minutes // 60,
            minute=interval_start_minutes % 60,
            second=0,
            microsecond=0
        )
        
        relevant_bars = [
            b for b in self.all_bars_1m 
            if interval_start <= b.timestamp <= current_time
        ]
        
        if not relevant_bars:
            return None
        aggregated_bar = Bar(
            symbol=relevant_bars[0].symbol,
            timeframe=timeframe,
            timestamp=interval_start,
            open=relevant_bars[0].open,
            high=max(b.high for b in relevant_bars),
            low=min(b.low for b in relevant_bars),
            close=relevant_bars[-1].close,
            volume=sum(b.volume for b in relevant_bars)
        )
        
        return aggregated_bar
    
    def _submit_order_like_live(self, signal, bar):
        order_side = "BUY" if signal.side == 1 else "SELL" if signal.side == -1 else "HOLD"
        fill_price = bar.close
        
        self.order_counter += 1
        order = Order(
            id=f"bt-{self.order_counter}",
            symbol=signal.symbol,
            side=order_side,
            size=signal.size,
            price=fill_price,
            status="FILLED",
            filled_size=signal.size,
            timestamp=bar.timestamp,
        )
        
        if self.logger_instance:
            log_order_placement(self.logger_instance, order)
            log_order_fill(self.logger_instance, order)
        self.custom_strategy.on_order_filled(order)
        return order


class BacktestEngine:
    def __init__(self, strategy, data_source_1m=None, logger=None):
        self.strategy = strategy
        self.data_source_1m = data_source_1m
        self.logger = logger
        self.trade_tracker = TradeTracker()
        self.bt = None
    
    def aggregate_to_timeframe(self, df_1m, timeframe):
        if timeframe == "1m":
            return df_1m
        freq_map = {"15m": "15T", "1h": "1H"}
        freq = freq_map.get(timeframe, "1T")
        
        df_agg = df_1m.resample(freq).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        return df_agg
    
    def run(self, start, end, cash=100000, commission=0.0):
        bars_1m = load_ohlcv_csv(self.data_source_1m)
        
        if self.logger:
            self.logger.info(f"Loaded {len(bars_1m)} 1-minute bars from CSV")
        
        relevant_bars = [b for b in bars_1m if start <= b.timestamp <= end]
        relevant_bars.sort(key=lambda b: b.timestamp)
        
        if not relevant_bars:
            if self.logger:
                self.logger.info("No bars found in the specified range")
            return []
        df = pd.DataFrame([
            {
                'Open': bar.open,
                'High': bar.high,
                'Low': bar.low,
                'Close': bar.close,
                'Volume': bar.volume,
            }
            for bar in relevant_bars
        ])
        df.index = pd.DatetimeIndex([bar.timestamp for bar in relevant_bars])
        df.index.name = 'Date'
        
        if self.logger:
            self.logger.info(f"Running backtest from {df.index[0]} to {df.index[-1]}")
            self.logger.info(f"Processing {len(df)} 1-minute bars")
            self.logger.info("Note: Backtest uses 1m bar data; timing and prices may differ from live trading")
        
        class CustomStrategy(StrategyAdapter):
            custom_strategy_instance = self.strategy
            trade_tracker_instance = self.trade_tracker
            logger_instance_ref = self.logger
            all_bars_1m_data = relevant_bars  # Pass all 1m bars for aggregation
        
        self.bt = Backtest(
            df,
            CustomStrategy,
            cash=cash,
            commission=0.0,  
            exclusive_orders=False
        )
        self.bt.run()
        
        return self.trade_tracker.get_all_orders()
    
    def save_trades_csv(self, path):
        all_orders = self.trade_tracker.get_all_orders()
        
        rows = []
        for order in all_orders:
            rows.append({
                "timestamp": order["timestamp"],
                "side": order["side"],
                "symbol": order["symbol"],
                "price": order["price"],
                "size": order["size"],
                "order_id": order["order_id"],
                "status": order["status"],
            })
        
        write_trades(path, rows)
        
        if self.logger:
            self.logger.debug(f"Saved {len(rows)} orders to {path}")
        
        return path


