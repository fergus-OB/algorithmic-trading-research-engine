# strategy.py
"""
Dip-buying strategy logic for 15-minute market data.

This module contains reusable strategy functions for:
- resampling one-minute bars into 15-minute OHLCV bars
- detecting dip-entry signals
- calculating position size
- checking take-profit, stop-loss, and time-based exits
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import pandas as pd


@dataclass
class Params:
    """
    Strategy parameters.
    """

    dip_pct: float = 0.015
    tp_pct: float = 0.01
    sl_pct: float = 0.015
    lookback: int = 96
    hold_bars: int = 64
    cooldown: int = 8
    risk_fraction: float = 0.0075
    max_exposure: float = 0.50
    session_utc: Tuple[int, int] = (6, 20)


def in_session(timestamp: pd.Timestamp, session_utc: Tuple[int, int]) -> bool:
    """
    Check whether a timestamp falls inside the allowed UTC trading session.
    """
    hour = timestamp.tz_convert("UTC").hour if timestamp.tzinfo else timestamp.hour
    return session_utc[0] <= hour < session_utc[1]


def resample_15m(data: pd.DataFrame) -> pd.DataFrame:
    """
    Resample one-minute OHLCV data into 15-minute bars.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing timestamp, open, high, low, close, and volume.

    Returns
    -------
    pd.DataFrame
        15-minute OHLCV bars with a timezone-aware datetime index.
    """
    data = data.copy()

    if "timestamp" in data.columns:
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
        data = data.set_index("timestamp")

    for column in ["open", "high", "low", "close", "volume"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    aggregation = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }

    return data.resample("15min").apply(aggregation).dropna()


def compute_rolling_peak(close: pd.Series, lookback: int) -> pd.Series:
    """
    Calculate the rolling peak over the lookback window.
    """
    return close.rolling(lookback, min_periods=lookback).max()


def dip_signal(bars15: pd.DataFrame, params: Params, state: dict) -> Optional[dict]:
    """
    Generate a long entry signal when price drops below a rolling-peak threshold.

    Returns
    -------
    dict or None
        Signal dictionary containing timestamp, entry, take-profit, and stop-loss.
    """
    if len(bars15) < params.lookback + 2:
        return None

    last = bars15.iloc[-1]
    timestamp = last.name

    if not in_session(timestamp, params.session_utc):
        return None

    if state.get("cooldown_left", 0) > 0:
        return None

    close = bars15["close"]
    peak = compute_rolling_peak(close, params.lookback)

    if pd.isna(peak.iloc[-1]):
        return None

    entry_condition = last["close"] <= (1.0 - params.dip_pct) * peak.iloc[-1]

    if entry_condition:
        entry_price = float(last["close"])
        take_profit = entry_price * (1 + params.tp_pct)
        stop_loss = entry_price * (1 - params.sl_pct)

        return {
            "timestamp": timestamp,
            "entry": entry_price,
            "tp": take_profit,
            "sl": stop_loss,
        }

    return None


def position_size(equity: float, entry_price: float, params: Params) -> float:
    """
    Calculate fractional position size using stop-distance risk and exposure cap.
    """
    raw_size = (equity * params.risk_fraction) / (entry_price * params.sl_pct)
    capped_size = (equity * params.max_exposure) / entry_price
    return float(min(raw_size, capped_size))


def should_exit(bars15: pd.DataFrame, params: Params, trade: dict):
    """
    Check whether an open trade should exit.

    Conservative rule:
    If take-profit and stop-loss are both touched in the same candle,
    assume stop-loss was hit first.

    Returns
    -------
    tuple
        (exit_now, exit_price, hit_stop_loss)
    """
    last = bars15.iloc[-1]

    hit_stop_loss = last["low"] <= trade["sl"]
    hit_take_profit = last["high"] >= trade["tp"]
    time_exit = trade["bars_held"] >= params.hold_bars

    if hit_stop_loss and hit_take_profit:
        return True, trade["sl"], True

    if hit_stop_loss:
        return True, trade["sl"], True

    if hit_take_profit:
        return True, trade["tp"], False

    if time_exit:
        return True, float(last["close"]), False

    return False, None, False
