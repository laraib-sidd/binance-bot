"""
Helios Trading Bot - Trading Exceptions

Custom exception classes for trading operations with security-conscious
error handling for financial applications.
"""

from typing import Any, Dict, Optional


class TradingError(Exception):
    """Base exception for all trading-related errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        return self.message


class OrderValidationError(TradingError):
    """Order failed validation checks before submission."""

    pass


class InsufficientBalanceError(OrderValidationError):
    """Account balance insufficient for the requested order."""

    pass


class InvalidSymbolError(OrderValidationError):
    """Trading symbol is invalid or not available."""

    pass


class OrderQuantityError(OrderValidationError):
    """Order quantity is invalid (too small, too large, or wrong precision)."""

    pass


class OrderPriceError(OrderValidationError):
    """Order price is invalid for the given order type."""

    pass


class RiskLimitExceeded(TradingError):
    """Order would exceed configured risk limits."""

    pass


class DrawdownLimitExceeded(RiskLimitExceeded):
    """Account drawdown has exceeded the maximum allowed threshold."""

    pass


class DailyLossLimitExceeded(RiskLimitExceeded):
    """Daily loss limit has been reached."""

    pass


class PositionLimitExceeded(RiskLimitExceeded):
    """Maximum position size or count exceeded."""

    pass


class OrderExecutionError(TradingError):
    """Error during order execution on the exchange."""

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        exchange_error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.order_id = order_id
        self.exchange_error_code = exchange_error_code


class OrderNotFoundError(TradingError):
    """Requested order was not found."""

    def __init__(self, order_id: str):
        super().__init__(f"Order not found: {order_id}")
        self.order_id = order_id


class PositionError(TradingError):
    """Error related to position tracking or management."""

    pass


class OrderCancellationError(TradingError):
    """Failed to cancel an order."""

    def __init__(
        self,
        message: str,
        order_id: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.order_id = order_id
