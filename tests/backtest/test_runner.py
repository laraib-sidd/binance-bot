import math

import polars as pl

from src.backtest.runner import BacktestResult, run_backtest


def test_run_backtest_minimal() -> None:
    df = pl.DataFrame(
        {
            "timestamp": [1, 2, 3, 4, 5],
            "open": [100, 101, 102, 103, 104],
            "high": [101, 102, 103, 104, 105],
            "low": [99, 100, 101, 102, 103],
            "close": [100, 102, 101, 105, 106],
            "volume": [1, 1, 1, 1, 1],
        }
    )

    # simple enter at t=2, exit at t=4 pattern
    def signals(_df: pl.DataFrame) -> list[int]:
        return [0, 1, 1, 0, 0]

    res = run_backtest(df, signals, initial_equity=1000.0)
    assert isinstance(res, BacktestResult)
    assert res.total_trades == 1
    assert res.backtest_days == 5


def test_backtest_golden_equity_series() -> None:
    # Prices: 100 -> 110 -> 121 (10% up each step); signals long entire time
    df = pl.DataFrame(
        {
            "timestamp": [1, 2, 3],
            "open": [100, 110, 121],
            "high": [100, 110, 121],
            "low": [100, 110, 121],
            "close": [100, 110, 121],
            "volume": [1, 1, 1],
        }
    )

    def signals(_df: pl.DataFrame) -> list[int]:
        return [1, 1, 1]

    res = run_backtest(df, signals, initial_equity=100.0)
    # Two periods of +10%: equity = 100 * 1.1 * 1.1 = 121
    assert math.isclose(res.total_return, 0.21, rel_tol=1e-6)
    assert res.backtest_days == 3


def test_backtest_invariants_flat_when_no_position_or_constant_price() -> None:
    # Constant price, alternating signals; returns 0 unless in position
    df = pl.DataFrame(
        {
            "timestamp": [1, 2, 3, 4],
            "open": [100, 100, 100, 100],
            "high": [100, 100, 100, 100],
            "low": [100, 100, 100, 100],
            "close": [100, 100, 100, 100],
            "volume": [1, 1, 1, 1],
        }
    )

    def signals_all_flat(_df: pl.DataFrame) -> list[int]:
        return [0, 0, 0, 0]

    res_flat = run_backtest(df, signals_all_flat, initial_equity=100.0)
    assert math.isclose(res_flat.total_return, 0.0, rel_tol=1e-9)
