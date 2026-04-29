# fetch_alpaca_data.py
"""
Fetch historical OHLCV market data from Alpaca Market Data API.

Credentials should be stored in a local .env file and must not be committed
to GitHub.
"""

import os
import argparse
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("APCA_API_KEY_ID")
SEC = os.getenv("APCA_API_SECRET_KEY")

BASE_DATA = "https://data.alpaca.markets"


def fetch_bars(
    symbol: str,
    timeframe: str = "1Day",
    limit: int = 100,
    feed: str = "iex",
    start: str | None = None,
    end: str | None = None,
    adjustment: str = "raw",
) -> pd.DataFrame:
    """
    Fetch OHLCV bars from Alpaca Market Data v2.

    Parameters
    ----------
    symbol : str
        Ticker symbol, e.g. "AAPL", "NVDA", "GLD".
    timeframe : str
        Bar timeframe, e.g. "1Min", "5Min", "15Min", "1Hour", "1Day".
    limit : int
        Maximum number of bars to request.
    feed : str
        Market data feed. Use "iex" for Alpaca's free/basic plan.
    start : str, optional
        ISO8601 start timestamp.
    end : str, optional
        ISO8601 end timestamp.
    adjustment : str
        Price adjustment mode: "raw", "split", "dividend", or "all".

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by time with OHLCV columns.
    """
    if not KEY or not SEC:
        raise RuntimeError(
            "Missing Alpaca API credentials. Add APCA_API_KEY_ID and "
            "APCA_API_SECRET_KEY to a local .env file."
        )

    headers = {
        "APCA-API-KEY-ID": KEY,
        "APCA-API-SECRET-KEY": SEC,
    }

    url = f"{BASE_DATA}/v2/stocks/{symbol}/bars"
    params = {
        "timeframe": timeframe,
        "limit": limit,
        "feed": feed,
        "adjustment": adjustment,
    }

    if start:
        params["start"] = start
    if end:
        params["end"] = end

    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    payload = response.json()
    bars = payload.get("bars")

    if not bars:
        raise RuntimeError(f"No bars returned. Params used: {params}")

    df = pd.DataFrame(bars).rename(
        columns={
            "t": "time",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
        }
    )

    df["time"] = pd.to_datetime(df["time"])
    return df.set_index("time").sort_index()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--timeframe", default="1Day")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--feed", default="iex")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--adjustment", default="raw")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    df = fetch_bars(
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit,
        feed=args.feed,
        start=args.start,
        end=args.end,
        adjustment=args.adjustment,
    )

    print(df.tail(10))

    out = args.out or f"data/{args.symbol}_{args.timeframe}.csv"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df.to_csv(out)
    print(f"Saved {len(df)} rows to: {out}")


if __name__ == "__main__":
    main()
