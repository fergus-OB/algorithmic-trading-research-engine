# broker.py
"""
Broker wrapper for Alpaca paper-trading integration.

This module keeps broker/API operations separate from strategy logic.
Credentials should be stored locally in a .env file and must not be committed
to GitHub.
"""

import os
from dataclasses import dataclass
import pandas as pd
from alpaca_trade_api import REST
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Broker:
    """
    Lightweight wrapper around the Alpaca REST client.
    """

    client: REST

    @classmethod
    def create(cls):
        """
        Create an Alpaca broker client from environment variables.
        """
        key = os.getenv("APCA_API_KEY_ID")
        sec = os.getenv("APCA_API_SECRET_KEY")
        url = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

        if not key or not sec:
            raise RuntimeError(
                "Missing Alpaca API credentials. Add APCA_API_KEY_ID and "
                "APCA_API_SECRET_KEY to a local .env file."
            )

        return cls(REST(key_id=key, secret_key=sec, base_url=url, api_version="v2"))

    def account(self):
        """
        Return Alpaca account information.
        """
        return self.client.get_account()

    def get_equity(self) -> float:
        """
        Return current account equity.
        """
        return float(self.client.get_account().equity)

    def positions_value(self, symbol: str) -> float:
        """
        Return current market value of a position.
        """
        try:
            position = self.client.get_position(symbol)
            return float(position.market_value)
        except Exception:
            return 0.0

    def get_bars_minute(self, symbol: str, minutes: int = 2000) -> pd.DataFrame:
        """
        Pull recent one-minute bars from Alpaca.

        Parameters
        ----------
        symbol : str
            Ticker symbol.
        minutes : int
            Number of recent minute bars to request.

        Returns
        -------
        pd.DataFrame
            DataFrame with timestamp, OHLC, and volume columns.
        """
        bars = self.client.get_bars(symbol, "1Min", limit=minutes).df

        if bars.empty:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

        bars = bars.reset_index().rename(columns={"timestamp": "timestamp"})
        bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)

        return bars[["timestamp", "open", "high", "low", "close", "volume"]]

    def place_bracket(
        self,
        symbol: str,
        qty: float,
        side: str,
        take_profit_price: float,
        stop_loss_price: float,
    ):
        """
        Place a bracket order with take-profit and stop-loss child orders.
        """
        qty_str = f"{qty:.4f}"

        order = self.client.submit_order(
            symbol=symbol,
            qty=qty_str,
            side=side,
            type="market",
            time_in_force="day",
            extended_hours=True,
            order_class="bracket",
            take_profit={"limit_price": round(take_profit_price, 2)},
            stop_loss={"stop_price": round(stop_loss_price, 2)},
        )

        return order

    def flat_position(self, symbol: str) -> None:
        """
        Close an open position in the given symbol if one exists.
        """
        try:
            self.client.close_position(symbol)
        except Exception:
            pass
