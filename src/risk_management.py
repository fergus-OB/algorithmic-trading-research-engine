"""
Risk management utilities for the algorithmic trading research engine.

This module will contain position sizing, stop-loss, exposure, and portfolio
risk control logic used during strategy testing.
"""


def calculate_position_size(account_value: float, risk_per_trade: float, stop_distance: float):
    """
    Calculate position size based on account risk and stop distance.

    Parameters
    ----------
    account_value : float
        Current account or portfolio value.
    risk_per_trade : float
        Fraction of account value risked per trade, e.g. 0.01 for 1%.
    stop_distance : float
        Distance between entry price and stop-loss price.

    Returns
    -------
    float
        Position size based on the risk model.
    """
    raise NotImplementedError("Position sizing logic will be added here.")


def max_drawdown(equity_curve):
    """
    Calculate maximum drawdown from an equity curve.

    Parameters
    ----------
    equity_curve : Series
        Portfolio value over time.

    Returns
    -------
    float
        Maximum drawdown value.
    """
    raise NotImplementedError("Drawdown logic will be added here.")
