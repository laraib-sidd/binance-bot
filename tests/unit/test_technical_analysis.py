"""
Unit Tests for Technical Analysis Indicators (Polars)
"""

import unittest

import polars as pl

from src.strategies.technical_analysis import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)


class TestTechnicalAnalysis(unittest.TestCase):
    def setUp(self) -> None:
        """Set up a sample DataFrame for testing."""
        self.data = pl.DataFrame(
            {
                "high": [110, 112, 108, 115, 118, 120, 122, 125, 130, 128],
                "low": [100, 105, 102, 108, 110, 115, 118, 120, 125, 122],
                "close": [105, 110, 105, 112, 115, 118, 120, 122, 128, 125],
            }
        )

    def test_calculate_sma(self) -> None:
        """Test Simple Moving Average calculation."""
        sma_5 = calculate_sma(self.data, length=5)
        self.assertIsNotNone(sma_5)
        self.assertIsInstance(sma_5, pl.Series)
        self.assertAlmostEqual(sma_5[-1], 122.6)
        self.assertTrue(sma_5.is_null().sum() == 4)

    def test_calculate_ema(self) -> None:
        """Test Exponential Moving Average calculation."""
        ema_5 = calculate_ema(self.data, length=5)
        self.assertIsNotNone(ema_5)
        assert ema_5 is not None
        self.assertIsInstance(ema_5, pl.Series)
        # Polars EMA calculation can differ slightly from Pandas
        self.assertAlmostEqual(ema_5[-1], 122.34, places=2)

    def test_calculate_atr(self) -> None:
        """Test Average True Range calculation."""
        atr_5 = calculate_atr(self.data, length=5)
        self.assertIsNotNone(atr_5)
        self.assertIsInstance(atr_5, pl.Series)
        # Polars ATR calculation can differ slightly
        self.assertAlmostEqual(atr_5[-1], 5.6, places=1)

    def test_insufficient_data(self) -> None:
        """Test that indicators return None for insufficient data."""
        small_data = self.data.slice(0, 3)
        self.assertIsNone(calculate_sma(small_data, length=5))
        self.assertIsNone(calculate_ema(small_data, length=5))
        self.assertIsNone(calculate_atr(small_data, length=5))

    def test_calculate_rsi(self) -> None:
        rsi = calculate_rsi(self.data, length=5)
        self.assertIsNotNone(rsi)
        assert rsi is not None
        self.assertIsInstance(rsi, pl.Series)
        self.assertTrue((rsi >= 0).all() and (rsi <= 100).all())

    def test_calculate_macd(self) -> None:
        result = calculate_macd(self.data)
        self.assertIsNotNone(result)
        assert result is not None
        macd, signal, hist = result
        self.assertIsInstance(macd, pl.Series)
        self.assertIsInstance(signal, pl.Series)
        self.assertIsInstance(hist, pl.Series)
        # histogram is macd - signal; check last value consistency
        self.assertAlmostEqual(float(hist[-1]), float(macd[-1] - signal[-1]), places=6)

    def test_bollinger_bands(self) -> None:
        result = calculate_bollinger_bands(self.data, length=5, k=2.0)
        self.assertIsNotNone(result)
        assert result is not None
        upper, mid, lower = result
        self.assertIsInstance(upper, pl.Series)
        self.assertIsInstance(mid, pl.Series)
        self.assertIsInstance(lower, pl.Series)
        # Upper >= middle >= lower for last fully-defined point
        self.assertGreaterEqual(float(upper[-1]), float(mid[-1]))
        self.assertGreaterEqual(float(mid[-1]), float(lower[-1]))


if __name__ == "__main__":
    unittest.main()
