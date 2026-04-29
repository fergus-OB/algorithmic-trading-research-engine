"""
Technical indicator utilities for the algorithmic trading research engine.

This module will contain reusable functions for calculating indicators used
in systematic trading strategy research.
"""


def simple_moving_average(prices, window: int):
    """
    Calculate a simple moving average.

    Parameters
    ----------
    prices : Series
        Series of price values.
    window : int
        Rolling window length.

    Returns
    -------
    Series
        Simple moving average values.
    """
    raise NotImplementedError("Simple moving average logic will be added here.")


def relative_strength_index(prices, window: int = 14):
    """
    Calculate the Relative Strength Index.

    Parameters
    ----------
    prices : Series
        Series of price values.
    window : int
        RSI lookback window.

    Returns
    -------
    Series
        RSI values.
    """
    raise NotImplementedError("RSI logic will be added here.")
