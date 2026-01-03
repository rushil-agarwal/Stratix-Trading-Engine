

from datetime import datetime
import pandas as pd
import numpy as np
from src.strategy.base import Strategy
from src.utils.types import *


class MultiTFStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        
        self.ema_fast_period = config.get('ema_fast_period', 15)  # 15min entry singals
        self.ema_slow_period = config.get('ema_slow_period', 60)  # 1 hour confirmation signals
        self.signal_period = config.get('signal_period', 3) 
        
        self.atr_period = config.get('atr_period', 10)
        self.risk_per_trade = config.get('risk_per_trade', 0.01)  
        self.atr_multiplier = config.get('atr_multiplier', 2.0)  
        self.max_leverage = config.get('max_leverage', 1.0)  
        
        # clipping limits for risk management
        self.min_position_size = config.get('min_position_size', 0.001) 
        self.max_position_size = config.get('max_position_size', 10.0)  
        self.min_position_value = config.get('min_position_value', 1.0) 
        self.max_position_value = config.get('max_position_value', 100.0)
        
        self.df_prices = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'timeframe']).astype({
            'timestamp': 'object',
            'open': 'float64',
            'high': 'float64',
            'low': 'float64',
            'close': 'float64',
            'timeframe': 'object'
        })
        
        self.macd = None
        self.macd_signal = None
        self.prev_macd = None
        self.prev_signal = None
        self.atr = None
        self.last_bar_1h = None
        self.last_bar_15m = None

    def on_bar(self, bar):
        # store the latest receieved bar

        bar_data = {
            'timestamp': bar.timestamp,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'timeframe': bar.timeframe
        }
        
        self.df_prices = pd.concat([self.df_prices, pd.DataFrame([bar_data])], ignore_index=True)
        if bar.timeframe == "1h":
            self.last_bar_1h = bar
        elif bar.timeframe == "15m":
            self.last_bar_15m = bar
        
        max_rows = max(self.ema_slow_period * 3, 200)
        if len(self.df_prices) > max_rows:
            self.df_prices = self.df_prices.iloc[-max_rows:].reset_index(drop=True)
        
        if len(self.df_prices) >= self.ema_slow_period:
            self.prev_macd = self.macd
            self.prev_signal = self.macd_signal
            ema_fast = self.df_prices['close'].ewm(span=self.ema_fast_period, adjust=False).mean()
            ema_slow = self.df_prices['close'].ewm(span=self.ema_slow_period, adjust=False).mean()
            
            macd_line = ema_fast - ema_slow
            
            signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
            self.macd = macd_line.iloc[-1]
            self.macd_signal = signal_line.iloc[-1]
            
            if len(self.df_prices) >= self.atr_period:
                high = self.df_prices['high']
                low = self.df_prices['low']
                close = self.df_prices['close']
                prev_close = close.shift(1)
                
                tr = pd.concat([
                    (high - low),
                    (high - prev_close).abs(),
                    (low - prev_close).abs()
                ], axis=1).max(axis=1)
                
                self.atr = tr.rolling(window=self.atr_period).mean().iloc[-1]

    def generate_signals(self):
        # return buy/sell/hold signals based on strategy

        signals = []
        
        if self.macd is None or self.macd_signal is None:
            return signals
        
        if self.prev_macd is None or self.prev_signal is None:
            return signals
        
        if self.last_bar_1h is None or self.last_bar_15m is None:
            return signals
        
        current_bar = self.last_bar_15m
        
        
        cross_signal = 0
        
        # Cross up if previous (macd <= signal) and current (macd > signal)
        if self.prev_macd <= self.prev_signal and self.macd > self.macd_signal:
            cross_signal = 1
        
        # Cross dow if previous (macd >= signal) and current (macd < signal)
        elif self.prev_macd >= self.prev_signal and self.macd < self.macd_signal:
            cross_signal = -1
        
        if cross_signal == 1:
            # BUY SIGNAL
            signals.append(Signal(
                symbol=current_bar.symbol,
                side=1,
                size=0.0, 
                price=None,
                timestamp=current_bar.timestamp,
            ))
        elif cross_signal == -1:
            # SELL SIGNAL
            signals.append(Signal(
                symbol=current_bar.symbol,
                side=-1,
                size=0.0,
                price=None,
                timestamp=current_bar.timestamp,
            ))
        
        return signals

    def position_size(self, signal, account):
        # calculatee the size of order based on confidence of signal
        if self.atr is None or np.isnan(self.atr) or self.atr <= 0:
            return 0.0
        
        entry_price = self.last_bar_15m.close if self.last_bar_15m else signal.price
        if entry_price is None or entry_price <= 0:
            return 0.0
        
        stop_distance = self.atr_multiplier * self.atr
        
        risk_dollars = self.risk_per_trade * account.balance
        qty = risk_dollars / stop_distance
        max_qty = (account.balance * self.max_leverage) / entry_price
        position = float(np.minimum(qty, max_qty))
        position = float(np.clip(position, self.min_position_size, self.max_position_size))
        
        position_value = position * entry_price
        
        if position_value < self.min_position_value:
            position = self.min_position_value / entry_price
        elif position_value > self.max_position_value:
            position = self.max_position_value / entry_price
        
        position = float(np.clip(position, self.min_position_size, self.max_position_size))
        
        return position

    
    def initialize_with_history(self, bars_1h, bars_15m):
        # pre load bars into memoory, otherwise strategy has to wait till it gets
        # enough data to start producing signals

        for bar in bars_1h:
            self.on_bar(bar)
        
        for bar in bars_15m:
            self.on_bar(bar)