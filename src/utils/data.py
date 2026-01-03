import pandas as pd
import numpy as np
from datetime import datetime
import json
from src.utils.types import *

CSV_HEADERS = ["timestamp", "side", "symbol", "price", "size", "order_id", "status"]

def write_trades(path, rows):
    if not rows:
        pd.DataFrame(columns=CSV_HEADERS).to_csv(path, index=False)
        return
    
    df = pd.DataFrame(rows)
    
    df.to_csv(path, index=False, columns=CSV_HEADERS)


def load_ohlcv_csv(path):
    df = pd.read_csv(path)
    
    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    except:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    if 'symbol' not in df.columns:
        df['symbol'] = 'UNK'

    if 'timeframe' not in df.columns:
        df['timeframe'] = 'UNK'
    
    bars = []
    for _, row in df.iterrows():
        bar = Bar(
            timestamp=row['timestamp'].to_pydatetime(),
            open=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            volume=float(row['volume']),
            symbol=row['symbol'],
            timeframe=row['timeframe'],
        )

        bars.append(bar)
    
    return bars
