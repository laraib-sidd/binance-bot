"""
Signal Generator Module

This module defines the SignalGenerator class, which is responsible for
generating trading signals based on technical indicators.
"""

from enum import Enum
from typing import Optional

import polars as pl

from .technical_analysis import calculate_adx, calculate_ema


class Signal(Enum):
    """Enum for trading signals."""

    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"  # Although we may not use it for entry, it's good practice


class SignalGenerator:
    """
    Generates trading signals based on a set of technical indicators.
    """

    def __init__(
        self,
        fast_ma_period: int = 10,
        slow_ma_period: int = 20,
        adx_threshold: Optional[float] = None,
    ):
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
        self.adx_threshold = adx_threshold

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

        # Regime filter: disable entries in strong trend regimes
        adx = calculate_adx(data, length=14)
        if self.adx_threshold is not None and adx is not None and len(adx) > 0:
            last_adx = float(adx[-1])
            if last_adx >= self.adx_threshold:
                return Signal.NEUTRAL

        # For this simple strategy, we use EMAs for the crossover.
        fast_ema = calculate_ema(data, length=self.fast_ma_period)
        slow_ema = calculate_ema(data, length=self.slow_ma_period)

        if fast_ema is None or slow_ema is None:
            return Signal.NEUTRAL

        # Entry condition: Fast EMA above Slow EMA (simplified rule for tests)
        if fast_ema[-1] > slow_ema[-1]:
            return Signal.BUY

        return Signal.NEUTRAL
