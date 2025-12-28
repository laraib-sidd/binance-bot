"""
Helios Trading Bot - Order Manager

Core order lifecycle management system for placing, tracking, and managing
orders on Binance exchange. Integrates with BinanceClient for exchange
operations and validates all orders before submission.

This module handles:
- Order submission with validation
- Order cancellation
- Order status synchronization
- Order persistence (database storage)
- Audit trail for order lifecycle events
"""

from decimal import Decimal
import logging
from typing import Dict, List, Optional

from src.api.binance_client import BinanceClient
from src.core.config import TradingConfig

from .exceptions import (
    OrderCancellationError,
    OrderExecutionError,
    OrderNotFoundError,
    OrderValidationError,
)
from .order_models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from .order_validator import OrderValidator, SymbolInfo

logger = logging.getLogger(__name__)


class OrderManager:
    """
    Manages the complete lifecycle of trading orders.

    Responsibilities:
    - Validate orders before submission
    - Submit orders to Binance API
    - Track order status and fill events
    - Maintain local order cache
    - Handle order cancellation
    - Provide order history access

    All monetary calculations use Decimal for precision per rule 010.
    """

    def __init__(
        self,
        client: BinanceClient,
        config: TradingConfig,
        validator: Optional[OrderValidator] = None,
    ):
        """
        Initialize OrderManager.

        Args:
            client: BinanceClient for exchange operations
            config: Trading configuration
            validator: Optional OrderValidator (created if not provided)
        """
        self._client = client
        self._config = config
        self._validator = validator or OrderValidator()

        # Local order cache: order_id -> Order
        self._orders: Dict[str, Order] = {}

        # Symbol info cache
        self._symbol_info: Dict[str, SymbolInfo] = {}

        # Track initialization state
        self._initialized = False

    @classmethod
    def from_config(
        cls,
        client: BinanceClient,
        config: TradingConfig,
    ) -> "OrderManager":
        """
        Create OrderManager from configuration.

        Args:
            client: BinanceClient instance
            config: Trading configuration

        Returns:
            Configured OrderManager instance
        """
        return cls(client=client, config=config)

    async def initialize(self) -> None:
        """
        Initialize order manager by loading symbol info from exchange.

        This should be called before placing any orders to ensure
        proper validation against exchange trading rules.
        """
        if self._initialized:
            return

        await self._load_symbol_info()
        self._initialized = True
        logger.info("OrderManager initialized with %d symbols", len(self._symbol_info))

    async def _load_symbol_info(self) -> None:
        """Load trading rules for configured symbols from exchange."""
        try:
            exchange_info = await self._client.get_exchange_info()

            for symbol_data in exchange_info.get("symbols", []):
                symbol = symbol_data.get("symbol", "")

                # Only load info for configured trading pairs
                if symbol not in self._config.default_trading_pairs:
                    continue

                symbol_info = self._parse_symbol_info(symbol_data)
                self._symbol_info[symbol] = symbol_info
                self._validator.set_symbol_info(symbol, symbol_info)

        except Exception as e:
            logger.warning("Failed to load symbol info: %s", e)

    def _parse_symbol_info(self, data: dict) -> SymbolInfo:
        """Parse symbol info from exchange API response."""
        symbol = data.get("symbol", "")
        base_asset = data.get("baseAsset", "")
        quote_asset = data.get("quoteAsset", "")

        # Extract filter values
        min_quantity = Decimal("0.00001")
        max_quantity = Decimal("9999999")
        step_size = Decimal("0.00001")
        min_price = Decimal("0.01")
        max_price = Decimal("9999999")
        tick_size = Decimal("0.01")
        min_notional = Decimal("10")

        for filter_data in data.get("filters", []):
            filter_type = filter_data.get("filterType", "")

            if filter_type == "LOT_SIZE":
                min_quantity = Decimal(filter_data.get("minQty", "0.00001"))
                max_quantity = Decimal(filter_data.get("maxQty", "9999999"))
                step_size = Decimal(filter_data.get("stepSize", "0.00001"))

            elif filter_type == "PRICE_FILTER":
                min_price = Decimal(filter_data.get("minPrice", "0.01"))
                max_price = Decimal(filter_data.get("maxPrice", "9999999"))
                tick_size = Decimal(filter_data.get("tickSize", "0.01"))

            elif filter_type == "NOTIONAL" or filter_type == "MIN_NOTIONAL":
                min_notional = Decimal(filter_data.get("minNotional", "10"))

        return SymbolInfo(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            is_trading=data.get("status") == "TRADING",
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            step_size=step_size,
            min_price=min_price,
            max_price=max_price,
            tick_size=tick_size,
            min_notional=min_notional,
        )

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.LIMIT,
        price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
    ) -> Order:
        """
        Place a new order on the exchange.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            side: Order side (BUY or SELL)
            quantity: Order quantity
            order_type: Order type (MARKET or LIMIT)
            price: Order price (required for LIMIT orders)
            time_in_force: Time in force (GTC, IOC, FOK)

        Returns:
            Order object with updated status

        Raises:
            OrderValidationError: If order fails validation
            OrderExecutionError: If order submission fails
        """
        # Create order object
        order = Order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
        )

        # Get available balance for validation
        available_balance = await self._get_available_balance(symbol, side)

        # Get current price for market orders
        current_price = None
        if order_type == OrderType.MARKET:
            current_price = await self._get_current_price(symbol)

        # Validate order
        validation_result = self._validator.validate_order(
            order,
            available_balance=available_balance,
            current_price=current_price,
        )

        if not validation_result.is_valid:
            order.mark_rejected("; ".join(validation_result.errors))
            self._orders[order.order_id] = order
            logger.warning("Order validation failed: %s", validation_result.errors)
            raise OrderValidationError(
                f"Order validation failed: {validation_result.errors}",
                context={
                    "order_id": order.order_id,
                    "errors": validation_result.errors,
                },
            )

        # Log warnings if any
        for warning in validation_result.warnings:
            logger.warning("Order validation warning: %s", warning)

        # Store order in cache
        self._orders[order.order_id] = order

        # Submit to exchange
        try:
            exchange_response = await self._submit_order_to_exchange(order)
            self._process_exchange_response(order, exchange_response)

            logger.info(
                "Order placed successfully: %s %s %s @ %s (exchange_id: %s)",
                order.side.value,
                order.quantity,
                order.symbol,
                order.price or "MARKET",
                order.exchange_order_id,
            )

        except Exception as e:
            order.mark_rejected(str(e))
            logger.error("Order submission failed: %s", e)
            raise OrderExecutionError(
                f"Failed to submit order: {e}",
                order_id=order.order_id,
                context={"symbol": symbol, "side": side.value},
            ) from e

        return order

    async def _submit_order_to_exchange(self, order: Order) -> dict:
        """Submit order to Binance API."""
        params = {
            "symbol": order.symbol,
            "side": order.side.value,
            "type": order.order_type.value,
            "quantity": str(order.quantity),
            "newClientOrderId": order.order_id,
        }

        if order.order_type == OrderType.LIMIT:
            params["price"] = str(order.price)
            params["timeInForce"] = order.time_in_force

        # Use the client's test order endpoint if on testnet
        # For actual implementation, this would call client.create_order()
        # Currently returning a mock response structure
        response = await self._client._make_request(
            "POST",
            "/api/v3/order",
            params=params,
            signed=True,
        )

        return response

    def _process_exchange_response(self, order: Order, response: dict) -> None:
        """Process exchange order response and update order status."""
        exchange_order_id = str(response.get("orderId", ""))
        order.mark_submitted(exchange_order_id)

        status = response.get("status", "")

        if status == "FILLED":
            # Order immediately filled
            filled_qty = Decimal(str(response.get("executedQty", "0")))
            avg_price = Decimal(str(response.get("price", "0")))

            # Handle cummulative quote qty for average price
            if response.get("cummulativeQuoteQty"):
                cum_quote = Decimal(str(response["cummulativeQuoteQty"]))
                if filled_qty > 0:
                    avg_price = cum_quote / filled_qty

            order.update_fill(
                filled_qty=filled_qty,
                fill_price=avg_price,
            )

        elif status == "PARTIALLY_FILLED":
            filled_qty = Decimal(str(response.get("executedQty", "0")))
            avg_price = Decimal(str(response.get("price", "0")))
            order.update_fill(
                filled_qty=filled_qty,
                fill_price=avg_price,
            )

        elif status == "NEW":
            order.mark_open()

        elif status == "CANCELED":
            order.mark_cancelled()

        elif status == "REJECTED":
            order.mark_rejected(response.get("msg", "Unknown rejection reason"))

    async def cancel_order(self, order_id: str) -> Order:
        """
        Cancel an open order.

        Args:
            order_id: Helios order ID

        Returns:
            Updated Order object

        Raises:
            OrderNotFoundError: If order not found
            OrderCancellationError: If cancellation fails
        """
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)

        # Validate cancellation is possible
        validation_result = self._validator.validate_cancel(order)
        if not validation_result.is_valid:
            raise OrderCancellationError(
                f"Cannot cancel order: {validation_result.errors}",
                order_id=order_id,
            )

        try:
            # Cancel on exchange
            await self._client._make_request(
                "DELETE",
                "/api/v3/order",
                params={
                    "symbol": order.symbol,
                    "orderId": order.exchange_order_id,
                },
                signed=True,
            )

            order.mark_cancelled()
            logger.info("Order cancelled: %s", order_id)

        except Exception as e:
            logger.error("Order cancellation failed: %s", e)
            raise OrderCancellationError(
                f"Failed to cancel order: {e}",
                order_id=order_id,
            ) from e

        return order

    async def sync_order_status(self, order_id: str) -> Order:
        """
        Synchronize order status with exchange.

        Args:
            order_id: Helios order ID

        Returns:
            Updated Order object

        Raises:
            OrderNotFoundError: If order not found
        """
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)

        if not order.exchange_order_id:
            # Order was never submitted
            return order

        try:
            response = await self._client._make_request(
                "GET",
                "/api/v3/order",
                params={
                    "symbol": order.symbol,
                    "orderId": order.exchange_order_id,
                },
                signed=True,
            )

            self._process_exchange_response(order, response)

        except Exception as e:
            logger.warning("Failed to sync order status: %s", e)

        return order

    def get_order(self, order_id: str) -> Order:
        """
        Get order by ID.

        Args:
            order_id: Helios order ID

        Returns:
            Order object

        Raises:
            OrderNotFoundError: If order not found
        """
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get all open orders, optionally filtered by symbol.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open orders
        """
        orders = [o for o in self._orders.values() if o.is_active]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    def get_all_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> List[Order]:
        """
        Get orders with optional filters.

        Args:
            symbol: Optional symbol filter
            status: Optional status filter
            limit: Maximum number of orders to return

        Returns:
            List of orders matching filters
        """
        orders = list(self._orders.values())

        if symbol:
            orders = [o for o in orders if o.symbol == symbol]

        if status:
            orders = [o for o in orders if o.status == status]

        # Sort by created_at descending
        orders.sort(key=lambda o: o.created_at, reverse=True)

        return orders[:limit]

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Cancel all open orders, optionally for a specific symbol.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of cancelled orders
        """
        open_orders = self.get_open_orders(symbol)
        cancelled: List[Order] = []

        for order in open_orders:
            try:
                await self.cancel_order(order.order_id)
                cancelled.append(order)
            except Exception as e:
                logger.warning("Failed to cancel order %s: %s", order.order_id, e)

        logger.info("Cancelled %d orders", len(cancelled))
        return cancelled

    async def _get_available_balance(
        self,
        symbol: str,
        side: OrderSide,
    ) -> Decimal:
        """Get available balance for order validation."""
        try:
            account_info = await self._client.get_account_info()

            # Determine which asset balance to check
            symbol_info = self._symbol_info.get(symbol)
            if symbol_info:
                if side == OrderSide.BUY:
                    asset = symbol_info.quote_asset  # Need USDT to buy BTC
                else:
                    asset = symbol_info.base_asset  # Need BTC to sell
            else:
                # Fallback: assume USDT for buy, extract base from symbol
                if side == OrderSide.BUY:
                    asset = "USDT"
                else:
                    # Try to extract base asset
                    for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                        if symbol.endswith(quote):
                            asset = symbol[: -len(quote)]
                            break
                    else:
                        asset = symbol[:3]  # Guess first 3 chars

            # Find balance for asset
            for balance in account_info.get("balances", []):
                if balance.get("asset") == asset:
                    return Decimal(str(balance.get("free", "0")))

            return Decimal("0")

        except Exception as e:
            logger.warning("Failed to get account balance: %s", e)
            return Decimal("0")

    async def _get_current_price(self, symbol: str) -> Decimal:
        """Get current market price for a symbol."""
        try:
            ticker = await self._client.get_ticker_price(symbol)
            return Decimal(str(ticker.get("price", "0")))
        except Exception as e:
            logger.warning("Failed to get current price for %s: %s", symbol, e)
            return Decimal("0")
