import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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
                pnl = (short_df.iloc[0]["entry_price"] - price) * close_size

                trades.append({
                    "symbol": symbol,
                    "entry_price": short_df.iloc[0]["entry_price"],
                    "exit_price": price,
                    "size": close_size,
                    "pnl": pnl
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
                pnl = (price - long_df.iloc[0]["entry_price"]) * close_size

                trades.append({
                    "symbol": symbol,
                    "entry_price": long_df.iloc[0]["entry_price"],
                    "exit_price": price,
                    "size": close_size,
                    "pnl": pnl
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


    unrealized_pnl = ((last_price - long_df["entry_price"]) * long_df["size"]).sum() +  ((short_df["entry_price"] - last_price) * short_df["size"]).sum()

    return pd.DataFrame(trades), unrealized_pnl, total_orders


def calculate_metrics(df, label, unrealized_pnl=0.0, total_orders=0):
    realized_pnl = df["pnl"].sum()

    return {
        "label": label,
        "total_orders": total_orders,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": realized_pnl + unrealized_pnl,
        "avg_pnl": df["pnl"].mean(),
        "largest_win": df.loc[df["pnl"] > 0, "pnl"].max(),
        "largest_loss": df.loc[df["pnl"] < 0, "pnl"].min(),
    }


def print_metrics(m):
    print(f"\n{m['label']}")
    print("_" * 80)
    for k, v in [
        ("Total Orders", m["total_orders"]),
        ("Realized PnL", f"{m['realized_pnl']:.4f} "),
        ("Unrealized PnL", f"{m['unrealized_pnl']:.4f} "),
        ("Total PnL", f"{m['total_pnl']:.4f} "),
        ("Average PnL", f"{m['avg_pnl']:.4f} "),
        ("Largest Win", f"{m['largest_win']:.4f} "),
        ("Largest Loss", f"{m['largest_loss']:.4f} ")
    ]:
        print(f"  {k}                   {v}")
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
    print(f"\nMetric                             Backtest               Live             Diff")
    print("_" * 80)

    print(f"Total Orders:                           {bt['total_orders']}                   {lv['total_orders']}           {lv['total_orders'] - bt['total_orders']}")
    print(f"Total PNL:                           {bt['total_pnl']:.4f}             {lv['total_pnl']:.4f}           {lv['total_pnl'] - bt['total_pnl']:.4f}")
    print(f"Avg PNL:                             {bt['avg_pnl']:.4f}              {lv['avg_pnl']:.4f}           {lv['avg_pnl'] - bt['avg_pnl']:.4f}")
   
    print()


if __name__ == "__main__":
    main()
