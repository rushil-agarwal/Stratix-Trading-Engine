# makes the actual calls to binance API
from src.utils.types import *
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from datetime import datetime

class BinanceClient:
    def __init__(self, api_key, api_secret, base_url="https://testnet.binance.vision"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    def _sign(self, params):
        params = {k: v for k, v in params.items() if v is not None}
        query = urlencode(params)
        signature = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        return f"{query}&signature={signature}"

    def place_order(self, symbol, side, quantity, price = None, order_type = "MARKET"):

        path = "/api/v3/order"
        ts = int(time.time() * 1000)
        
        quantity = round(quantity, 4)
        
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
            "timestamp": ts,
        }
        
        if order_type.upper() == "LIMIT":
            params["price"] = price
            params["timeInForce"] = "GTC" 
        
        signed = self._sign(params)
        url = f"{self.base_url}{path}?{signed}"
        resp = self.session.post(url)
        resp.raise_for_status()
        data = resp.json()
        
        fill_price = price
        if data.get("fills") and len(data["fills"]) > 0:

            total_qty = sum(float(f.get("qty", 0)) for f in data["fills"])
            if total_qty > 0:
                weighted_sum = sum(float(f.get("qty", 0)) * float(f.get("price", 0)) for f in data["fills"])
                fill_price = weighted_sum / total_qty

        
        order = Order(
            id=str(data.get("orderId")), symbol=data.get("symbol"), side=data.get("side"),
            size=float(data.get("origQty", 0)),
            price=fill_price,
            status=data.get("status"),
            filled_size=float(data.get("executedQty", 0)),
            timestamp=datetime.now(),
        )

        return order

    def get_account(self):
        path = "/api/v3/account"
        ts = int(time.time() * 1000)
        params = {"timestamp": ts}
        signed = self._sign(params)
        url = f"{self.base_url}{path}?{signed}"
        resp = self.session.get(url)
        resp.raise_for_status()

        return resp.json()

    def get_historical_klines(self, symbol, timeframe, start = None, end = None, limit = 500):
        #return past data in range start to end
        #used to either prefill data while live trading, or getting data for 
        # backtesting
        
        path = "/api/v3/klines"
        params = {"symbol": symbol, "interval": timeframe, "limit": limit}
        
        if start is not None:
            params["startTime"] = start
        
        if end is not None:
            params["endTime"] = end
        
        url = f"{self.base_url}{path}?{urlencode(params)}"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        bars = []
        
        for k in data:
            b = Bar(
                timestamp=datetime.fromtimestamp(k[0] / 1000),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
                symbol=symbol,
                timeframe=timeframe,
            )

            bars.append(b)

        return bars
