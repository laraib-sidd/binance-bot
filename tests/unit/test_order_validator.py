"""
Helios Trading Bot - Order Validator Unit Tests

Tests for order validation logic including balance checks, symbol validation,
quantity/price constraints, and notional value requirements.
"""

from decimal import Decimal

import pytest

from src.trading.order_models import Order, OrderSide, OrderType
from src.trading.order_validator import (
    OrderValidator,
    SymbolInfo,
    ValidationResult,
    create_default_symbol_info,
)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating a success result."""
        result = ValidationResult.success()

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_success_with_warnings(self) -> None:
        """Test success result with warnings."""
        result = ValidationResult.success(warnings=["Minor issue"])

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == ["Minor issue"]

    def test_failure_result(self) -> None:
        """Test creating a failure result."""
        result = ValidationResult.failure(errors=["Invalid quantity"])

        assert result.is_valid is False
        assert result.errors == ["Invalid quantity"]


class TestSymbolInfo:
    """Test SymbolInfo dataclass."""

    def test_default_symbol_info(self) -> None:
        """Test default symbol info creation."""
        info = create_default_symbol_info("BTCUSDT")

        assert info.symbol == "BTCUSDT"
        assert info.base_asset == "BTC"
        assert info.quote_asset == "USDT"
        assert info.is_trading is True

    def test_symbol_info_other_pairs(self) -> None:
        """Test symbol info for various trading pairs."""
        eth_info = create_default_symbol_info("ETHUSDT")
        assert eth_info.base_asset == "ETH"
        assert eth_info.quote_asset == "USDT"

        btc_pair = create_default_symbol_info("ETHBTC")
        assert btc_pair.base_asset == "ETH"
        assert btc_pair.quote_asset == "BTC"


class TestOrderValidator:
    """Test OrderValidator class."""

    @pytest.fixture
    def validator(self) -> OrderValidator:
        """Create validator with common symbol info."""
        validator = OrderValidator()
        validator.set_symbol_info(
            "BTCUSDT",
            SymbolInfo(
                symbol="BTCUSDT",
                base_asset="BTC",
                quote_asset="USDT",
                is_trading=True,
                min_quantity=Decimal("0.00001"),
                max_quantity=Decimal("1000"),
                step_size=Decimal("0.00001"),
                min_price=Decimal("0.01"),
                max_price=Decimal("1000000"),
                tick_size=Decimal("0.01"),
                min_notional=Decimal("10"),
            ),
        )
        return validator

    def test_valid_limit_buy_order(self, validator: OrderValidator) -> None:
        """Test validation of a valid limit buy order."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.001"),
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100"),  # Enough for 0.001 * 50000 + 5%
        )

        assert result.is_valid is True
        assert result.errors == []

    def test_valid_market_buy_order(self, validator: OrderValidator) -> None:
        """Test validation of a valid market buy order."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.001"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100"),
            current_price=Decimal("50000"),
        )

        assert result.is_valid is True

    def test_valid_sell_order(self, validator: OrderValidator) -> None:
        """Test validation of a valid sell order."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.001"),
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("0.01"),  # Enough BTC to sell
        )

        assert result.is_valid is True

    def test_insufficient_balance_buy(self, validator: OrderValidator) -> None:
        """Test validation fails for insufficient balance on buy."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),  # 1 BTC at 50000 = 50000 USDT needed
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("1000"),  # Only 1000 USDT
        )

        assert result.is_valid is False
        assert any("Insufficient balance" in e for e in result.errors)

    def test_insufficient_balance_sell(self, validator: OrderValidator) -> None:
        """Test validation fails for insufficient balance on sell."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),  # Selling 1 BTC
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("0.5"),  # Only 0.5 BTC
        )

        assert result.is_valid is False
        assert any("Insufficient balance" in e for e in result.errors)

    def test_balance_includes_safety_buffer(self, validator: OrderValidator) -> None:
        """Test that balance check includes 5% safety buffer."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),  # 0.01 BTC at 10000 = 100 USDT
            price=Decimal("10000"),
        )

        # Exactly 100 USDT should fail (need 105 with buffer)
        result = validator.validate_order(
            order,
            available_balance=Decimal("100"),
        )
        assert result.is_valid is False

        # 105 USDT should pass
        result = validator.validate_order(
            order,
            available_balance=Decimal("105"),
        )
        assert result.is_valid is True

    def test_zero_quantity(self, validator: OrderValidator) -> None:
        """Test validation fails for zero quantity."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0"),
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100000"),
        )

        assert result.is_valid is False
        assert any("positive" in e.lower() for e in result.errors)

    def test_negative_quantity(self, validator: OrderValidator) -> None:
        """Test validation fails for negative quantity."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("-0.1"),
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100000"),
        )

        assert result.is_valid is False
        assert any("positive" in e.lower() for e in result.errors)

    def test_quantity_below_minimum(self, validator: OrderValidator) -> None:
        """Test validation fails for quantity below minimum."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.000001"),  # Below 0.00001 min
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100000"),
        )

        assert result.is_valid is False
        assert any("below minimum" in e for e in result.errors)

    def test_quantity_above_maximum(self, validator: OrderValidator) -> None:
        """Test validation fails for quantity above maximum."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("10000"),  # Above 1000 max
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("999999999"),
        )

        assert result.is_valid is False
        assert any("exceeds maximum" in e for e in result.errors)

    def test_limit_order_requires_price(self, validator: OrderValidator) -> None:
        """Test limit order validation fails without price."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=None,  # Missing price
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100000"),
        )

        assert result.is_valid is False
        assert any("Price is required" in e for e in result.errors)

    def test_price_below_minimum(self, validator: OrderValidator) -> None:
        """Test validation fails for price below minimum."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("0.001"),  # Below 0.01 min
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100000"),
        )

        assert result.is_valid is False
        assert any("below minimum" in e for e in result.errors)

    def test_price_above_maximum(self, validator: OrderValidator) -> None:
        """Test validation fails for price above maximum."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("9999999"),  # Above 1000000 max
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("999999999"),
        )

        assert result.is_valid is False
        assert any("exceeds maximum" in e for e in result.errors)

    def test_notional_below_minimum(self, validator: OrderValidator) -> None:
        """Test validation fails for notional value below minimum."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.00001"),  # Very small quantity
            price=Decimal("100"),  # Notional = 0.001 < 10 min
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100000"),
        )

        assert result.is_valid is False
        assert any("notional" in e.lower() for e in result.errors)

    def test_symbol_not_trading(self) -> None:
        """Test validation fails for symbol not currently trading."""
        validator = OrderValidator()
        validator.set_symbol_info(
            "BTCUSDT",
            SymbolInfo(
                symbol="BTCUSDT",
                base_asset="BTC",
                quote_asset="USDT",
                is_trading=False,  # Not trading
            ),
        )

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100000"),
        )

        assert result.is_valid is False
        assert any("not currently trading" in e for e in result.errors)

    def test_unknown_symbol_passes_basic_validation(self) -> None:
        """Test that unknown symbols pass basic validation."""
        validator = OrderValidator()  # No symbol info loaded

        order = Order(
            symbol="UNKNOWNUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("100"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100"),  # Needs 1.05 with buffer
        )

        # Should pass basic validation (quantity > 0, etc.)
        # Symbol-specific constraints can't be checked
        assert result.is_valid is True

    def test_validate_cancel_active_order(self, validator: OrderValidator) -> None:
        """Test that active orders can be cancelled."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )

        result = validator.validate_cancel(order)
        assert result.is_valid is True

    def test_validate_cancel_filled_order_fails(
        self, validator: OrderValidator
    ) -> None:
        """Test that filled orders cannot be cancelled."""
        from src.trading.order_models import OrderStatus

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )
        order.status = OrderStatus.FILLED

        result = validator.validate_cancel(order)
        assert result.is_valid is False
        assert any("Cannot cancel" in e for e in result.errors)

    def test_market_order_requires_current_price_for_buy(
        self, validator: OrderValidator
    ) -> None:
        """Test market buy order requires current price for balance check."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.01"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("100000"),
            current_price=None,  # Missing price
        )

        assert result.is_valid is False
        assert any("Current price required" in e for e in result.errors)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_balance(self) -> None:
        """Test validation with zero balance."""
        validator = OrderValidator()

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("0"),
        )

        assert result.is_valid is False
        assert any(
            "zero" in e.lower() or "insufficient" in e.lower() for e in result.errors
        )

    def test_very_large_quantity(self) -> None:
        """Test handling of very large quantities."""
        validator = OrderValidator()
        validator.set_symbol_info("BTCUSDT", create_default_symbol_info("BTCUSDT"))

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("99999999999"),
            price=Decimal("50000"),
        )

        result = validator.validate_order(
            order,
            available_balance=Decimal("99999999999999999999"),
        )

        assert result.is_valid is False  # Should fail max quantity check

    def test_very_small_price_precision(self) -> None:
        """Test handling of high precision prices."""
        validator = OrderValidator()

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("50000.123456789012345"),  # High precision
        )

        # Should handle without error
        result = validator.validate_order(
            order,
            available_balance=Decimal("1000"),
        )

        # Basic validation should pass
        assert isinstance(result, ValidationResult)
