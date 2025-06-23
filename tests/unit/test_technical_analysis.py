"""
Unit Tests for Technical Analysis Indicators (Polars)
"""

import unittest

import polars as pl

from src.strategies.technical_analysis import (
    calculate_atr,
    calculate_ema,
    calculate_sma,
)


class TestTechnicalAnalysis(unittest.TestCase):
    def setUp(self):
        """Set up a sample DataFrame for testing."""
        self.data = pl.DataFrame(
            {
                "high": [110, 112, 108, 115, 118, 120, 122, 125, 130, 128],
                "low": [100, 105, 102, 108, 110, 115, 118, 120, 125, 122],
                "close": [105, 110, 105, 112, 115, 118, 120, 122, 128, 125],
            }
        )

    def test_calculate_sma(self):
        """Test Simple Moving Average calculation."""
        sma_5 = calculate_sma(self.data, length=5)
        self.assertIsInstance(sma_5, pl.Series)
        self.assertAlmostEqual(sma_5[-1], 122.6)
        self.assertTrue(sma_5.is_null().sum() == 4)

    def test_calculate_ema(self):
        """Test Exponential Moving Average calculation."""
        ema_5 = calculate_ema(self.data, length=5)
        self.assertIsInstance(ema_5, pl.Series)
        # Polars EMA calculation can differ slightly from Pandas
        self.assertAlmostEqual(ema_5[-1], 122.34, places=2)

    def test_calculate_atr(self):
        """Test Average True Range calculation."""
        atr_5 = calculate_atr(self.data, length=5)
        self.assertIsInstance(atr_5, pl.Series)
        # Polars ATR calculation can differ slightly
        self.assertAlmostEqual(atr_5[-1], 5.6, places=1)

    def test_insufficient_data(self):
        """Test that indicators return None for insufficient data."""
        small_data = self.data.slice(0, 3)
        self.assertIsNone(calculate_sma(small_data, length=5))
        self.assertIsNone(calculate_ema(small_data, length=5))
        self.assertIsNone(calculate_atr(small_data, length=5))


if __name__ == "__main__":
    unittest.main()
