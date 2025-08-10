"""
Technical Analysis Module

This module provides functions for calculating various technical indicators
used in the trading strategies. All functions are designed to work with
Polars DataFrames that contain OHLCV data.
"""

from typing import Optional

import polars as pl


def calculate_sma(data: pl.DataFrame, length: int = 20) -> Optional[pl.Series]:
    """
    Calculates the Simple Moving Average (SMA) using Polars.

    Args:
        data (pl.DataFrame): DataFrame with a 'close' price column.
        length (int): The period over which to calculate the SMA.

    Returns:
        Optional[pl.Series]: A Polars Series containing the SMA values,
                             or None if the DataFrame is too small.
    """
    if len(data) < length:
        return None
    return data["close"].rolling_mean(window_size=length)


def calculate_ema(data: pl.DataFrame, length: int = 20) -> Optional[pl.Series]:
    """
    Calculates the Exponential Moving Average (EMA) using Polars.

    Args:
        data (pl.DataFrame): DataFrame with a 'close' price column.
        length (int): The period over which to calculate the EMA.

    Returns:
        Optional[pl.Series]: A Polars Series containing the EMA values,
                             or None if the DataFrame is too small.
    """
    if len(data) < length:
        return None
    return data["close"].ewm_mean(span=length, adjust=False)


def calculate_atr(data: pl.DataFrame, length: int = 14) -> Optional[pl.Series]:
    """
    Calculates the Average True Range (ATR) using Polars.

    ATR is a measure of market volatility.

    Args:
        data (pl.DataFrame): DataFrame with 'high', 'low', and 'close' columns.
        length (int): The period over which to calculate the ATR.

    Returns:
        Optional[pl.Series]: A Polars Series containing the ATR values,
                             or None if the DataFrame is too small.
    """
    if len(data) < length:
        return None

    high_low = data["high"] - data["low"]
    high_close = (data["high"] - data["close"].shift(1)).abs()
    low_close = (data["low"] - data["close"].shift(1)).abs()

    # Calculate True Range by taking the max of the three series row-wise
    tr = data.select(
        pl.max_horizontal([high_low, high_close, low_close]).alias("tr")
    ).to_series()

    atr = tr.rolling_mean(window_size=length)

    return atr
