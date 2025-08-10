from pathlib import Path
import sys

import polars as pl
import pytest

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.strategies.signal_generator import Signal, SignalGenerator  # noqa: E402


@pytest.fixture
def mock_ohlcv_data() -> pl.DataFrame:
    """
    Provides a DataFrame simulating a bullish crossover.
    - The fast EMA crosses above the slow EMA at the last time step.
    """
    return pl.DataFrame(
        {
            "timestamp": [
                1672531200000,
                1672534800000,
                1672538400000,
                1672542000000,
                1672545600000,
            ],
            "open": [95, 98, 100, 105, 110],
            "high": [96, 99, 104, 108, 115],
            "low": [94, 97, 99, 103, 108],
            "close": [95, 99, 102, 106, 114],
            "volume": [1000, 1200, 1100, 1300, 1500],
        }
    )


def test_moving_average_crossover_buy_signal(mock_ohlcv_data: pl.DataFrame) -> None:
    """
    Test that a BUY signal is generated on a fast MA crossover.
    """
    signal_generator = SignalGenerator(fast_ma_period=3, slow_ma_period=5)
    signal = signal_generator.generate_signal(mock_ohlcv_data)
    assert signal == Signal.BUY


def test_moving_average_crossover_neutral_signal(mock_ohlcv_data: pl.DataFrame) -> None:
    """
    Test that a NEUTRAL signal is generated when there is no crossover.
    """
    # Reverse the data to simulate a non-crossover (bearish) scenario
    reversed_data = mock_ohlcv_data.reverse()
    signal_generator = SignalGenerator(fast_ma_period=3, slow_ma_period=5)
    signal = signal_generator.generate_signal(reversed_data)
    assert signal == Signal.NEUTRAL


def test_insufficient_data_for_signal(mock_ohlcv_data: pl.DataFrame) -> None:
    """
    Test that a NEUTRAL signal is generated when data is insufficient.
    """
    # Use fewer data points than the slow_ma_period
    insufficient_data = mock_ohlcv_data.slice(0, 4)
    signal_generator = SignalGenerator(fast_ma_period=3, slow_ma_period=5)
    signal = signal_generator.generate_signal(insufficient_data)
    assert signal == Signal.NEUTRAL


def test_signal_generator_init_validation() -> None:
    """
    Test that the SignalGenerator raises an error with invalid MA periods.
    """
    with pytest.raises(
        ValueError, match="Fast MA period must be less than Slow MA period."
    ):
        SignalGenerator(fast_ma_period=10, slow_ma_period=5)

    with pytest.raises(
        ValueError, match="Fast MA period must be less than Slow MA period."
    ):
        SignalGenerator(fast_ma_period=10, slow_ma_period=10)
