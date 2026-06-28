import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from datetime import datetime, timedelta
from config.config import load_config
from src.trading.exchange import BinanceClient
import csv

def fetch_and_save(symbol, timeframe, start_date, end_date, output_file):
    config = load_config()
    client = BinanceClient(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, base_url="https://api.binance.com")
    
    print(f"Getting {timeframe} data for {symbol} from {start_date} to {end_date}...")

    all_bars = []
    current_start = start_date
    limit = 1000
    
    while current_start < end_date:
        start_ms = int(current_start.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)
        
        bars = client.get_historical_klines(symbol, timeframe, start=start_ms, end=end_ms, limit=limit)
        if not bars:
            break
            
        all_bars.extend(bars)
        
        last_ts = bars[-1].timestamp
        if timeframe == "1m":
            next_start = last_ts + timedelta(minutes=1)
        elif timeframe == "15m":
            next_start = last_ts + timedelta(minutes=15)
        elif timeframe == "1h":
            next_start = last_ts + timedelta(hours=1)
        else:
            next_start = last_ts + timedelta(minutes=1)
            
        if next_start <= current_start:
            next_start = current_start + timedelta(minutes=1)
        current_start = next_start
        
        print(f"Fetched {len(bars)} bars, progress to: {last_ts}")
        
    filtered_bars = [b for b in all_bars if start_date <= b.timestamp <= end_date]
    
    seen = set()
    deduped_bars = []
    for b in filtered_bars:
        if b.timestamp not in seen:
            seen.add(b.timestamp)
            deduped_bars.append(b)
            
    deduped_bars.sort(key=lambda x: x.timestamp)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol', 'timeframe'])
        
        for bar in deduped_bars:
            writer.writerow([
                bar.timestamp.isoformat(),
                bar.open,
                bar.high,
                bar.low,
                bar.close,
                bar.volume,
                bar.symbol,
                bar.timeframe
            ])
    
    print(f"Saved {len(deduped_bars)} unique bars to {output_file}")
    return len(deduped_bars)

if __name__ == "__main__":
    start_date = datetime.strptime('2025-12-19 00:00:00', '%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime('2025-12-29 23:59:00', '%Y-%m-%d %H:%M:%S')
    
    symbol = "ETHUSDT"
    
    count_1m = fetch_and_save(
        symbol=symbol,
        timeframe="1m",
        start_date=start_date,
        end_date=end_date,
        output_file="data/eth_1m.csv"
    )
    
    print(f"Data fetched: {count_1m} 1-minute bars")