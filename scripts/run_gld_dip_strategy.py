# run_gld_dip_strategy.py
"""
Example runner for the 15-minute GLD/IAU dip strategy.

This script connects the broker wrapper and strategy logic. It is intended for
paper-trading research and should not be used for live trading without further
testing, monitoring, and risk controls.
"""

import time

from src.broker import Broker
from src.strategy import Params, resample_15m, dip_signal, position_size, should_exit

SYMBOL = "GLD"
POLL_SECONDS = 30
LOOKBACK_MINUTES = 15 * (96 + 70)


def main() -> None:
    """
    Run the strategy loop.

    The loop:
    - fetches recent one-minute bars
    - resamples them into 15-minute bars
    - checks for exits on open trades
    - checks for new dip-entry signals
    - places bracket orders through Alpaca paper trading
    """
    params = Params(
        dip_pct=0.015,
        tp_pct=0.01,
        sl_pct=0.015,
        lookback=96,
        hold_bars=64,
        cooldown=8,
        risk_fraction=0.0075,
        max_exposure=0.50,
        session_utc=(6, 20),
    )

    broker = Broker.create()

    state = {
        "cooldown_left": 0,
        "in_trade": False,
        "trade": None,
        "last_bar_time": None,
    }

    print(f"Starting paper-trading runner for {SYMBOL}")

    while True:
        try:
            bars_minute = broker.get_bars_minute(SYMBOL, minutes=LOOKBACK_MINUTES)

            if bars_minute.empty:
                time.sleep(POLL_SECONDS)
                continue

            bars15 = resample_15m(bars_minute)
            last_timestamp = bars15.index[-1]

            is_new_bar = (
                state["last_bar_time"] is None
                or last_timestamp > state["last_bar_time"]
            )

            if is_new_bar:
                state["last_bar_time"] = last_timestamp

                if state["cooldown_left"] > 0:
                    state["cooldown_left"] -= 1

                if state["in_trade"] and state["trade"]:
                    state["trade"]["bars_held"] += 1

                if state["in_trade"]:
                    exit_now, exit_price, hit_stop_loss = should_exit(
                        bars15, params, state["trade"]
                    )

                    if exit_now:
                        broker.flat_position(SYMBOL)
                        print(
                            f"[{last_timestamp}] EXIT {SYMBOL} "
                            f"@ approximately {exit_price:.2f} "
                            f"(stop_loss={hit_stop_loss})"
                        )
                        state["in_trade"] = False
                        state["trade"] = None
                        state["cooldown_left"] = params.cooldown

                if (not state["in_trade"]) and state["cooldown_left"] == 0:
                    signal = dip_signal(bars15, params, state)

                    if signal is not None:
                        entry_price = signal["entry"]
                        take_profit = signal["tp"]
                        stop_loss = signal["sl"]

                        equity = broker.get_equity()
                        quantity = position_size(equity, entry_price, params)

                        if quantity < 0.01:
                            print(
                                f"[{last_timestamp}] Signal found but quantity "
                                f"too small. Equity={equity:.2f}"
                            )
                        else:
                            order = broker.place_bracket(
                                symbol=SYMBOL,
                                qty=quantity,
                                side="buy",
                                take_profit_price=take_profit,
                                stop_loss_price=stop_loss,
                            )

                            state["in_trade"] = True
                            state["trade"] = {
                                "entry_px": entry_price,
                                "tp": take_profit,
                                "sl": stop_loss,
                                "bars_held": 0,
                            }

                            print(
                                f"[{last_timestamp}] ENTRY {SYMBOL} "
                                f"qty={quantity:.4f} entry~{entry_price:.2f} "
                                f"tp={take_profit:.2f} sl={stop_loss:.2f} "
                                f"order_id={order.id}"
                            )

        except Exception as exc:
            print(f"Loop error: {exc}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
