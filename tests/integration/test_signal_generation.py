"""
Integration Tests for the SignalGenerator
"""

import pandas as pd
import polars as pl
import pytest

from src.data.market_data_pipeline import MarketDataPipeline
from src.strategies.signal_generator import MovingAverageCrossoverSignal


@pytest.fixture
def mock_market_data():
    """
    Provides a mock Polars DataFrame for market data.
    This simulates the data that would be returned from the database.
    """
    data = {
        "timestamp": pd.to_datetime(
            [
                "2023-01-01 10:00:00",
                "2023-01-01 10:01:00",
                "2023-01-01 10:02:00",
                "2023-01-01 10:03:00",
                "2023-01-01 10:04:00",
                "2023-01-01 10:05:00",
                "2023-01-01 10:06:00",
                "2023-01-01 10:07:00",
                "2023-01-01 10:08:00",
                "2023-01-01 10:09:00",
                "2023-01-01 10:10:00",
            ]
        ),
        "close_price": [100, 101, 102, 103, 104, 105, 106, 102, 100, 103, 105],
        "high_price": [101, 102, 103, 104, 105, 106, 107, 104, 102, 104, 106],
        "low_price": [99, 100, 101, 102, 103, 104, 105, 101, 99, 102, 104],
    }
    return pl.DataFrame(data)


@pytest.mark.asyncio
async def test_signal_generation_with_mocked_data(mocker, mock_market_data):
    """
    Tests the signal generator with mocked data, avoiding network and DB calls.
    """
    # 1. Mock the method that hits the database
    mocker.patch.object(
        MarketDataPipeline,
        "get_recent_ohlcv",
        return_value=mock_market_data.to_dicts(),  # get_recent_ohlcv returns a list of dicts
    )

    # 2. Initialize the pipeline and signal generator
    # We don't need to call await pipeline.initialize() because we are not using real connections
    pipeline = MarketDataPipeline()
    signal_generator = MovingAverageCrossoverSignal(pipeline)

    # 3. Generate the signal
    signal = await signal_generator.generate_signal("BTCUSDT")

    # 4. Assert the outcome based on the mock data
    # In our mock data, the short-term average (last 5) crosses above the long-term (last 10)
    # Short avg: (106+102+100+103+105)/5 = 103.2
    # Long avg: (101+102+103+104+105+106+102+100+103+105)/10 = 103.1
    # Since short > long, we expect a BUY signal.
    assert signal["signal"] == "BUY"
    assert "short_sma" in signal["context"]
    assert "long_sma" in signal["context"]
    assert signal["context"]["short_sma"] > signal["context"]["long_sma"]


if __name__ == "__main__":
    pytest.main()
