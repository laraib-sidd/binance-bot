"""
Helios Trading Bot - Order Manager Unit Tests

Unit tests for OrderManager with mocked BinanceClient.
Tests cover order placement, cancellation, and status tracking.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.models import (
    AccountInfo,
    ExchangeInfo,
    SymbolInfo as APISymbolInfo,
    TickerData,
)
from src.core.config import TradingConfig
from src.trading.exceptions import (
    OrderExecutionError,
    OrderNotFoundError,
    OrderValidationError,
)
from src.trading.order_manager import OrderManager
from src.trading.order_models import OrderSide, OrderStatus, OrderType
from src.trading.order_validator import SymbolInfo


def create_mock_account_info(balances: dict[str, str]) -> AccountInfo:
    """Helper to create a mock AccountInfo dataclass."""
    return AccountInfo(
        account_type="SPOT",
        can_trade=True,
        can_withdraw=True,
        can_deposit=True,
        update_time=datetime.now(timezone.utc),
        total_wallet_balance=Decimal("10000"),
        total_unrealized_pnl=Decimal("0"),
        balances={k: Decimal(v) for k, v in balances.items()},
    )


def create_mock_ticker_data(symbol: str, price: str) -> TickerData:
    """Helper to create a mock TickerData dataclass."""
    return TickerData(
        symbol=symbol,
        price=Decimal(price),
        bid_price=Decimal(price),
        ask_price=Decimal(price),
        volume_24h=Decimal("1000000"),
        price_change_24h=Decimal("100"),
        price_change_percent_24h=Decimal("0.2"),
        high_24h=Decimal(price),
        low_24h=Decimal(price),
        timestamp=datetime.now(timezone.utc),
    )


def create_mock_exchange_info(symbols: list[dict]) -> ExchangeInfo:
    """Helper to create a mock ExchangeInfo dataclass."""
    api_symbols = {}
    for sym_data in symbols:
        api_sym = APISymbolInfo(
            symbol=sym_data["symbol"],
            status=sym_data.get("status", "TRADING"),
            base_asset=sym_data["baseAsset"],
            quote_asset=sym_data["quoteAsset"],
            base_precision=8,
            quote_precision=8,
            min_qty=Decimal(sym_data.get("minQty", "0.00001")),
            max_qty=Decimal(sym_data.get("maxQty", "1000")),
            step_size=Decimal(sym_data.get("stepSize", "0.00001")),
            min_price=Decimal(sym_data.get("minPrice", "0.01")),
            max_price=Decimal(sym_data.get("maxPrice", "1000000")),
            tick_size=Decimal(sym_data.get("tickSize", "0.01")),
            min_notional=Decimal(sym_data.get("minNotional", "10")),
        )
        api_symbols[api_sym.symbol] = api_sym
    return ExchangeInfo(
        server_time=datetime.now(timezone.utc),
        symbols=api_symbols,
    )


@pytest.fixture
def mock_config() -> TradingConfig:
    """Create a mock trading config."""
    return TradingConfig(
        binance_api_key="test_api_key",
        binance_api_secret="test_api_secret",
        binance_testnet=True,
        default_trading_pairs=["BTCUSDT", "ETHUSDT"],
        validate_on_init=False,
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock BinanceClient."""
    client = MagicMock()
    client._make_request = AsyncMock()
    client.get_exchange_info = AsyncMock()
    client.get_account_info = AsyncMock()
    client.get_ticker_price = AsyncMock()
    return client


@pytest.fixture
def order_manager(mock_client: MagicMock, mock_config: TradingConfig) -> OrderManager:
    """Create an OrderManager with mocked dependencies."""
    manager = OrderManager(client=mock_client, config=mock_config)

    # Pre-populate symbol info
    manager._validator.set_symbol_info(
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
    manager._symbol_info["BTCUSDT"] = manager._validator.get_symbol_info("BTCUSDT")
    manager._initialized = True

    return manager


class TestOrderManagerInitialization:
    """Test OrderManager initialization."""

    @pytest.mark.asyncio
    async def test_initialize_loads_symbol_info(
        self,
        mock_client: MagicMock,
        mock_config: TradingConfig,
    ) -> None:
        """Test that initialization loads symbol info from exchange."""
        mock_client.get_exchange_info.return_value = create_mock_exchange_info(
            [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "minQty": "0.00001",
                    "maxQty": "1000",
                    "stepSize": "0.00001",
                    "minPrice": "0.01",
                    "maxPrice": "1000000",
                    "tickSize": "0.01",
                    "minNotional": "10",
                }
            ]
        )

        manager = OrderManager(client=mock_client, config=mock_config)
        await manager.initialize()

        assert manager._initialized is True
        assert "BTCUSDT" in manager._symbol_info


class TestOrderPlacement:
    """Test order placement functionality."""

    @pytest.mark.asyncio
    async def test_place_limit_buy_order_success(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test successful limit buy order placement."""
        # Mock account balance (USDT for buying BTC)
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"USDT": "10000"}
        )

        # Mock order submission response
        mock_client._make_request.return_value = {
            "orderId": "12345",
            "status": "NEW",
            "executedQty": "0",
        }

        order = await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.01"),
            order_type=OrderType.LIMIT,
            price=Decimal("50000"),
        )

        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.quantity == Decimal("0.01")
        assert order.status == OrderStatus.OPEN
        assert order.exchange_order_id == "12345"

    @pytest.mark.asyncio
    async def test_place_market_sell_order_success(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test successful market sell order placement."""
        # Mock account balance (BTC for selling)
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"BTC": "1.0"}
        )

        # Mock current price
        mock_client.get_ticker_price.return_value = create_mock_ticker_data(
            "BTCUSDT", "50000"
        )

        # Mock order submission - immediately filled
        mock_client._make_request.return_value = {
            "orderId": "12346",
            "status": "FILLED",
            "executedQty": "0.01",
            "cummulativeQuoteQty": "500",
        }

        order = await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            quantity=Decimal("0.01"),
            order_type=OrderType.MARKET,
        )

        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == Decimal("0.01")

    @pytest.mark.asyncio
    async def test_place_order_insufficient_balance(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test order rejection due to insufficient balance."""
        # Mock low balance
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"USDT": "10"}
        )

        with pytest.raises(OrderValidationError) as exc_info:
            await order_manager.place_order(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal("1.0"),  # 1 BTC @ 50000 = 50000 USDT
                order_type=OrderType.LIMIT,
                price=Decimal("50000"),
            )

        assert "Insufficient balance" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_place_order_exchange_error(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test order failure due to exchange error."""
        # Mock sufficient balance
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"USDT": "100000"}
        )

        # Mock exchange error
        mock_client._make_request.side_effect = Exception("Exchange error")

        with pytest.raises(OrderExecutionError):
            await order_manager.place_order(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                quantity=Decimal("0.01"),
                order_type=OrderType.LIMIT,
                price=Decimal("50000"),
            )


class TestOrderCancellation:
    """Test order cancellation functionality."""

    @pytest.mark.asyncio
    async def test_cancel_open_order_success(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test successful order cancellation."""
        # Place an order first
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"USDT": "100000"}
        )
        mock_client._make_request.return_value = {
            "orderId": "12345",
            "status": "NEW",
        }

        order = await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.01"),
            order_type=OrderType.LIMIT,
            price=Decimal("50000"),
        )

        # Cancel the order
        mock_client._make_request.return_value = {"status": "CANCELED"}

        cancelled_order = await order_manager.cancel_order(order.order_id)

        assert cancelled_order.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order(
        self,
        order_manager: OrderManager,
    ) -> None:
        """Test cancellation of non-existent order."""
        with pytest.raises(OrderNotFoundError):
            await order_manager.cancel_order("nonexistent-order-id")


class TestOrderRetrieval:
    """Test order retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_order(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test retrieving an order by ID."""
        # Place an order
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"USDT": "100000"}
        )
        mock_client._make_request.return_value = {
            "orderId": "12345",
            "status": "NEW",
        }

        placed_order = await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.01"),
            order_type=OrderType.LIMIT,
            price=Decimal("50000"),
        )

        # Retrieve the order
        retrieved_order = order_manager.get_order(placed_order.order_id)

        assert retrieved_order.order_id == placed_order.order_id
        assert retrieved_order.symbol == "BTCUSDT"

    def test_get_order_not_found(
        self,
        order_manager: OrderManager,
    ) -> None:
        """Test retrieving non-existent order."""
        with pytest.raises(OrderNotFoundError):
            order_manager.get_order("nonexistent-order-id")

    @pytest.mark.asyncio
    async def test_get_open_orders(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test retrieving all open orders."""
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"USDT": "100000"}
        )
        mock_client._make_request.return_value = {
            "orderId": "12345",
            "status": "NEW",
        }

        # Place multiple orders
        await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.01"),
            order_type=OrderType.LIMIT,
            price=Decimal("50000"),
        )

        mock_client._make_request.return_value = {
            "orderId": "12346",
            "status": "NEW",
        }

        await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.02"),
            order_type=OrderType.LIMIT,
            price=Decimal("49000"),
        )

        open_orders = order_manager.get_open_orders()

        assert len(open_orders) == 2

    @pytest.mark.asyncio
    async def test_get_open_orders_by_symbol(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test filtering open orders by symbol."""
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"USDT": "100000"}
        )
        mock_client._make_request.return_value = {
            "orderId": "12345",
            "status": "NEW",
        }

        await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.01"),
            order_type=OrderType.LIMIT,
            price=Decimal("50000"),
        )

        open_orders = order_manager.get_open_orders(symbol="BTCUSDT")
        assert len(open_orders) == 1

        # Filter by different symbol
        open_orders = order_manager.get_open_orders(symbol="ETHUSDT")
        assert len(open_orders) == 0


class TestOrderStatusSync:
    """Test order status synchronization."""

    @pytest.mark.asyncio
    async def test_sync_order_status(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test synchronizing order status with exchange."""
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"USDT": "100000"}
        )
        mock_client._make_request.return_value = {
            "orderId": "12345",
            "status": "NEW",
        }

        order = await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.01"),
            order_type=OrderType.LIMIT,
            price=Decimal("50000"),
        )

        # Simulate order being filled on exchange
        mock_client._make_request.return_value = {
            "orderId": "12345",
            "status": "FILLED",
            "executedQty": "0.01",
            "cummulativeQuoteQty": "500",
        }

        synced_order = await order_manager.sync_order_status(order.order_id)

        assert synced_order.status == OrderStatus.FILLED


class TestCancelAllOrders:
    """Test bulk order cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_all_orders(
        self,
        order_manager: OrderManager,
        mock_client: MagicMock,
    ) -> None:
        """Test cancelling all open orders."""
        mock_client.get_account_info.return_value = create_mock_account_info(
            {"USDT": "100000"}
        )
        mock_client._make_request.return_value = {
            "orderId": "12345",
            "status": "NEW",
        }

        # Place orders
        await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.01"),
            order_type=OrderType.LIMIT,
            price=Decimal("50000"),
        )

        mock_client._make_request.return_value = {
            "orderId": "12346",
            "status": "NEW",
        }

        await order_manager.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.02"),
            order_type=OrderType.LIMIT,
            price=Decimal("49000"),
        )

        assert len(order_manager.get_open_orders()) == 2

        # Cancel all
        mock_client._make_request.return_value = {"status": "CANCELED"}
        cancelled = await order_manager.cancel_all_orders()

        assert len(cancelled) == 2
        assert len(order_manager.get_open_orders()) == 0
