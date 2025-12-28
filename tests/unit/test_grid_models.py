"""
Helios Trading Bot - Grid Models Unit Tests

Tests for grid trading models: GridConfig, GridLevel, and GridSession.
"""

from datetime import datetime, timezone
from decimal import Decimal

from src.trading.grid_models import (
    GridConfig,
    GridLevel,
    GridLevelStatus,
    GridSession,
    GridSide,
    GridStatus,
)


class TestGridConfig:
    """Tests for GridConfig validation."""

    def test_default_config_is_valid(self) -> None:
        """Test default configuration passes validation."""
        config = GridConfig(symbol="BTCUSDT")
        errors = config.validate()
        assert errors == []

    def test_invalid_grid_levels_too_few(self) -> None:
        """Test validation fails with too few grid levels."""
        config = GridConfig(symbol="BTCUSDT", grid_levels=2)
        errors = config.validate()
        assert any("at least 4" in e for e in errors)

    def test_invalid_grid_levels_too_many(self) -> None:
        """Test validation fails with too many grid levels."""
        config = GridConfig(symbol="BTCUSDT", grid_levels=30)
        errors = config.validate()
        assert any("not exceed 20" in e for e in errors)

    def test_invalid_grid_levels_odd(self) -> None:
        """Test validation fails with odd grid levels."""
        config = GridConfig(symbol="BTCUSDT", grid_levels=7)
        errors = config.validate()
        assert any("even" in e for e in errors)

    def test_invalid_range_multiplier_too_low(self) -> None:
        """Test validation fails with low range multiplier."""
        config = GridConfig(symbol="BTCUSDT", range_multiplier=Decimal("0.5"))
        errors = config.validate()
        assert any("at least 1.0" in e for e in errors)

    def test_invalid_range_multiplier_too_high(self) -> None:
        """Test validation fails with high range multiplier."""
        config = GridConfig(symbol="BTCUSDT", range_multiplier=Decimal("6.0"))
        errors = config.validate()
        assert any("not exceed 5.0" in e for e in errors)

    def test_invalid_risk_per_session(self) -> None:
        """Test validation fails with high risk per session."""
        config = GridConfig(symbol="BTCUSDT", risk_per_session=Decimal("0.10"))
        errors = config.validate()
        assert any("5%" in e for e in errors)


class TestGridLevel:
    """Tests for GridLevel functionality."""

    def test_grid_level_creation(self) -> None:
        """Test creating a grid level."""
        level = GridLevel(
            level_index=0,
            side=GridSide.BUY,
            price=Decimal("50000"),
            quantity=Decimal("0.01"),
        )
        assert level.side == GridSide.BUY
        assert level.price == Decimal("50000")
        assert level.status == GridLevelStatus.PENDING

    def test_is_complete_false_for_pending(self) -> None:
        """Test is_complete returns False for pending level."""
        level = GridLevel()
        assert level.is_complete is False

    def test_is_complete_true_for_sell_filled(self) -> None:
        """Test is_complete returns True when sell filled."""
        level = GridLevel()
        level.status = GridLevelStatus.SELL_FILLED
        assert level.is_complete is True

    def test_is_active_for_open_order(self) -> None:
        """Test is_active returns True for open order."""
        level = GridLevel()
        level.status = GridLevelStatus.OPEN
        assert level.is_active is True

    def test_is_active_for_buy_filled(self) -> None:
        """Test is_active returns True for buy_filled (waiting for sell)."""
        level = GridLevel()
        level.status = GridLevelStatus.BUY_FILLED
        assert level.is_active is True

    def test_mark_buy_filled(self) -> None:
        """Test marking buy order as filled."""
        level = GridLevel(
            price=Decimal("50000"),
            quantity=Decimal("0.01"),
        )
        fill_time = datetime.now(timezone.utc)
        level.mark_buy_filled(Decimal("49950"), fill_time)

        assert level.status == GridLevelStatus.BUY_FILLED
        assert level.buy_fill_price == Decimal("49950")
        assert level.buy_fill_time == fill_time

    def test_mark_sell_filled_calculates_pnl(self) -> None:
        """Test marking sell order calculates P&L correctly."""
        level = GridLevel(
            price=Decimal("50000"),
            quantity=Decimal("0.01"),
        )
        level.mark_buy_filled(Decimal("50000"), datetime.now(timezone.utc))

        pnl = level.mark_sell_filled(
            fill_price=Decimal("51000"),
            fill_time=datetime.now(timezone.utc),
            commission=Decimal("0.5"),
        )

        # Profit: (51000 - 50000) * 0.01 = 10, minus 0.5 commission = 9.5
        assert pnl == Decimal("9.5")
        assert level.realized_pnl == Decimal("9.5")
        assert level.status == GridLevelStatus.SELL_FILLED

    def test_to_dict_serialization(self) -> None:
        """Test GridLevel serialization."""
        level = GridLevel(
            level_index=2,
            side=GridSide.SELL,
            price=Decimal("55000"),
            quantity=Decimal("0.02"),
        )
        data = level.to_dict()

        assert data["level_index"] == 2
        assert data["side"] == "sell"
        assert data["price"] == "55000"
        assert data["quantity"] == "0.02"
        assert data["status"] == "pending"


class TestGridSession:
    """Tests for GridSession functionality."""

    def test_session_creation(self) -> None:
        """Test creating a grid session."""
        session = GridSession(
            symbol="BTCUSDT",
            entry_price=Decimal("50000"),
            upper_bound=Decimal("52000"),
            lower_bound=Decimal("48000"),
        )
        assert session.status == GridStatus.PENDING
        assert session.symbol == "BTCUSDT"
        assert session.entry_price == Decimal("50000")

    def test_session_start(self) -> None:
        """Test starting a session."""
        session = GridSession(symbol="BTCUSDT")
        session.start()

        assert session.status == GridStatus.ACTIVE
        assert session.started_at is not None

    def test_session_stop(self) -> None:
        """Test stopping a session."""
        session = GridSession(symbol="BTCUSDT")
        session.start()
        session.stop("Manual stop")

        assert session.status == GridStatus.STOPPED
        assert session.ended_at is not None

    def test_session_complete(self) -> None:
        """Test completing a session."""
        session = GridSession(symbol="BTCUSDT")
        session.start()
        session.complete()

        assert session.status == GridStatus.COMPLETED

    def test_buy_levels_filter(self) -> None:
        """Test filtering buy levels."""
        session = GridSession(symbol="BTCUSDT")
        session.levels = [
            GridLevel(level_index=0, side=GridSide.BUY),
            GridLevel(level_index=1, side=GridSide.BUY),
            GridLevel(level_index=0, side=GridSide.SELL),
        ]

        assert len(session.buy_levels) == 2
        assert all(lvl.side == GridSide.BUY for lvl in session.buy_levels)

    def test_sell_levels_filter(self) -> None:
        """Test filtering sell levels."""
        session = GridSession(symbol="BTCUSDT")
        session.levels = [
            GridLevel(level_index=0, side=GridSide.BUY),
            GridLevel(level_index=0, side=GridSide.SELL),
            GridLevel(level_index=1, side=GridSide.SELL),
        ]

        assert len(session.sell_levels) == 2
        assert all(lvl.side == GridSide.SELL for lvl in session.sell_levels)

    def test_active_levels_filter(self) -> None:
        """Test filtering active levels."""
        session = GridSession(symbol="BTCUSDT")
        session.levels = [
            GridLevel(level_index=0, side=GridSide.BUY, status=GridLevelStatus.OPEN),
            GridLevel(
                level_index=1, side=GridSide.BUY, status=GridLevelStatus.BUY_FILLED
            ),
            GridLevel(
                level_index=2, side=GridSide.BUY, status=GridLevelStatus.CANCELLED
            ),
        ]

        assert len(session.active_levels) == 2

    def test_completed_levels_filter(self) -> None:
        """Test filtering completed levels."""
        session = GridSession(symbol="BTCUSDT")
        session.levels = [
            GridLevel(
                level_index=0, side=GridSide.BUY, status=GridLevelStatus.SELL_FILLED
            ),
            GridLevel(level_index=1, side=GridSide.BUY, status=GridLevelStatus.OPEN),
        ]

        assert len(session.completed_levels) == 1

    def test_fill_rate_calculation(self) -> None:
        """Test fill rate calculation."""
        session = GridSession(symbol="BTCUSDT")
        session.levels = [
            GridLevel(
                level_index=0, side=GridSide.BUY, status=GridLevelStatus.SELL_FILLED
            ),
            GridLevel(level_index=1, side=GridSide.BUY, status=GridLevelStatus.OPEN),
            GridLevel(
                level_index=2, side=GridSide.BUY, status=GridLevelStatus.SELL_FILLED
            ),
            GridLevel(
                level_index=3, side=GridSide.BUY, status=GridLevelStatus.CANCELLED
            ),
        ]

        # 2 out of 4 = 50%
        assert session.fill_rate == Decimal("50")

    def test_update_pnl(self) -> None:
        """Test P&L update calculation."""
        session = GridSession(symbol="BTCUSDT")

        # Completed level with profit
        completed_level = GridLevel(
            level_index=0,
            side=GridSide.BUY,
            quantity=Decimal("0.01"),
            status=GridLevelStatus.SELL_FILLED,
            realized_pnl=Decimal("10"),
            commission=Decimal("0.5"),
        )

        # Open level (buy filled, waiting for sell)
        open_level = GridLevel(
            level_index=1,
            side=GridSide.BUY,
            quantity=Decimal("0.01"),
            status=GridLevelStatus.BUY_FILLED,
        )
        open_level.buy_fill_price = Decimal("50000")

        session.levels = [completed_level, open_level]
        session.update_pnl(Decimal("51000"))  # Price went up

        assert session.realized_pnl == Decimal("10")
        assert session.unrealized_pnl == Decimal("10")  # (51000 - 50000) * 0.01
        assert session.total_pnl == Decimal("20")

    def test_record_trade_statistics(self) -> None:
        """Test trade statistics recording."""
        session = GridSession(symbol="BTCUSDT")

        session.record_trade(Decimal("10"))  # Win
        session.record_trade(Decimal("5"))  # Win
        session.record_trade(Decimal("-3"))  # Loss
        session.record_trade(Decimal("0"))  # Breakeven

        assert session.total_trades == 4
        assert session.winning_trades == 2
        assert session.losing_trades == 1
        assert session.win_rate == Decimal("50")

    def test_session_serialization(self) -> None:
        """Test session to_dict and from_dict."""
        session = GridSession(
            symbol="BTCUSDT",
            entry_price=Decimal("50000"),
            upper_bound=Decimal("52000"),
            lower_bound=Decimal("48000"),
            grid_spacing=Decimal("500"),
            atr_value=Decimal("1000"),
            allocated_capital=Decimal("1000"),
            order_size_per_level=Decimal("0.01"),
        )
        session.levels = [
            GridLevel(
                level_index=0,
                side=GridSide.BUY,
                price=Decimal("49500"),
                quantity=Decimal("0.01"),
            )
        ]

        data = session.to_dict()
        restored = GridSession.from_dict(data)

        assert restored.symbol == session.symbol
        assert restored.entry_price == session.entry_price
        assert restored.upper_bound == session.upper_bound
        assert restored.lower_bound == session.lower_bound
        assert len(restored.levels) == 1
        assert restored.levels[0].price == Decimal("49500")
