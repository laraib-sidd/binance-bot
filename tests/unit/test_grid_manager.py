"""
Helios Trading Bot - Grid Manager Unit Tests

Tests for GridManager with mocked OrderManager dependencies.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.grid_manager import (
    GridDeploymentError,
    GridManager,
    GridSessionNotFoundError,
)
from src.trading.grid_models import (
    GridConfig,
    GridLevelStatus,
    GridStatus,
)
from src.trading.order_models import Order, OrderSide, OrderStatus, OrderType


@pytest.fixture
def mock_order_manager() -> MagicMock:
    """Create a mock OrderManager."""
    manager = MagicMock()
    manager.place_order = AsyncMock()
    manager.cancel_order = AsyncMock()
    return manager


@pytest.fixture
def grid_config() -> GridConfig:
    """Create a test grid configuration."""
    return GridConfig(
        symbol="BTCUSDT",
        grid_levels=4,
        range_multiplier=Decimal("2.0"),
        risk_per_session=Decimal("0.01"),
    )


@pytest.fixture
def grid_manager(mock_order_manager: MagicMock, grid_config: GridConfig) -> GridManager:
    """Create a GridManager with mocked dependencies."""
    return GridManager(
        order_manager=mock_order_manager,
        default_config=grid_config,
    )


class TestGridManagerCreation:
    """Tests for GridManager session creation."""

    @pytest.mark.asyncio
    async def test_create_session(
        self, grid_manager: GridManager, grid_config: GridConfig
    ) -> None:
        """Test creating a grid session."""
        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        assert session.symbol == "BTCUSDT"
        assert session.status == GridStatus.PENDING
        assert len(session.levels) == 4  # From grid_config

    @pytest.mark.asyncio
    async def test_create_session_with_custom_config(
        self, grid_manager: GridManager
    ) -> None:
        """Test creating session with custom config."""
        custom_config = GridConfig(
            symbol="ETHUSDT",
            grid_levels=6,
        )

        session = await grid_manager.create_session(
            symbol="ETHUSDT",
            current_price=Decimal("2000"),
            atr_value=Decimal("50"),
            available_capital=Decimal("5000"),
            config=custom_config,
        )

        assert session.symbol == "ETHUSDT"
        assert len(session.levels) == 6

    @pytest.mark.asyncio
    async def test_session_stored_after_creation(
        self, grid_manager: GridManager
    ) -> None:
        """Test session is stored in manager after creation."""
        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        retrieved = grid_manager.get_session(session.session_id)
        assert retrieved.session_id == session.session_id


class TestGridManagerDeployment:
    """Tests for grid deployment."""

    @pytest.mark.asyncio
    async def test_deploy_session_places_buy_orders(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test deployment places buy orders for all buy levels."""
        # Setup mock order response
        mock_order_manager.place_order.return_value = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("49000"),
            status=OrderStatus.OPEN,
            exchange_order_id="EX123",
        )

        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        deployed = await grid_manager.deploy_session(session.session_id)

        assert deployed.status == GridStatus.ACTIVE
        assert deployed.started_at is not None
        # Should have called place_order for each buy level
        buy_level_count = len(session.buy_levels)
        assert mock_order_manager.place_order.call_count == buy_level_count

    @pytest.mark.asyncio
    async def test_deploy_session_updates_level_status(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test deployment updates level status to OPEN."""
        mock_order_manager.place_order.return_value = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("49000"),
            status=OrderStatus.OPEN,
            exchange_order_id="EX123",
        )

        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        await grid_manager.deploy_session(session.session_id)

        for level in session.buy_levels:
            assert level.status == GridLevelStatus.OPEN
            assert level.order_id is not None

    @pytest.mark.asyncio
    async def test_deploy_non_pending_session_fails(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test deploying an already active session fails."""
        mock_order_manager.place_order.return_value = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("49000"),
        )

        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )
        await grid_manager.deploy_session(session.session_id)

        with pytest.raises(GridDeploymentError) as exc_info:
            await grid_manager.deploy_session(session.session_id)

        assert "not pending" in str(exc_info.value).lower()


class TestGridManagerFillHandling:
    """Tests for order fill handling."""

    @pytest.mark.asyncio
    async def test_handle_buy_fill_places_sell(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test handling buy fill places corresponding sell order."""
        # Create unique orders for each level
        order_counter = [0]

        def create_unique_order(*args, **kwargs):
            order_counter[0] += 1
            return Order(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("0.01"),
                price=Decimal("49000"),
                status=OrderStatus.OPEN,
                exchange_order_id=f"EX{order_counter[0]}",
            )

        mock_order_manager.place_order.side_effect = create_unique_order

        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )
        await grid_manager.deploy_session(session.session_id)

        # Get the first buy level and its tracked order_id
        buy_level = session.buy_levels[0]
        tracked_order_id = buy_level.order_id

        # Setup mock for sell order
        sell_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("49500"),
            status=OrderStatus.OPEN,
            exchange_order_id="EX_SELL",
        )
        mock_order_manager.place_order.side_effect = None
        mock_order_manager.place_order.return_value = sell_order

        # Simulate buy fill
        new_order = await grid_manager.handle_order_fill(
            order_id=tracked_order_id,
            fill_price=Decimal("49000"),
            fill_quantity=Decimal("0.01"),
        )

        # Should have placed sell order
        assert new_order is not None

        # Level should be marked as buy filled
        assert buy_level.status == GridLevelStatus.BUY_FILLED
        assert buy_level.buy_fill_price == Decimal("49000")

    @pytest.mark.asyncio
    async def test_handle_sell_fill_records_pnl(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test handling sell fill records P&L correctly."""
        # Create unique orders for each level
        order_counter = [0]

        def create_unique_order(*args, **kwargs):
            order_counter[0] += 1
            return Order(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("0.01"),
                price=Decimal("49000"),
                status=OrderStatus.OPEN,
                exchange_order_id=f"EX{order_counter[0]}",
            )

        mock_order_manager.place_order.side_effect = create_unique_order

        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )
        await grid_manager.deploy_session(session.session_id)

        # Get the first buy level
        level = session.buy_levels[0]
        tracked_order_id = level.order_id

        # Manually set level to buy_filled state (simulating a fill)
        level.status = GridLevelStatus.BUY_FILLED
        level.buy_fill_price = Decimal("49000")
        level.quantity = Decimal("0.01")

        # Handle sell fill using the tracked order_id
        await grid_manager.handle_order_fill(
            order_id=tracked_order_id,
            fill_price=Decimal("50000"),
            fill_quantity=Decimal("0.01"),
            commission=Decimal("0.5"),
        )

        # Level should be complete
        assert level.status == GridLevelStatus.SELL_FILLED
        # P&L = (50000 - 49000) * 0.01 - 0.5 = 10 - 0.5 = 9.5
        assert level.realized_pnl == Decimal("9.5")
        assert session.total_trades == 1
        assert session.winning_trades == 1


class TestGridManagerSessionControl:
    """Tests for session control and monitoring."""

    @pytest.mark.asyncio
    async def test_stop_session_cancels_orders(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test stopping session cancels all open orders."""
        mock_order_manager.place_order.return_value = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("49000"),
            status=OrderStatus.OPEN,
        )

        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )
        await grid_manager.deploy_session(session.session_id)

        stopped = await grid_manager.stop_session(session.session_id, "Test stop")

        assert stopped.status == GridStatus.STOPPED
        assert stopped.ended_at is not None
        # Should have cancelled all buy orders
        assert mock_order_manager.cancel_order.call_count == len(session.buy_levels)

    @pytest.mark.asyncio
    async def test_check_session_conditions_stop_loss(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test session is stopped when price hits stop-loss."""
        mock_order_manager.place_order.return_value = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("49000"),
        )

        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )
        await grid_manager.deploy_session(session.session_id)

        # Price drops below stop-loss
        result = await grid_manager.check_session_conditions(
            session_id=session.session_id,
            current_price=session.stop_loss_price - Decimal("100"),
        )

        assert "stop_loss" in result["actions"]
        assert result["status"] == GridStatus.STOPPED.value

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, grid_manager: GridManager) -> None:
        """Test getting non-existent session raises error."""
        with pytest.raises(GridSessionNotFoundError):
            grid_manager.get_session("nonexistent-id")

    @pytest.mark.asyncio
    async def test_get_session_summary(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test getting session summary."""
        mock_order_manager.place_order.return_value = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("49000"),
        )

        session = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )

        summary = grid_manager.get_session_summary(session.session_id)

        assert summary["symbol"] == "BTCUSDT"
        assert summary["status"] == "pending"
        assert "entry_price" in summary
        assert "grid_range" in summary

    @pytest.mark.asyncio
    async def test_active_sessions_property(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test active_sessions returns only active sessions."""
        mock_order_manager.place_order.return_value = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("49000"),
        )

        # Create and deploy one session
        session1 = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )
        await grid_manager.deploy_session(session1.session_id)

        # Create pending session
        await grid_manager.create_session(
            symbol="ETHUSDT",
            current_price=Decimal("2000"),
            atr_value=Decimal("50"),
            available_capital=Decimal("5000"),
        )

        active = grid_manager.active_sessions

        assert len(active) == 1
        assert active[0].session_id == session1.session_id

    @pytest.mark.asyncio
    async def test_stop_all_sessions(
        self, grid_manager: GridManager, mock_order_manager: MagicMock
    ) -> None:
        """Test stopping all active sessions."""
        mock_order_manager.place_order.return_value = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("49000"),
        )

        # Create and deploy two sessions
        session1 = await grid_manager.create_session(
            symbol="BTCUSDT",
            current_price=Decimal("50000"),
            atr_value=Decimal("1000"),
            available_capital=Decimal("10000"),
        )
        await grid_manager.deploy_session(session1.session_id)

        session2 = await grid_manager.create_session(
            symbol="ETHUSDT",
            current_price=Decimal("2000"),
            atr_value=Decimal("50"),
            available_capital=Decimal("5000"),
        )
        await grid_manager.deploy_session(session2.session_id)

        stopped_count = await grid_manager.stop_all_sessions("Emergency stop")

        assert stopped_count == 2
        assert len(grid_manager.active_sessions) == 0
