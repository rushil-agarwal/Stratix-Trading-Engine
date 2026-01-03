from abc import ABC, abstractmethod
from src.utils.types import *

class Strategy(ABC):
    def __init__(self, config):
        
        self.config = config

    @abstractmethod
    def on_bar(self, bar):
        # function to update the strategy with latest data/bar
        raise NotImplementedError

    @abstractmethod
    def generate_signals(self):
        # function to generate new signals of buy/sell/hold when getting new data
        raise NotImplementedError

    @abstractmethod
    def position_size(self, signal, account):
        # calculate how much to buy/sell based on signal strength/confidence
        raise NotImplementedError
    
    def on_order_filled(self, order):
        # function to handle order filled events, can be overridden by subclasses
        pass
