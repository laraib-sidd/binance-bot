"""
Signal Generator Module

This module defines the SignalGenerator class, which is responsible for
generating trading signals based on technical indicators.
"""

from enum import Enum

import polars as pl

from .technical_analysis import calculate_ema


class Signal(Enum):
    """Enum for trading signals."""

    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"  # Although we may not use it for entry, it's good practice


class SignalGenerator:
    """
    Generates trading signals based on a set of technical indicators.
    """

    def __init__(self, fast_ma_period: int = 10, slow_ma_period: int = 20):
        """
        Initializes the SignalGenerator with specific periods for moving averages.

        Args:
            fast_ma_period (int): The period for the fast moving average.
            slow_ma_period (int): The period for the slow moving average.
        """
        if fast_ma_period >= slow_ma_period:
            raise ValueError("Fast MA period must be less than Slow MA period.")

        self.fast_ma_period = fast_ma_period
        self.slow_ma_period = slow_ma_period

    def generate_signal(self, data: pl.DataFrame) -> Signal:
        """
        Generates a signal based on a moving average crossover strategy.

        Args:
            data (pl.DataFrame): DataFrame with OHLCV data.

        Returns:
            Signal: The generated trading signal (BUY or NEUTRAL).
        """
        if len(data) < self.slow_ma_period:
            return Signal.NEUTRAL  # Not enough data to generate a signal

        # For this simple strategy, we use EMAs for the crossover.
        fast_ema = calculate_ema(data, length=self.fast_ma_period)
        slow_ema = calculate_ema(data, length=self.slow_ma_period)

        if fast_ema is None or slow_ema is None:
            return Signal.NEUTRAL

        # Signal condition: Fast EMA has crossed above Slow EMA
        if fast_ema[-1] > slow_ema[-1] and fast_ema[-2] <= slow_ema[-2]:
            return Signal.BUY

        return Signal.NEUTRAL
