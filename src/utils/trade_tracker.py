from src.utils.types import *

class TradeTracker:
    
    def __init__(self):
        self.all_orders = []  
    
    def add_order(self, order):
        side = order.side.upper()

        order_record = {
            "timestamp": order.timestamp.isoformat(),
            "side": side,
            "symbol": order.symbol,
            "price": order.price or 0,
            "size": order.filled_size,
            "order_id": order.id,
            "status": order.status,
        }
        self.all_orders.append(order_record)
        return order_record
    
    def get_all_orders(self):
        return self.all_orders

