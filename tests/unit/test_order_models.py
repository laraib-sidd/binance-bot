"""
Helios Trading Bot - Order Models Unit Tests

Comprehensive unit tests for Order and Position dataclasses.
Tests cover Decimal precision, lifecycle management, and P&L calculations.
"""

from decimal import Decimal

from src.trading.order_models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    generate_order_id,
)


class TestOrderId:
    """Test order ID generation."""

    def test_generate_order_id_format(self) -> None:
        """Test order ID has expected format."""
        order_id = generate_order_id()

        assert order_id.startswith("HLO-")
        parts = order_id.split("-")
        assert len(parts) == 3
        # Timestamp part should be 14 chars (YYYYMMDDHHmmss)
        assert len(parts[1]) == 14
        # Unique part should be 12 hex chars
        assert len(parts[2]) == 12

    def test_generate_order_id_unique(self) -> None:
        """Test that generated order IDs are unique."""
        ids = [generate_order_id() for _ in range(100)]
        assert len(ids) == len(set(ids))


class TestOrder:
    """Test Order dataclass."""

    def test_create_limit_order(self) -> None:
        """Test creating a limit order."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.quantity == Decimal("0.1")
        assert order.price == Decimal("50000")
        assert order.status == OrderStatus.PENDING
        assert order.filled_quantity == Decimal("0")
        assert order.order_id.startswith("HLO-")

    def test_create_market_order(self) -> None:
        """Test creating a market order."""
        order = Order(
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.5"),
        )

        assert order.order_type == OrderType.MARKET
        assert order.price is None
        assert order.status == OrderStatus.PENDING

    def test_order_converts_to_decimal(self) -> None:
        """Test that numeric values are converted to Decimal."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,  # type: ignore
            price=50000,  # type: ignore
        )

        assert isinstance(order.quantity, Decimal)
        assert isinstance(order.price, Decimal)
        assert order.quantity == Decimal("0.1")
        assert order.price == Decimal("50000")

    def test_remaining_quantity(self) -> None:
        """Test remaining quantity calculation."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
        )

        assert order.remaining_quantity == Decimal("1.0")

        order.filled_quantity = Decimal("0.3")
        assert order.remaining_quantity == Decimal("0.7")

    def test_fill_percentage(self) -> None:
        """Test fill percentage calculation."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
        )

        assert order.fill_percentage == Decimal("0")

        order.filled_quantity = Decimal("0.5")
        assert order.fill_percentage == Decimal("50")

        order.filled_quantity = Decimal("1.0")
        assert order.fill_percentage == Decimal("100")

    def test_is_active(self) -> None:
        """Test is_active property."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
        )

        # PENDING is active
        assert order.is_active is True

        order.status = OrderStatus.SUBMITTED
        assert order.is_active is True

        order.status = OrderStatus.OPEN
        assert order.is_active is True

        order.status = OrderStatus.PARTIALLY_FILLED
        assert order.is_active is True

        # Terminal states are not active
        order.status = OrderStatus.FILLED
        assert order.is_active is False

        order.status = OrderStatus.CANCELLED
        assert order.is_active is False

    def test_is_complete(self) -> None:
        """Test is_complete property."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
        )

        assert order.is_complete is False

        order.status = OrderStatus.FILLED
        assert order.is_complete is True

        order.status = OrderStatus.CANCELLED
        assert order.is_complete is True

        order.status = OrderStatus.REJECTED
        assert order.is_complete is True

    def test_notional_value(self) -> None:
        """Test notional value calculation."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

        assert order.notional_value == Decimal("5000")

    def test_update_fill(self) -> None:
        """Test order fill updates."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
        )

        # First partial fill
        order.update_fill(
            filled_qty=Decimal("0.3"),
            fill_price=Decimal("49900"),
            commission=Decimal("0.0003"),
        )

        assert order.filled_quantity == Decimal("0.3")
        assert order.average_fill_price == Decimal("49900")
        assert order.commission == Decimal("0.0003")
        assert order.status == OrderStatus.PARTIALLY_FILLED

        # Second partial fill at different price
        order.update_fill(
            filled_qty=Decimal("0.7"),
            fill_price=Decimal("50100"),
            commission=Decimal("0.0007"),
        )

        assert order.filled_quantity == Decimal("1.0")
        assert order.commission == Decimal("0.001")
        assert order.status == OrderStatus.FILLED

        # Check weighted average price
        # (0.3 * 49900 + 0.7 * 50100) / 1.0 = 50040
        assert order.average_fill_price == Decimal("50040")

    def test_mark_submitted(self) -> None:
        """Test marking order as submitted."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
        )

        order.mark_submitted("BINANCE123456")

        assert order.status == OrderStatus.SUBMITTED
        assert order.exchange_order_id == "BINANCE123456"

    def test_mark_cancelled(self) -> None:
        """Test marking order as cancelled."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
        )

        order.mark_cancelled()
        assert order.status == OrderStatus.CANCELLED

    def test_mark_rejected(self) -> None:
        """Test marking order as rejected with reason."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=Decimal("50000"),
        )

        order.mark_rejected("Insufficient balance")

        assert order.status == OrderStatus.REJECTED
        assert "Insufficient balance" in str(order.notes)

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )

        order_dict = order.to_dict()

        assert order_dict["symbol"] == "BTCUSDT"
        assert order_dict["side"] == "BUY"
        assert order_dict["order_type"] == "LIMIT"
        assert order_dict["quantity"] == "0.1"
        assert order_dict["price"] == "50000"
        assert order_dict["status"] == "PENDING"
        assert "created_at" in order_dict


class TestPosition:
    """Test Position dataclass."""

    def test_create_long_position(self) -> None:
        """Test creating a long position."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.5"),
            entry_price=Decimal("50000"),
        )

        assert position.symbol == "BTCUSDT"
        assert position.side == PositionSide.LONG
        assert position.quantity == Decimal("0.5")
        assert position.entry_price == Decimal("50000")
        assert position.current_price == Decimal("50000")  # Initialized to entry

    def test_is_flat(self) -> None:
        """Test is_flat property."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.5"),
            entry_price=Decimal("50000"),
        )

        assert position.is_flat is False

        position.quantity = Decimal("0")
        assert position.is_flat is True

        position.quantity = Decimal("0.1")
        position.side = PositionSide.FLAT
        assert position.is_flat is True

    def test_notional_value(self) -> None:
        """Test notional value calculation."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.5"),
            entry_price=Decimal("50000"),
        )

        position.current_price = Decimal("52000")

        assert position.notional_value == Decimal("26000")  # 0.5 * 52000
        assert position.entry_notional_value == Decimal("25000")  # 0.5 * 50000

    def test_unrealized_pnl_long_profit(self) -> None:
        """Test unrealized P&L for profitable long position."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.5"),
            entry_price=Decimal("50000"),
        )

        position.update_price(Decimal("52000"))

        # (52000 - 50000) * 0.5 = 1000
        assert position.unrealized_pnl == Decimal("1000")
        assert position.unrealized_pnl_percent == Decimal("4")  # 1000/25000 * 100

    def test_unrealized_pnl_long_loss(self) -> None:
        """Test unrealized P&L for losing long position."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.5"),
            entry_price=Decimal("50000"),
        )

        position.update_price(Decimal("48000"))

        # (48000 - 50000) * 0.5 = -1000
        assert position.unrealized_pnl == Decimal("-1000")

    def test_unrealized_pnl_flat_position(self) -> None:
        """Test unrealized P&L for flat position is zero."""
        position = Position.create_flat("BTCUSDT")

        assert position.unrealized_pnl == Decimal("0")

    def test_add_to_position(self) -> None:
        """Test adding to an existing position."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.5"),
            entry_price=Decimal("50000"),
        )

        # Add 0.5 more at 52000
        position.add_to_position(
            quantity=Decimal("0.5"),
            price=Decimal("52000"),
            commission=Decimal("1.0"),
        )

        assert position.quantity == Decimal("1.0")
        # Weighted average: (0.5 * 50000 + 0.5 * 52000) / 1.0 = 51000
        assert position.entry_price == Decimal("51000")
        assert position.total_commission == Decimal("1.0")

    def test_reduce_position(self) -> None:
        """Test reducing a position and realizing P&L."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("1.0"),
            entry_price=Decimal("50000"),
        )

        # Reduce by selling 0.5 at 52000
        realized = position.reduce_position(
            quantity=Decimal("0.5"),
            price=Decimal("52000"),
            commission=Decimal("0.5"),
        )

        # (52000 - 50000) * 0.5 = 1000
        assert realized == Decimal("1000")
        assert position.realized_pnl == Decimal("1000")
        assert position.quantity == Decimal("0.5")
        assert position.total_commission == Decimal("0.5")

    def test_reduce_position_fully_closes(self) -> None:
        """Test that fully reducing a position marks it as flat."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("1.0"),
            entry_price=Decimal("50000"),
        )

        position.reduce_position(
            quantity=Decimal("1.0"),
            price=Decimal("52000"),
        )

        assert position.is_flat is True
        assert position.side == PositionSide.FLAT
        assert position.quantity == Decimal("0")

    def test_total_pnl(self) -> None:
        """Test total P&L calculation (realized + unrealized)."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("1.0"),
            entry_price=Decimal("50000"),
        )

        # Partially close with profit
        position.reduce_position(
            quantity=Decimal("0.5"),
            price=Decimal("52000"),
        )

        # Remaining position also in profit
        position.update_price(Decimal("53000"))

        # Realized: (52000 - 50000) * 0.5 = 1000
        # Unrealized: (53000 - 50000) * 0.5 = 1500
        # Total: 2500
        assert position.realized_pnl == Decimal("1000")
        assert position.unrealized_pnl == Decimal("1500")
        assert position.total_pnl == Decimal("2500")

    def test_net_pnl(self) -> None:
        """Test net P&L after commissions."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("1.0"),
            entry_price=Decimal("50000"),
            total_commission=Decimal("10"),
        )

        position.update_price(Decimal("52000"))

        # Unrealized: 2000
        # Net: 2000 - 10 = 1990
        assert position.net_pnl == Decimal("1990")

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.5"),
            entry_price=Decimal("50000"),
        )
        position.update_price(Decimal("52000"))

        pos_dict = position.to_dict()

        assert pos_dict["symbol"] == "BTCUSDT"
        assert pos_dict["side"] == "LONG"
        assert pos_dict["quantity"] == "0.5"
        assert pos_dict["entry_price"] == "50000"
        assert pos_dict["current_price"] == "52000"
        # Decimal string representation may include trailing zeros
        assert Decimal(pos_dict["unrealized_pnl"]) == Decimal("1000")
        assert "opened_at" in pos_dict

    def test_create_flat(self) -> None:
        """Test creating a flat position."""
        position = Position.create_flat("BTCUSDT")

        assert position.symbol == "BTCUSDT"
        assert position.side == PositionSide.FLAT
        assert position.quantity == Decimal("0")
        assert position.is_flat is True


class TestDecimalPrecision:
    """Test Decimal precision is maintained per rule 010."""

    def test_order_precision_maintained(self) -> None:
        """Test that Decimal precision is not lost in calculations."""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.00123456"),
            price=Decimal("50000.12345678"),
        )

        assert order.quantity == Decimal("0.00123456")
        assert order.price == Decimal("50000.12345678")

        # Notional should maintain precision
        expected_notional = Decimal("0.00123456") * Decimal("50000.12345678")
        assert order.notional_value == expected_notional

    def test_position_precision_maintained(self) -> None:
        """Test that position P&L maintains Decimal precision."""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.00123456"),
            entry_price=Decimal("50000.12345678"),
        )

        position.update_price(Decimal("50100.98765432"))

        # Verify precision is maintained
        assert isinstance(position.unrealized_pnl, Decimal)
        assert isinstance(position.notional_value, Decimal)
