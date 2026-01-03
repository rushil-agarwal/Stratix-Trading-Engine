import logging
import sys
import json

def setup_logger(name = "numatix", level = logging.INFO, logfile = None):
   
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    if not logger.hasHandlers():
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        if logfile:
            fh = logging.FileHandler(logfile)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    return logger


def log_market_data(logger, bar, context = None):
    msg = f"Market Data| Timeframe={bar.timeframe} | O={bar.open:.4f} H={bar.high:.4f} L={bar.low:.4f} C={bar.close:.4f} V={bar.volume:.4f}"
    if context:
        msg += f" | {json.dumps(context)}"

    logger.info(msg)


def log_signal_generation(logger, signals, bar, context= None):
    signal_count = len(signals) if signals else 0
    msg = f"Signal Generation | Bar={bar.timestamp.isoformat()} | Signals={signal_count}"
    if signals:
        for sig in signals:
            temp = "BUY" if sig.side == 1 else "SELL" if sig.side == -1 else "HOLD"
            msg += f" | Signal: {temp} {sig.size:.4f} at {sig.price or 'MARKET'}"
    if context:
        msg += f" | {json.dumps(context)}"
    
    logger.info(msg)


def log_order_placement(logger, order, context=None):
    msg = f"ORDER PLACED | OrderID={order.id} | Side={order.side} | Size={order.size} | Price={order.price or 'MARKET'} | Status={order.status}"
    if context:
        msg += f" | {json.dumps(context)}"
    logger.info(msg)


def log_order_fill(logger, order, context=None):
    msg = f"ORDER FILLED | OrderID={order.id}| Side={order.side} | FilledSize={order.filled_size} | FillPrice={order.price} | Status={order.status}"
    
    if context:
        msg += f" | {json.dumps(context)}"
    
    logger.info(msg)


def log_trade(logger, order_record):
    side = order_record.get("side", "UNKNOWN")
    price = order_record.get("price", "NONE")
    size = order_record.get("size", "NONE")
    order_id = order_record.get("order_id", "NONE")
    status = order_record.get("status", "NONE")

    msg = f"Order Logged | OrderID={order_id} | Side={side}| Price={price} | Size={size} | Status={status}"
        
    logger.info(msg)
