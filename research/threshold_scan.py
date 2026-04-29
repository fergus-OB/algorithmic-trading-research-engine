# threshold_scan.py
"""
Threshold-scan research tool for event-based strategy testing.

This script tests simple drop/rise threshold combinations on OHLCV data and
reports summary performance statistics. It is intended for research only.
"""

import os
import math
import glob
import argparse
import numpy as np
import pandas as pd


def load_csv(path: str) -> pd.DataFrame:
    """
    Load a CSV file containing OHLCV market data.

    Expected columns:
    time, open, high, low, close, volume
    """
    data = pd.read_csv(path, parse_dates=["time"])
    data = data.set_index("time").sort_index()
    return data[["open", "high", "low", "close", "volume"]].copy()


def add_vol_metrics(data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Add rolling volatility and ATR-style range metrics.
    """
    output = data.copy()
    output["ret"] = np.log(output["close"]).diff()
    output["vol_win"] = output["ret"].rolling(window).std()

    tr1 = (output["high"] - output["low"]).abs()
    tr2 = (output["high"] - output["close"].shift()).abs()
    tr3 = (output["low"] - output["close"].shift()).abs()

    output["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    output["atr"] = output["true_range"].rolling(window).mean()

    return output


def drawdown(equity_series: pd.Series) -> float:
    """
    Calculate maximum drawdown from an equity series.
    """
    peak = equity_series.cummax()
    drawdowns = equity_series / peak - 1
    return float(drawdowns.min())


def count_threshold_swings(
    data: pd.DataFrame,
    drop: float = 0.10,
    rise: float = 0.10,
    fee_bp: float = 1.0,
    slip_bp_side: float = 3.0,
):
    """
    Event-based threshold backtest.

    Logic:
    - When flat, buy after a selected percentage drop from a reference peak.
    - When long, sell after a selected percentage rise from entry.
    """
    prices = data["close"].values
    times = data.index.values

    position = 0
    reference_price = prices[0]
    entry_price = None
    trades = []
    equity_multiplier = 1.0

    cost_per_turn = (fee_bp / 1e4) + 2 * (slip_bp_side / 1e4)

    for i in range(1, len(prices)):
        price = prices[i]

        if position == 0:
            reference_price = max(reference_price, price)

            if price <= reference_price * (1 - drop):
                position = 1
                entry_price = price
                trades.append({"time": times[i], "side": "BUY", "price": price})
                equity_multiplier *= 1 - cost_per_turn

        else:
            if price >= entry_price * (1 + rise):
                position = 0
                pnl = (price / entry_price) - 1
                equity_multiplier *= 1 + pnl
                equity_multiplier *= 1 - cost_per_turn
                trades.append(
                    {"time": times[i], "side": "SELL", "price": price, "pnl": pnl}
                )
                reference_price = price
                entry_price = None

    if position == 1 and entry_price is not None:
        equity_multiplier *= prices[-1] / entry_price

    trades_df = pd.DataFrame(trades)
    completed_trades = (
        int((trades_df["side"] == "SELL").sum()) if not trades_df.empty else 0
    )

    cagr = np.nan
    if len(data) >= 252:
        cagr = equity_multiplier ** (252 / len(data)) - 1

    avg_pnl = (
        trades_df["pnl"].dropna().mean()
        if "pnl" in trades_df.columns
        else np.nan
    )

    summary = {
        "equity_mult": equity_multiplier,
        "CAGR": cagr,
        "trades": completed_trades,
        "avg_pnl_trade": avg_pnl,
    }

    return summary, trades_df


def grid_search(data: pd.DataFrame, drops, rises, vol_scale=None) -> pd.DataFrame:
    """
    Test multiple drop/rise threshold combinations.
    """
    base = add_vol_metrics(data)
    results = []

    for drop_value in drops:
        for rise_value in rises:
            if vol_scale is not None:
                sigma = base["vol_win"].median(skipna=True)
                drop = math.exp(drop_value * vol_scale * sigma) - 1
                rise = math.exp(rise_value * vol_scale * sigma) - 1
            else:
                drop = drop_value
                rise = rise_value

            stats, _ = count_threshold_swings(base.dropna(), drop=drop, rise=rise)
            results.append({"drop": drop, "rise": rise, **stats})

    return pd.DataFrame(results).sort_values("equity_mult", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_glob",
        default="data/*_1Day.csv",
        help="Pattern of CSVs to scan, e.g. data/*_1Day.csv",
    )
    parser.add_argument(
        "--drops",
        default="0.05,0.075,0.10",
        help="Comma-separated drop thresholds.",
    )
    parser.add_argument(
        "--rises",
        default="0.05,0.075,0.10",
        help="Comma-separated rise thresholds.",
    )
    parser.add_argument(
        "--use_vol_scale",
        action="store_true",
        help="Interpret thresholds as volatility-scaled values.",
    )

    args = parser.parse_args()

    drops = [float(value) for value in args.drops.split(",")]
    rises = [float(value) for value in args.rises.split(",")]

    files = glob.glob(args.data_glob)

    if not files:
        print("No CSVs found. Generate sample data first with fetch_alpaca_data.py.")
        return

    for path in files:
        symbol = os.path.basename(path).split("_")[0]
        print(f"\n=== {symbol} ===")
        data = load_csv(path)
        table = grid_search(
            data,
            drops,
            rises,
            vol_scale=2.0 if args.use_vol_scale else None,
        )
        print(table.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
