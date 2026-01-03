# main driver code for backtesting and live trading

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import argparse
from config.config import load_config
import time
from datetime import datetime
from src.utils.logger import log_order_placement, log_trade, log_order_fill, log_signal_generation, log_market_data, setup_logger
from src.strategy.base import Strategy
from src.trading.exchange import BinanceClient
from src.utils.types import Order
from src.utils.types import AccountInfo
from src.utils.trade_tracker import TradeTracker
from src.backtesting.backtest import BacktestEngine
from datetime import datetime
from src.utils.data import write_trades
from src.strategy.multi_tf import MultiTFStrategy
from src.trading.exchange import BinanceClient

class Executor:
    def __init__(self, strategy, broker = None, logger=None):
        self.strategy = strategy
        self.broker = broker
        self.orders = [] 
        self.trade_tracker = TradeTracker()
        self.logger = logger

    def run_backtest(self, start, end, data_path_1m=None, cash=100000, commission=0.002):
        engine = BacktestEngine(
            self.strategy, 
            data_source_1m=data_path_1m,
            logger=self.logger
        )
        
        self.logger.info(f"Starting backtest...")
        
        orders = engine.run(start, end, cash=cash, commission=commission)
        engine.save_trades_csv("data/backtest_trades.csv")
        
        self.logger.info(f"Backtesting completed, {len(orders)} orders saved")
        
        return orders

    def run_live(self, symbol = "ETHUSDT", poll_interval= 60.0):
        # while live trading, fetches latest data, sends it to strategy logic
        # generated signals, and places order if required at interval of 
        # poll_interval

        if hasattr(self.strategy, 'initialize_with_history'):
            self.logger.info(f"Fetching past data to prefill memory")

            hist_1h = self.broker.get_historical_klines(symbol, "1h", limit=100)
            hist_15m = self.broker.get_historical_klines(symbol, "15m", limit=50)
            

            self.strategy.initialize_with_history(hist_1h, hist_15m)

        account_data = self.broker.get_account()

        balance = 0.0
        positions = {}
        
        for asset in account_data.get("balances", []):
            free = float(asset.get("free", 0))

            if free > 0:
                asset_name = asset.get("asset", "")
                positions[asset_name] = free
                if asset_name == "USDT" or asset_name.endswith("USDT"):
                    balance += free
        
        account = AccountInfo(balance=balance, positions=positions)

        try:
            while True:
                # infitie loop for live trading pipeline

                bars_1h = self.broker.get_historical_klines(symbol, "1h", limit=2)
                
                if bars_1h and len(bars_1h) >= 1:
                    bar_1h = bars_1h[-1] 
                    log_market_data(self.logger, bar_1h)
                    self.strategy.on_bar(bar_1h)
                
                bars_15m = self.broker.get_historical_klines(symbol, "15m", limit=2)
                if not bars_15m or len(bars_15m) < 1:
                    time.sleep(poll_interval)
                    continue
                
                bar_15m = bars_15m[-1] 
                
                log_market_data(self.logger, bar_15m)
                
                self.strategy.on_bar(bar_15m)
                
                signals = self.strategy.generate_signals()
                
                log_signal_generation(self.logger, signals, bar_15m)
                
                for sig in signals:

                    # skipping hold signals
                    if sig.side == 0:
                        continue
                    
                    size = self.strategy.position_size(sig, account)
                    
                    sig.size = size
                    order = self.submit_order(sig, bar_15m)
                    
                    order_record = self.trade_tracker.add_order(order)
                    log_trade(self.logger, order_record)
                    
                    if order.side == "BUY":
                        account.balance -= order.filled_size * (order.price)
                    elif order.side == "SELL":
                        account.balance += order.filled_size * (order.price)
                
                self.save_live_trades("data/live_trades.csv")
                
                total_orders = len(self.trade_tracker.get_all_orders())
                self.logger.debug(f"Live Trading Result: {total_orders} total orders logged")
                
                time.sleep(poll_interval)

        except Exception as e:
            self.logger.info(e)
            return
        
    def submit_order(self, signal, bar=None):

        if self.broker is None:
            # no broker is present in backtesting
            # in case of backtesting, we just fill the order directly

            order_side = "BUY" if signal.side == 1 else "SELL" if signal.side == -1 else "HOLD"
            
            fill_price = bar.close if bar else signal.price
            order = Order(
                id=f"sim-{len(self.orders) + 1}",
                symbol=signal.symbol,
                side=order_side,
                size=signal.size,
                price=fill_price,
                status="FILLED",
                filled_size=signal.size,
                timestamp=signal.timestamp if hasattr(signal, "timestamp") else datetime.now(),
            )
            
            log_order_placement(self.logger, order)
            
            self.orders.append(order)
            log_order_fill(self.logger, order)
            self.strategy.on_order_filled(order)
            return order
        else:
            order_type = "MARKET"
            order_price = None
            
            order_side = "BUY" if signal.side == 1 else "SELL" if signal.side == -1 else "HOLD"
            
            order = self.broker.place_order(
                signal.symbol, 
                order_side, 
                signal.size, 
                price=order_price,
                order_type=order_type
            )
            
            log_order_placement(self.logger, order)
            
            self.orders.append(order)
            log_order_fill(self.logger, order)
            
            self.strategy.on_order_filled(order)
            return order

    def save_live_trades(self, path):
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
        
        self.logger.debug(f"Saved {len(rows)} orders to {path}")
        
        return path


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="run backtesting or live")
    parser.add_argument("--mode", choices=["backtest", "live"], required=True)
    parser.add_argument("--data-1m", type=str, help="path to 1-minute ohlcv data for bt", default="data/eth_1m.csv")
    parser.add_argument("--start", type=str, help="Starttime for bt")
    parser.add_argument("--end", type=str, help="Endtime for bt")
    parser.add_argument("--symbol", type=str, default="ETHUSDT")
    parser.add_argument("--logfile", type=str, help="Path to log file in logs/", required = True)

    args = parser.parse_args()

    logger = setup_logger(level=20, logfile=args.logfile)
    config = load_config()

    strategy = MultiTFStrategy({})

    if args.mode == "backtest":
        execr = Executor(strategy, logger=logger)
        start = datetime.fromisoformat(args.start)
        end = datetime.fromisoformat(args.end)
        
        execr.run_backtest(start, end, data_path_1m=args.data_1m)
    else:
        broker = BinanceClient(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, base_url=config.TESTNET_URL)
        execr = Executor(strategy, broker=broker, logger=logger)
        execr.run_live(symbol=args.symbol)
