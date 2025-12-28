"""
Helios Trading Bot - Position Tracker Unit Tests

Unit tests for PositionTracker covering position lifecycle,
P&L calculations, and trade history.
"""

from decimal import Decimal

from src.trading.order_models import Order, OrderSide, OrderType
from src.trading.position_tracker import PositionSide, PositionTracker


class TestPositionTrackerBasics:
    """Test basic PositionTracker functionality."""

    def test_initial_state(self) -> None:
        """Test tracker starts with empty state."""
        tracker = PositionTracker()

        assert len(tracker.positions) == 0
        assert len(tracker.open_positions) == 0
        assert tracker.total_realized_pnl == Decimal("0")
        assert tracker.total_unrealized_pnl == Decimal("0")

    def test_get_position_creates_flat(self) -> None:
        """Test getting non-existent position creates flat position."""
        tracker = PositionTracker()

        position = tracker.get_position("BTCUSDT")

        assert position.symbol == "BTCUSDT"
        assert position.is_flat is True
        assert position.side == PositionSide.FLAT

    def test_update_price(self) -> None:
        """Test updating price for a symbol."""
        tracker = PositionTracker()

        # Create position first
        tracker._positions["BTCUSDT"] = tracker.get_position("BTCUSDT")
        tracker._positions["BTCUSDT"].side = PositionSide.LONG
        tracker._positions["BTCUSDT"].quantity = Decimal("1")
        tracker._positions["BTCUSDT"].entry_price = Decimal("50000")

        tracker.update_price("BTCUSDT", Decimal("52000"))

        assert tracker._positions["BTCUSDT"].current_price == Decimal("52000")

    def test_update_prices_batch(self) -> None:
        """Test batch price update."""
        tracker = PositionTracker()

        # Create positions
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            tracker._positions[symbol] = tracker.get_position(symbol)
            tracker._positions[symbol].side = PositionSide.LONG
            tracker._positions[symbol].quantity = Decimal("1")
            tracker._positions[symbol].entry_price = Decimal("1000")

        tracker.update_prices(
            {
                "BTCUSDT": Decimal("1100"),
                "ETHUSDT": Decimal("1200"),
            }
        )

        assert tracker._positions["BTCUSDT"].current_price == Decimal("1100")
        assert tracker._positions["ETHUSDT"].current_price == Decimal("1200")


class TestProcessFill:
    """Test order fill processing."""

    def test_open_long_position(self) -> None:
        """Test opening a long position from a buy order."""
        tracker = PositionTracker()

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.5"),
        )

        realized = tracker.process_fill(
            order=order,
            fill_quantity=Decimal("0.5"),
            fill_price=Decimal("50000"),
            commission=Decimal("0.5"),
        )

        position = tracker.get_position("BTCUSDT")

        assert realized == Decimal("0")  # No realized P&L on open
        assert position.side == PositionSide.LONG
        assert position.quantity == Decimal("0.5")
        assert position.entry_price == Decimal("50000")
        assert tracker.total_commission == Decimal("0.5")

    def test_add_to_long_position(self) -> None:
        """Test adding to an existing long position."""
        tracker = PositionTracker()

        # Open initial position
        order1 = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.5"),
        )
        tracker.process_fill(order1, Decimal("0.5"), Decimal("50000"))

        # Add more
        order2 = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.5"),
        )
        tracker.process_fill(order2, Decimal("0.5"), Decimal("52000"))

        position = tracker.get_position("BTCUSDT")

        assert position.quantity == Decimal("1.0")
        # Weighted average: (0.5 * 50000 + 0.5 * 52000) / 1.0 = 51000
        assert position.entry_price == Decimal("51000")

    def test_reduce_long_position_profit(self) -> None:
        """Test reducing a long position for profit."""
        tracker = PositionTracker()

        # Open position
        buy_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(buy_order, Decimal("1.0"), Decimal("50000"))

        # Sell half at profit
        sell_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.5"),
        )
        realized = tracker.process_fill(sell_order, Decimal("0.5"), Decimal("52000"))

        position = tracker.get_position("BTCUSDT")

        # (52000 - 50000) * 0.5 = 1000
        assert realized == Decimal("1000")
        assert position.quantity == Decimal("0.5")
        assert tracker.total_realized_pnl == Decimal("1000")

    def test_close_long_position(self) -> None:
        """Test fully closing a long position."""
        tracker = PositionTracker()

        # Open position
        buy_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(buy_order, Decimal("1.0"), Decimal("50000"))

        # Sell all
        sell_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        realized = tracker.process_fill(sell_order, Decimal("1.0"), Decimal("55000"))

        position = tracker.get_position("BTCUSDT")

        # (55000 - 50000) * 1.0 = 5000
        assert realized == Decimal("5000")
        assert position.is_flat is True

    def test_close_long_position_loss(self) -> None:
        """Test closing a long position for a loss."""
        tracker = PositionTracker()

        # Open position
        buy_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(buy_order, Decimal("1.0"), Decimal("50000"))

        # Sell at loss
        sell_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        realized = tracker.process_fill(sell_order, Decimal("1.0"), Decimal("48000"))

        # (48000 - 50000) * 1.0 = -2000
        assert realized == Decimal("-2000")
        assert tracker.total_realized_pnl == Decimal("-2000")


class TestUnrealizedPnL:
    """Test unrealized P&L calculations."""

    def test_unrealized_pnl_profit(self) -> None:
        """Test unrealized P&L when position is profitable."""
        tracker = PositionTracker()

        # Open position
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(order, Decimal("1.0"), Decimal("50000"))

        # Update price to higher
        tracker.update_price("BTCUSDT", Decimal("52000"))

        # (52000 - 50000) * 1.0 = 2000
        assert tracker.total_unrealized_pnl == Decimal("2000")

    def test_unrealized_pnl_loss(self) -> None:
        """Test unrealized P&L when position is losing."""
        tracker = PositionTracker()

        # Open position
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(order, Decimal("1.0"), Decimal("50000"))

        # Update price to lower
        tracker.update_price("BTCUSDT", Decimal("48000"))

        # (48000 - 50000) * 1.0 = -2000
        assert tracker.total_unrealized_pnl == Decimal("-2000")

    def test_total_pnl_combines_realized_and_unrealized(self) -> None:
        """Test total P&L combines realized and unrealized."""
        tracker = PositionTracker()

        # Open position
        buy_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("2.0"),
        )
        tracker.process_fill(buy_order, Decimal("2.0"), Decimal("50000"))

        # Sell half at profit
        sell_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(sell_order, Decimal("1.0"), Decimal("52000"))

        # Remaining position moves up more
        tracker.update_price("BTCUSDT", Decimal("54000"))

        # Realized: (52000 - 50000) * 1.0 = 2000
        # Unrealized: (54000 - 50000) * 1.0 = 4000
        # Total: 6000
        assert tracker.total_realized_pnl == Decimal("2000")
        assert tracker.total_unrealized_pnl == Decimal("4000")
        assert tracker.total_pnl == Decimal("6000")


class TestPortfolioSummary:
    """Test portfolio-level reporting."""

    def test_portfolio_summary_empty(self) -> None:
        """Test portfolio summary with no positions."""
        tracker = PositionTracker()

        summary = tracker.get_portfolio_summary()

        assert summary["open_positions"] == 0
        assert summary["positions"] == []
        assert Decimal(summary["total_pnl"]) == Decimal("0")

    def test_portfolio_summary_with_positions(self) -> None:
        """Test portfolio summary with multiple positions."""
        tracker = PositionTracker()

        # Open BTC position
        btc_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(btc_order, Decimal("1.0"), Decimal("50000"))

        # Open ETH position
        eth_order = Order(
            symbol="ETHUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10.0"),
        )
        tracker.process_fill(eth_order, Decimal("10.0"), Decimal("3000"))

        summary = tracker.get_portfolio_summary()

        assert summary["open_positions"] == 2
        assert len(summary["positions"]) == 2

    def test_net_pnl_after_commission(self) -> None:
        """Test net P&L subtracts commissions."""
        tracker = PositionTracker()

        # Open position with commission
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(order, Decimal("1.0"), Decimal("50000"), Decimal("50"))

        # Update price
        tracker.update_price("BTCUSDT", Decimal("52000"))

        # Unrealized: 2000, Commission: 50, Net: 1950
        assert tracker.total_unrealized_pnl == Decimal("2000")
        assert tracker.total_commission == Decimal("50")
        assert tracker.net_pnl == Decimal("1950")


class TestTradeHistory:
    """Test trade history tracking."""

    def test_trade_history_records_opens(self) -> None:
        """Test trade history records position opens."""
        tracker = PositionTracker()

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(order, Decimal("1.0"), Decimal("50000"))

        history = tracker.get_trade_history()

        assert len(history) == 1
        assert history[0]["action"] == "OPEN"
        assert history[0]["symbol"] == "BTCUSDT"

    def test_trade_history_records_closes(self) -> None:
        """Test trade history records position closes."""
        tracker = PositionTracker()

        # Open
        buy_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(buy_order, Decimal("1.0"), Decimal("50000"))

        # Close
        sell_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(sell_order, Decimal("1.0"), Decimal("52000"))

        history = tracker.get_trade_history()

        assert len(history) == 2
        # History is returned with most recent first
        assert history[0]["action"] == "CLOSE"
        assert "realized_pnl" in history[0]

    def test_trade_history_filter_by_symbol(self) -> None:
        """Test filtering trade history by symbol."""
        tracker = PositionTracker()

        # Trade in BTC
        btc_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(btc_order, Decimal("1.0"), Decimal("50000"))

        # Trade in ETH
        eth_order = Order(
            symbol="ETHUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("10.0"),
        )
        tracker.process_fill(eth_order, Decimal("10.0"), Decimal("3000"))

        btc_history = tracker.get_trade_history(symbol="BTCUSDT")
        eth_history = tracker.get_trade_history(symbol="ETHUSDT")

        assert len(btc_history) == 1
        assert len(eth_history) == 1


class TestTrackerPersistence:
    """Test tracker serialization and deserialization."""

    def test_to_dict(self) -> None:
        """Test serializing tracker to dictionary."""
        tracker = PositionTracker()

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(order, Decimal("1.0"), Decimal("50000"), Decimal("10"))

        data = tracker.to_dict()

        assert "positions" in data
        assert "total_realized_pnl" in data
        assert "total_commission" in data
        assert "trade_history" in data
        assert "BTCUSDT" in data["positions"]

    def test_from_dict(self) -> None:
        """Test deserializing tracker from dictionary."""
        original = PositionTracker()

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        original.process_fill(order, Decimal("1.0"), Decimal("50000"), Decimal("10"))

        data = original.to_dict()
        restored = PositionTracker.from_dict(data)

        assert len(restored.positions) == len(original.positions)
        assert restored.total_commission == original.total_commission

    def test_reset(self) -> None:
        """Test resetting tracker state."""
        tracker = PositionTracker()

        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(order, Decimal("1.0"), Decimal("50000"))

        tracker.reset()

        assert len(tracker.positions) == 0
        assert tracker.total_realized_pnl == Decimal("0")
        assert len(tracker.get_trade_history()) == 0


class TestClosePosition:
    """Test direct position closing."""

    def test_close_position(self) -> None:
        """Test closing a position directly."""
        tracker = PositionTracker()

        # Open position
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        tracker.process_fill(order, Decimal("1.0"), Decimal("50000"))

        # Close at profit
        realized = tracker.close_position("BTCUSDT", Decimal("55000"))

        assert realized == Decimal("5000")
        assert tracker.get_position("BTCUSDT").is_flat

    def test_close_flat_position(self) -> None:
        """Test closing an already flat position returns zero."""
        tracker = PositionTracker()

        realized = tracker.close_position("BTCUSDT", Decimal("50000"))

        assert realized == Decimal("0")
