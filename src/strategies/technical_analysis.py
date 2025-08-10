"""
Technical Analysis Module

This module provides functions for calculating various technical indicators
used in the trading strategies. All functions are designed to work with
Polars DataFrames that contain OHLCV data.
"""

from typing import Optional, Tuple

import polars as pl


def calculate_adx(data: pl.DataFrame, length: int = 14) -> Optional[pl.Series]:
    """
    Calculate production-grade ADX using Wilder's smoothing (vectorized with Polars).

    - True Range (TR): max(high-low, abs(high-prev_close), abs(low-prev_close))
    - +DM / -DM per Wilder: take dominant move or 0
    - Smoothed with Wilder's method via EMA alpha = 1/length (adjust=False)
    - +DI/-DI = 100 * (smoothed +DM/-DM) / ATR
    - DX = 100 * |+DI - -DI| / (+DI + -DI)
    - ADX = Wilder-smoothed DX (alpha = 1/length)

    Returns None if not enough rows.
    """
    if len(data) < length + 1:
        return None

    high = data["high"]
    low = data["low"]
    close = data["close"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    up_move = (high - prev_high).clip(0, None)
    down_move = (prev_low - low).clip(0, None)

    plus_dm = (up_move > down_move).cast(pl.Int8) * up_move
    minus_dm = (down_move > up_move).cast(pl.Int8) * down_move

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = data.select(pl.max_horizontal([tr1, tr2, tr3]).alias("tr")).to_series()

    # Wilder smoothing via EMA(alpha=1/length)
    alpha = 1.0 / float(length)
    atr = tr.ewm_mean(alpha=alpha, adjust=False)
    plus_dm_smooth = plus_dm.ewm_mean(alpha=alpha, adjust=False)
    minus_dm_smooth = minus_dm.ewm_mean(alpha=alpha, adjust=False)

    atr_safe = atr.fill_null(1e-9).clip(1e-9, None)
    plus_di = (plus_dm_smooth / atr_safe) * 100.0
    minus_di = (minus_dm_smooth / atr_safe) * 100.0

    denom = (plus_di + minus_di).fill_null(0.0).clip(1e-9, None)
    dx = ((plus_di - minus_di).abs() / denom) * 100.0
    adx = dx.ewm_mean(alpha=alpha, adjust=False)
    return adx


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


def calculate_rsi(data: pl.DataFrame, length: int = 14) -> Optional[pl.Series]:
    """
    Calculate Relative Strength Index (RSI) using Wilder's smoothing.

    - delta = close.diff()
    - gains = max(delta, 0), losses = max(-delta, 0)
    - smoothed via EMA with alpha=1/length (Wilder)
    - RSI = 100 - 100 / (1 + avg_gain/avg_loss)
    """
    if len(data) < length + 1:
        return None

    close = data["close"]
    delta = close.diff()
    gains = delta.clip(0, None)
    losses = (-delta).clip(0, None)

    alpha = 1.0 / float(length)
    avg_gain = gains.ewm_mean(alpha=alpha, adjust=False)
    avg_loss = losses.ewm_mean(alpha=alpha, adjust=False)
    avg_loss_safe = avg_loss.fill_null(1e-9).clip(1e-9, None)

    rs = avg_gain / avg_loss_safe
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def calculate_macd(
    data: pl.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pl.Series, pl.Series, pl.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Returns a tuple of (macd, signal, histogram).
    """
    close = data["close"]
    ema_fast = close.ewm_mean(span=fast, adjust=False)
    ema_slow = close.ewm_mean(span=slow, adjust=False)
    macd = ema_fast - ema_slow
    signal_line = macd.ewm_mean(span=signal, adjust=False)
    hist = macd - signal_line
    return macd, signal_line, hist


def calculate_bollinger_bands(
    data: pl.DataFrame, length: int = 20, k: float = 2.0
) -> Optional[Tuple[pl.Series, pl.Series, pl.Series]]:
    """
    Calculate Bollinger Bands: (upper, middle=SMA, lower).
    """
    if len(data) < length:
        return None

    close = data["close"]
    sma = close.rolling_mean(window_size=length)
    std = close.rolling_std(window_size=length)
    upper = sma + (std * k)
    lower = sma - (std * k)
    return upper, sma, lower
