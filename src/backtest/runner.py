from dataclasses import dataclass
from typing import Callable, List, Tuple

import polars as pl


@dataclass
class BacktestResult:
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    total_trades: int
    backtest_days: int


def compute_simple_kpis(
    equity: List[float], daily_returns: List[float]
) -> Tuple[float, float, float]:
    if not equity or not daily_returns:
        return 0.0, 0.0, 0.0
    total_return = (equity[-1] / equity[0]) - 1.0 if equity[0] != 0 else 0.0
    # Max drawdown
    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    # Simple sharpe (no rf), using daily returns
    import statistics

    if len(daily_returns) > 1:
        mean = statistics.mean(daily_returns)
        stdev = statistics.pstdev(daily_returns) or 1e-9
        sharpe = (mean / stdev) * (252**0.5)
    else:
        sharpe = 0.0
    return total_return, max_dd, sharpe


def run_backtest(
    ohlcv: pl.DataFrame,
    signal_fn: Callable[[pl.DataFrame], List[int]],
    initial_equity: float = 10000.0,
) -> BacktestResult:
    """Minimal backtest loop: generate signals, track equity.

    - ohlcv columns: [timestamp, open, high, low, close, volume]
    - signal_fn returns a list of +1 (long), 0 (flat) for each row
    - fills at close for simplicity
    """
    if ohlcv.is_empty():
        return BacktestResult(0.0, 0.0, 0.0, 0, 0)

    closes = ohlcv["close"].to_list()
    signals = signal_fn(ohlcv)
    n = min(len(closes), len(signals))
    if n == 0:
        return BacktestResult(0.0, 0.0, 0.0, 0, 0)

    equity = [initial_equity]
    total_trades = 0
    daily_returns: List[float] = []

    for i in range(1, n):
        # Trades counted on transition 0 -> 1 (enter on close[i])
        if signals[i - 1] == 0 and signals[i] == 1:
            total_trades += 1

        # Apply period return based on whether we were IN a position during (i-1 -> i)
        if signals[i - 1] == 1 and closes[i - 1] > 0:
            r_t = (closes[i] - closes[i - 1]) / closes[i - 1]
        else:
            r_t = 0.0

        equity.append(equity[-1] * (1.0 + r_t))
        daily_returns.append(r_t)

    total_return, max_dd, sharpe = compute_simple_kpis(equity, daily_returns)
    # days approx by rows
    return BacktestResult(total_return, max_dd, sharpe, total_trades, n)
