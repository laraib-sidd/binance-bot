"""
Helios Trading Bot - Grid Calculator Unit Tests

Tests for dynamic grid calculation based on ATR and market conditions.
"""

from decimal import Decimal

from src.trading.grid_calculator import (
    GridCalculator,
    calculate_atr_based_grid,
)
from src.trading.grid_models import GridConfig, GridSide


class TestGridCalculator:
    """Tests for GridCalculator functionality."""

    def test_calculate_grid_success(self) -> None:
        """Test successful grid calculation."""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_levels=8,
            range_multiplier=Decimal("2.0"),
        )
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),  # 2% volatility
            available_capital=Decimal("10000"),
            price_precision=2,
            quantity_precision=5,
        )

        assert result.success is True
        assert result.session is not None
        assert result.session.symbol == "BTCUSDT"
        assert result.session.entry_price == Decimal("50000")

    def test_calculate_grid_bounds(self) -> None:
        """Test grid bounds calculation from ATR."""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_levels=8,
            range_multiplier=Decimal("2.0"),
        )
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),  # ATR = 1000
            available_capital=Decimal("10000"),
        )

        session = result.session
        assert session is not None

        # Range should be 2 * ATR = 2000 on each side
        # Upper = 50000 + 2000 = 52000
        # Lower = 50000 - 2000 = 48000
        assert session.upper_bound == Decimal("52000")
        assert session.lower_bound == Decimal("48000")

    def test_calculate_grid_spacing(self) -> None:
        """Test grid spacing calculation."""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_levels=8,
            range_multiplier=Decimal("2.0"),
        )
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        session = result.session
        assert session is not None

        # Total range = 52000 - 48000 = 4000
        # Spacing = 4000 / 8 = 500
        assert session.grid_spacing == Decimal("500")

    def test_calculate_grid_levels_count(self) -> None:
        """Test correct number of grid levels generated."""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_levels=8,
        )
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        session = result.session
        assert session is not None

        # 8 total levels: 4 buy + 4 sell
        assert len(session.levels) == 8
        assert len(session.buy_levels) == 4
        assert len(session.sell_levels) == 4

    def test_calculate_grid_level_prices(self) -> None:
        """Test grid levels have correct prices."""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_levels=4,  # 2 buy + 2 sell
            range_multiplier=Decimal("2.0"),
        )
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),  # Range +/- 2000
            available_capital=Decimal("10000"),
        )

        session = result.session
        assert session is not None

        # Buy levels should be below current price
        for level in session.buy_levels:
            assert level.price < Decimal("50000")
            assert level.side == GridSide.BUY

        # Sell levels should be above current price
        for level in session.sell_levels:
            assert level.price > Decimal("50000")
            assert level.side == GridSide.SELL

    def test_calculate_grid_stop_loss(self) -> None:
        """Test stop-loss price calculation."""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_levels=8,
            range_multiplier=Decimal("2.0"),
            stop_loss_percent=Decimal("0.02"),  # 2% below lower bound
        )
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        session = result.session
        assert session is not None

        # Lower bound = 48000
        # Stop-loss = 48000 * (1 - 0.02) = 47040
        assert session.stop_loss_price == Decimal("47040")

    def test_calculate_grid_invalid_price(self) -> None:
        """Test grid calculation fails with invalid price."""
        config = GridConfig(symbol="BTCUSDT")
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("0"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        assert result.success is False
        assert "price must be positive" in result.error_message.lower()

    def test_calculate_grid_invalid_atr(self) -> None:
        """Test grid calculation fails with invalid ATR."""
        config = GridConfig(symbol="BTCUSDT")
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("-100"),
            available_capital=Decimal("10000"),
        )

        assert result.success is False
        assert "atr" in result.error_message.lower()

    def test_calculate_grid_invalid_capital(self) -> None:
        """Test grid calculation fails with zero capital."""
        config = GridConfig(symbol="BTCUSDT")
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("0"),
        )

        assert result.success is False
        assert "capital" in result.error_message.lower()

    def test_calculate_grid_spacing_too_small(self) -> None:
        """Test grid fails when spacing is too small."""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_levels=8,
            range_multiplier=Decimal("0.1"),  # Very small range
            min_spacing_percent=Decimal("0.01"),  # 1% minimum
        )
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("100"),  # Small ATR
            available_capital=Decimal("10000"),
        )

        assert result.success is False
        assert "spacing too small" in result.error_message.lower()

    def test_calculate_grid_capital_allocation(self) -> None:
        """Test capital is properly allocated to levels."""
        config = GridConfig(
            symbol="BTCUSDT",
            grid_levels=4,
            risk_per_session=Decimal("0.01"),  # 1% of capital
        )
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        session = result.session
        assert session is not None

        # Allocated capital = 10000 * 0.01 = 100
        assert session.allocated_capital == Decimal("100")

        # 2 buy levels, so 50 per level
        # Quantity = 50 / 50000 (mid price approx) = 0.001
        assert session.order_size_per_level > Decimal("0")

    def test_recalculate_spacing_recommends_on_high_atr_change(self) -> None:
        """Test recalculation is recommended when ATR changes significantly."""
        config = GridConfig(symbol="BTCUSDT")
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        session = result.session
        assert session is not None

        # ATR doubled - should recommend recalculation
        should_recalc = calculator.recalculate_spacing(
            session=session,
            new_atr=Decimal("2000"),  # 100% increase
            current_price=Decimal("50000"),
        )

        assert should_recalc is True

    def test_recalculate_spacing_no_change(self) -> None:
        """Test recalculation not recommended when ATR stable."""
        config = GridConfig(symbol="BTCUSDT")
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        session = result.session
        assert session is not None

        # Small ATR change - should not recommend recalculation
        should_recalc = calculator.recalculate_spacing(
            session=session,
            new_atr=Decimal("1100"),  # 10% increase
            current_price=Decimal("50000"),
        )

        assert should_recalc is False

    def test_recalculate_spacing_price_outside_bounds(self) -> None:
        """Test recalculation recommended when price exits grid."""
        config = GridConfig(symbol="BTCUSDT")
        calculator = GridCalculator(config)

        result = calculator.calculate_grid(
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        session = result.session
        assert session is not None

        # Price moved above upper bound
        should_recalc = calculator.recalculate_spacing(
            session=session,
            new_atr=Decimal("1000"),
            current_price=Decimal("55000"),  # Above 52000 upper
        )

        assert should_recalc is True

    def test_calculate_profit_target_price(self) -> None:
        """Test profit target price calculation."""
        config = GridConfig(symbol="BTCUSDT")
        calculator = GridCalculator(config)

        target = calculator.calculate_profit_target_price(
            buy_price=Decimal("50000"),
            target_percent=Decimal("0.01"),  # 1%
        )

        assert target == Decimal("50500")


class TestConvenienceFunction:
    """Tests for calculate_atr_based_grid convenience function."""

    def test_calculate_atr_based_grid(self) -> None:
        """Test the convenience function works."""
        result = calculate_atr_based_grid(
            symbol="ETHUSDT",
            current_price=Decimal("2000"),
            atr_14=Decimal("50"),
            available_capital=Decimal("5000"),
            grid_levels=6,
        )

        assert result.success is True
        assert result.session is not None
        assert result.session.symbol == "ETHUSDT"
        assert len(result.session.levels) == 6
