# random strategy to test backtest and live trading pipelines, later replaved 
# by multi-timeframe strategy


from datetime import datetime
import random
from src.strategy.base import Strategy
from src.utils.types import *

class RandomDemoStrategy(Strategy):
    def __init__(self, config = None, seed = 42, buy_prob= 0.2, sell_prob = 0.2):
        super().__init__(config)
        
        self.rng = random.Random(seed)
        self.last_bar: Bar
        self.buy_prob = buy_prob
        
        self.sell_prob = sell_prob

    def on_bar(self, bar):
        self.last_bar = bar

    def generate_signals(self):
        signals = []
        
        if self.last_bar is None:
            return signals
        
        p = self.rng.random()
        
        if p < self.buy_prob:
            signals.append(Signal(symbol=self.last_bar.symbol, side=1, size=0.01, price=None, timestamp=self.last_bar.timestamp))
        elif p > (1.0 - self.sell_prob):
            signals.append(Signal(symbol=self.last_bar.symbol, side=-1, size=0.01, price=None, timestamp=self.last_bar.timestamp))
        return signals

    def position_size(self, signal, account):
        return signal.size

    def position_size(self, signal, account):
        pass

    def on_order_filled(self, order):
        pass