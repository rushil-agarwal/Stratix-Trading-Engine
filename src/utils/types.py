from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str

@dataclass
class Signal:
    symbol: str
    side: int 
    size: float
    price: Optional[float]
    timestamp: datetime

@dataclass
class Order:
    id: Optional[str]
    symbol: str
    side: str
    size: float
    price: Optional[float]
    status: str
    filled_size: float
    timestamp: datetime

@dataclass
class AccountInfo:
    balance: float
    positions: dict
