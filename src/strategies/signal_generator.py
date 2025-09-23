"""
Signal Generator Module

This module defines the SignalGenerator class, which is responsible for
generating trading signals based on technical indicators.
"""

from enum import Enum
from typing import Optional

import polars as pl

from .technical_analysis import (
    calculate_adx,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
)


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
        # Optional confirmations (all disabled by default to preserve behavior)
        rsi_length: Optional[int] = None,
        rsi_overbought: Optional[float] = None,
        rsi_oversold: Optional[float] = None,
        macd_confirm: bool = False,
        bb_confirm: bool = False,
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
        self.rsi_length = rsi_length
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.macd_confirm = macd_confirm
        self.bb_confirm = bb_confirm

    def _regime_ok(self, data: pl.DataFrame) -> bool:
        adx = calculate_adx(data, length=14)
        if self.adx_threshold is None or adx is None or len(adx) == 0:
            return True
        return float(adx[-1]) < float(self.adx_threshold)

    def _rsi_ok(self, data: pl.DataFrame) -> bool:
        if self.rsi_length is None:
            return True
        rsi = calculate_rsi(data, length=self.rsi_length)
        if rsi is None or len(rsi) == 0:
            return True
        if self.rsi_overbought is None:
            return True
        return float(rsi[-1]) < float(self.rsi_overbought)

    def _macd_ok(self, data: pl.DataFrame) -> bool:
        if not self.macd_confirm:
            return True
        macd, signal_line, _ = calculate_macd(data)
        return float(macd[-1]) > float(signal_line[-1])

    def _bb_ok(self, data: pl.DataFrame) -> bool:
        if not self.bb_confirm:
            return True
        result = calculate_bollinger_bands(data)
        if result is None:
            return False
        _, middle, _ = result
        return float(data["close"][-1]) > float(middle[-1])

    def generate_signal(self, data: pl.DataFrame) -> Signal:
        """Generate signal using MA crossover with optional confirmations."""
        if len(data) < self.slow_ma_period:
            return Signal.NEUTRAL

        if not self._regime_ok(data):
            return Signal.NEUTRAL
        if not self._rsi_ok(data):
            return Signal.NEUTRAL

        fast_ema = calculate_ema(data, length=self.fast_ma_period)
        slow_ema = calculate_ema(data, length=self.slow_ma_period)
        if fast_ema is None or slow_ema is None:
            return Signal.NEUTRAL

        base_buy = fast_ema[-1] > slow_ema[-1]
        if not base_buy:
            return Signal.NEUTRAL

        if not self._macd_ok(data):
            return Signal.NEUTRAL
        if not self._bb_ok(data):
            return Signal.NEUTRAL

        return Signal.BUY
