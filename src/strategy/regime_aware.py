from datetime import datetime
import pandas as pd
import numpy as np
from src.strategy.base import Strategy
from src.utils.types import *

class RegimeAwareMomentumStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        
        self.momentum_lookback = config.get('momentum_lookback', 24)
        self.vol_window = config.get('vol_window', 168)
        self.target_vol = config.get('target_vol', 0.40)
        self.max_scale = config.get('max_scale', 2.0)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_threshold = config.get('rsi_threshold', 50.0)
        self.atr_period = config.get('atr_period', 14)
        self.stop_atr_mult = config.get('stop_atr_mult', 2.5)
        self.max_holding_bars = config.get('max_holding_bars', 72)
        self.base_notional = config.get('base_notional', 10000.0)
        self.max_leverage = config.get('max_leverage', 1.0)

        self.min_position_size = config.get('min_position_size', 0.001)
        self.max_position_size = config.get('max_position_size', 10.0)
        self.min_position_value = config.get('min_position_value', 1.0)
        self.max_position_value = config.get('max_position_value', 100.0)

        self.df_prices = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']).astype({
            'timestamp': 'object',
            'open': 'float64',
            'high': 'float64',
            'low': 'float64',
            'close': 'float64',
            'volume': 'float64'
        })
        
        self.positions = {}
        self.last_bar = None
        self.new_bar_received = False
        self.latest_vol = 0.0
        self.latest_atr = 0.0

    def on_bar(self, bar):
        if bar.timeframe != "1h":
            return

        bar_data = {
            'timestamp': bar.timestamp,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        }
        
        symbol = bar.symbol
        
        if not self.df_prices.empty and bar.timestamp in self.df_prices['timestamp'].values:
            idx = self.df_prices[self.df_prices['timestamp'] == bar.timestamp].index[0]
            self.df_prices.loc[idx] = bar_data
        else:
            self.df_prices = pd.concat([self.df_prices, pd.DataFrame([bar_data])], ignore_index=True)
            
            if symbol in self.positions and self.positions[symbol]["side"] != 0:
                self.positions[symbol]["bars_held"] += 1
                
            self.new_bar_received = True
            
        self.last_bar = bar
        
        max_rows = max(self.vol_window * 2, 500)
        if len(self.df_prices) > max_rows:
            self.df_prices = self.df_prices.iloc[-max_rows:].reset_index(drop=True)

    def generate_signals(self):
        signals = []
        
        if not self.new_bar_received or len(self.df_prices) < self.vol_window + 1:
            return signals
            
        self.new_bar_received = False
        
        if self.last_bar is None:
            return signals
            
        symbol = self.last_bar.symbol
        close = self.df_prices['close']
        
        momentum = np.log(close.iloc[-1] / close.iloc[-(self.momentum_lookback + 1)])
        
        log_returns = np.log(close / close.shift(1))
        recent_log_returns = log_returns.iloc[-self.vol_window:]
        self.latest_vol = float(recent_log_returns.std(ddof=1) * np.sqrt(8760))
        
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/self.rsi_period, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1])
        
        high = self.df_prices['high']
        low = self.df_prices['low']
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        self.latest_atr = float(tr.rolling(window=self.atr_period).mean().iloc[-1])
        
        if symbol not in self.positions:
            self.positions[symbol] = {
                "side": 0,
                "size": 0.0,
                "entry_price": 0.0,
                "bars_held": 0,
                "stop_price": 0.0,
                "atr_at_entry": 0.0
            }
            
        pos = self.positions[symbol]
        current_close = float(close.iloc[-1])
        
        if pos["side"] != 0:
            exit_triggered = False
            
            if pos["side"] == 1 and current_close <= pos["stop_price"]:
                exit_triggered = True
            elif pos["side"] == -1 and current_close >= pos["stop_price"]:
                exit_triggered = True
                
            if pos["bars_held"] >= self.max_holding_bars:
                exit_triggered = True
                
            if pos["side"] == 1 and momentum < 0:
                exit_triggered = True
            elif pos["side"] == -1 and momentum > 0:
                exit_triggered = True
                
            if exit_triggered:
                exit_side = -pos["side"]
                signals.append(Signal(
                    symbol=symbol,
                    side=exit_side,
                    size=pos["size"],
                    price=current_close,
                    timestamp=self.last_bar.timestamp
                ))
        else:
            if momentum > 0 and current_rsi > self.rsi_threshold:
                if self.latest_vol > 0:
                    signals.append(Signal(
                        symbol=symbol,
                        side=1,
                        size=0.0,
                        price=current_close,
                        timestamp=self.last_bar.timestamp
                    ))
            elif momentum < 0 and current_rsi < self.rsi_threshold:
                if self.latest_vol > 0:
                    signals.append(Signal(
                        symbol=symbol,
                        side=-1,
                        size=0.0,
                        price=current_close,
                        timestamp=self.last_bar.timestamp
                    ))
                    
        return signals

    def position_size(self, signal, account):
        symbol = signal.symbol
        pos = self.positions.get(symbol, {"side": 0, "size": 0.0})
        
        if pos["side"] != 0 and signal.side == -pos["side"]:
            return pos["size"]
            
        if self.latest_vol <= 0 or np.isnan(self.latest_vol):
            return 0.0
            
        scale = min(self.target_vol / self.latest_vol, self.max_scale)
        position_value = self.base_notional * scale
        
        entry_price = self.last_bar.close if self.last_bar else signal.price
        if entry_price is None or entry_price <= 0:
            return 0.0
            
        max_allowed_value = account.balance * self.max_leverage
        position_value = min(position_value, max_allowed_value)
        
        position_value = np.clip(position_value, self.min_position_value, self.max_position_value)
        
        qty = position_value / entry_price
        qty = float(np.clip(qty, self.min_position_size, self.max_position_size))
        
        return qty

    def on_order_filled(self, order):
        symbol = order.symbol
        side = 1 if order.side == "BUY" else -1 if order.side == "SELL" else 0
        
        if symbol not in self.positions:
            self.positions[symbol] = {
                "side": 0,
                "size": 0.0,
                "entry_price": 0.0,
                "bars_held": 0,
                "stop_price": 0.0,
                "atr_at_entry": 0.0
            }
            
        pos = self.positions[symbol]
        
        if pos["side"] == 0:
            pos["side"] = side
            pos["size"] = order.filled_size
            pos["entry_price"] = order.price
            pos["bars_held"] = 0
            pos["atr_at_entry"] = self.latest_atr
            
            if side == 1:
                pos["stop_price"] = order.price - self.stop_atr_mult * self.latest_atr
            else:
                pos["stop_price"] = order.price + self.stop_atr_mult * self.latest_atr
        else:
            if side == -pos["side"]:
                pos["side"] = 0
                pos["size"] = 0.0
                pos["entry_price"] = 0.0
                pos["bars_held"] = 0
                pos["stop_price"] = 0.0
                pos["atr_at_entry"] = 0.0

    def initialize_with_history(self, bars_1h, bars_15m):
        for bar in bars_1h:
            self.on_bar(bar)
