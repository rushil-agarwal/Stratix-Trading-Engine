import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CSV_HEADERS = ["timestamp", "side", "symbol", "price", "size", "order_id", "status"]

def calculate_pnl(df):
    if df.empty:
        return pd.DataFrame(), 0.0, 0

    long_df = pd.DataFrame(columns=["entry_price", "size", "symbol"])
    short_df = pd.DataFrame(columns=["entry_price", "size", "symbol"])
    trades = []

    last_price = df.iloc[-1]["price"]
    total_orders = len(df)

    for row in df.itertuples(index=False):
        side = row.side.upper()
        qty = row.size
        price = row.price
        symbol = row.symbol

        if side == "BUY":
            while qty > 0 and not short_df.empty:
                close_size = min(short_df.iloc[0]["size"], qty)
                entry_price = short_df.iloc[0]["entry_price"]
                pnl = (entry_price - price) * close_size
                ret = (entry_price - price) / entry_price if entry_price > 0 else 0.0

                trades.append({
                    "symbol": symbol,
                    "direction": "SHORT",
                    "entry_price": entry_price,
                    "exit_price": price,
                    "size": close_size,
                    "pnl": pnl,
                    "return": ret
                })

                short_df.at[short_df.index[0], "size"] -= close_size
                qty -= close_size

                if short_df.iloc[0]["size"] <= 0:
                    short_df = short_df.iloc[1:].reset_index(drop=True)

            if qty > 0:
                long_df = pd.concat([
                    long_df,
                    pd.DataFrame([{"entry_price": price, "size": qty, "symbol": symbol}])
                ], ignore_index=True)

        else:
            while qty > 0 and not long_df.empty:
                close_size = min(long_df.iloc[0]["size"], qty)
                entry_price = long_df.iloc[0]["entry_price"]
                pnl = (price - entry_price) * close_size
                ret = (price - entry_price) / entry_price if entry_price > 0 else 0.0

                trades.append({
                    "symbol": symbol,
                    "direction": "LONG",
                    "entry_price": entry_price,
                    "exit_price": price,
                    "size": close_size,
                    "pnl": pnl,
                    "return": ret
                })

                long_df.at[long_df.index[0], "size"] -= close_size
                qty -= close_size

                if long_df.iloc[0]["size"] <= 0:
                    long_df = long_df.iloc[1:].reset_index(drop=True)

            if qty > 0:
                short_df = pd.concat([
                    short_df,
                    pd.DataFrame([{"entry_price": price, "size": qty, "symbol": symbol}])
                ], ignore_index=True)

    unrealized_pnl = ((last_price - long_df["entry_price"]) * long_df["size"]).sum() + ((short_df["entry_price"] - last_price) * short_df["size"]).sum()

    return pd.DataFrame(trades), unrealized_pnl, total_orders


def calculate_metrics(df, label, unrealized_pnl=0.0, total_orders=0):
    if df.empty or "pnl" not in df.columns:
        return {
            "label": label,
            "total_orders": total_orders,
            "realized_pnl": 0.0,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": unrealized_pnl,
            "avg_pnl": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "avg_return": 0.0,
            "largest_win_return": 0.0,
            "largest_loss_return": 0.0,
            "win_rate": 0.0,
        }

    has_wins = len(df.loc[df["pnl"] > 0]) > 0
    has_losses = len(df.loc[df["pnl"] < 0]) > 0
    
    win_rate = (len(df.loc[df["pnl"] > 0]) / len(df)) * 100 if len(df) > 0 else 0.0

    return {
        "label": label,
        "total_orders": total_orders,
        "realized_pnl": df["pnl"].sum(),
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": df["pnl"].sum() + unrealized_pnl,
        "avg_pnl": df["pnl"].mean(),
        "largest_win": df.loc[df["pnl"] > 0, "pnl"].max() if has_wins else 0.0,
        "largest_loss": df.loc[df["pnl"] < 0, "pnl"].min() if has_losses else 0.0,
        "avg_return": df["return"].mean() * 100 if "return" in df.columns else 0.0,
        "largest_win_return": df.loc[df["return"] > 0, "return"].max() * 100 if has_wins and "return" in df.columns else 0.0,
        "largest_loss_return": df.loc[df["return"] < 0, "return"].min() * 100 if has_losses and "return" in df.columns else 0.0,
        "win_rate": win_rate,
    }


def print_metrics(m):
    print(f"\n{m['label']}")
    print("_" * 80)
    for k, v in [
        ("Total Orders", m["total_orders"]),
        ("Realized PnL", f"{m['realized_pnl']:.4f}"),
        ("Unrealized PnL", f"{m['unrealized_pnl']:.4f}"),
        ("Total PnL", f"{m['total_pnl']:.4f}"),
        ("Average PnL", f"{m['avg_pnl']:.4f}"),
        ("Largest Win PnL", f"{m['largest_win']:.4f}"),
        ("Largest Loss PnL", f"{m['largest_loss']:.4f}"),
        ("Win Rate", f"{m['win_rate']:.2f}%"),
        ("Average Return", f"{m['avg_return']:.4f}%"),
        ("Largest Win Return", f"{m['largest_win_return']:.4f}%"),
        ("Largest Loss Return", f"{m['largest_loss_return']:.4f}%"),
    ]:
        print(f"  {k:<22} {v}")
    print()


def main():
    backtest_orders = pd.read_csv("data/backtest_trades.csv", parse_dates=["timestamp"])
    live_orders = pd.read_csv("data/live_trades.csv", parse_dates=["timestamp"])

    bt_trades, bt_unrealized, bt_total = calculate_pnl(backtest_orders)
    lv_trades, lv_unrealized, lv_total = calculate_pnl(live_orders)

    bt = calculate_metrics(bt_trades, "BACKTEST", bt_unrealized, bt_total)
    lv = calculate_metrics(lv_trades, "LIVE", lv_unrealized, lv_total)

    print_metrics(bt)
    print_metrics(lv)

    print("\nBACKTEST vs LIVE")
    print(f"\n{'Metric':<25} {'Backtest':<20} {'Live':<20} {'Diff':<20}")
    print("_" * 80)

    print(f"{'Total Orders:':<25} {bt['total_orders']:<20} {lv['total_orders']:<20} {lv['total_orders'] - bt['total_orders']:<20}")
    print(f"{'Total PNL:':<25} {bt['total_pnl']:<20.4f} {lv['total_pnl']:<20.4f} {lv['total_pnl'] - bt['total_pnl']:<20.4f}")
    print(f"{'Avg PNL:':<25} {bt['avg_pnl']:<20.4f} {lv['avg_pnl']:<20.4f} {lv['avg_pnl'] - bt['avg_pnl']:<20.4f}")
    bt_wr = f"{bt['win_rate']:.2f}%"
    lv_wr = f"{lv['win_rate']:.2f}%"
    diff_wr = f"{lv['win_rate'] - bt['win_rate']:.2f}%"
    
    bt_ret = f"{bt['avg_return']:.4f}%"
    lv_ret = f"{lv['avg_return']:.4f}%"
    diff_ret = f"{lv['avg_return'] - bt['avg_return']:.4f}%"

    print(f"{'Win Rate:':<25} {bt_wr:<20} {lv_wr:<20} {diff_wr:<20}")
    print(f"{'Avg Return:':<25} {bt_ret:<20} {lv_ret:<20} {diff_ret:<20}")
   
    print()


if __name__ == "__main__":
    main()
