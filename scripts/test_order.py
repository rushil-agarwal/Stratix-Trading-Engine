import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.config import load_config
from src.trading.exchange import BinanceClient
import json

config = load_config()
BINANCE_API_KEY = config.BINANCE_API_KEY
BINANCE_API_SECRET = config.BINANCE_API_SECRET

def test_place_order(qty):
    client = BinanceClient(BINANCE_API_KEY, BINANCE_API_SECRET)
    print(f"quantity={qty}")
    print("_"*100)
    order = client.place_order(
        symbol="ETHUSDT",
        side="BUY",
        quantity=qty,
        order_type="MARKET"
    )
    print(f"Order placed")
    print(f"  Status: {order.status}")
    print(f"  Filled: {order.filled_size} at price {order.price}")
    return True



quantities=[0.03376,0.034,0.01,0.1,]
    
for q in quantities:
    test_place_order(q)
