import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from datetime import datetime, timedelta
from config.config import load_config
from src.trading.exchange import BinanceClient
import csv

def fetch_and_save(symbol, timeframe, start_date, end_date, output_file):
    config = load_config()
    client = BinanceClient(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, base_url=config.TESTNET_URL)
    
    print(f"GEtting {timeframe} data for {symbol} from {start_date} to {end_date}...")

    limit = 1000
    
    # Convert datetime to milliseconds timestamp for Binance API
    start_ms = int(start_date.timestamp() * 1000)
    end_ms = int(end_date.timestamp() * 1000)
    
    bars = client.get_historical_klines(symbol, timeframe, start=start_ms, end=end_ms, limit=limit)
    
    filtered_bars = [b for b in bars if start_date <= b.timestamp <= end_date]
    
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol', 'timeframe'])
        
        for bar in filtered_bars:
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
    
    print(f"Saved to {output_file}")
    return len(filtered_bars)

if __name__ == "__main__":
    # end_date = datetime.now()
    # start_date = end_date - timedelta(days=30)
    start_date = datetime.strptime('2025-12-29 16:00:00', '%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime('2025-12-29 21:30:00', '%Y-%m-%d %H:%M:%S')
    
    symbol = "ETHUSDT"
    
    count_1m = fetch_and_save(
        symbol=symbol,
        timeframe="1m",
        start_date=start_date,
        end_date=end_date,
        output_file="data/eth_1m.csv"
    )
    
    print(f"Data fetched: {count_1m} 1-minute bars")
    print()