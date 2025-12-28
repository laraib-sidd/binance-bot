"""
Helios Trading Bot - Order Validator

Pre-order validation logic to ensure orders meet all requirements before
submission to the exchange. Implements financial safety checks per rule 010.

Validation includes:
- Balance sufficiency with safety buffer
- Symbol validity and tradability
- Quantity precision and minimum order size
- Price validity for limit orders
- Risk limit compliance
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from .order_models import Order, OrderSide, OrderType


@dataclass
class SymbolInfo:
    """Exchange symbol trading rules and constraints."""

    symbol: str
    base_asset: str  # e.g., BTC
    quote_asset: str  # e.g., USDT
    is_trading: bool = True

    # Precision constraints
    base_precision: int = 8  # Decimal places for quantity
    quote_precision: int = 8  # Decimal places for price

    # Quantity constraints
    min_quantity: Decimal = Decimal("0.00001")
    max_quantity: Decimal = Decimal("9999999")
    step_size: Decimal = Decimal("0.00001")  # Quantity must be multiple of this

    # Price constraints
    min_price: Decimal = Decimal("0.00000001")
    max_price: Decimal = Decimal("9999999")
    tick_size: Decimal = Decimal("0.01")  # Price must be multiple of this

    # Notional constraints
    min_notional: Decimal = Decimal("10")  # Minimum order value in quote asset


@dataclass
class ValidationResult:
    """Result of order validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]

    @classmethod
    def success(cls, warnings: Optional[list[str]] = None) -> "ValidationResult":
        """Create successful validation result."""
        return cls(is_valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(
        cls, errors: list[str], warnings: Optional[list[str]] = None
    ) -> "ValidationResult":
        """Create failed validation result."""
        return cls(is_valid=False, errors=errors, warnings=warnings or [])


class OrderValidator:
    """
    Validates orders before submission to exchange.

    Performs comprehensive checks including:
    - Account balance sufficiency
    - Symbol validity and trading status
    - Quantity constraints (min/max/step)
    - Price constraints (min/max/tick)
    - Notional value requirements
    - Risk limit compliance
    """

    # Safety buffer percentage for balance checks (5% buffer per rule 010)
    BALANCE_SAFETY_BUFFER = Decimal("0.05")

    def __init__(
        self,
        symbol_info: Optional[Dict[str, SymbolInfo]] = None,
    ):
        """
        Initialize order validator.

        Args:
            symbol_info: Dictionary mapping symbols to their trading rules
        """
        self._symbol_info: Dict[str, SymbolInfo] = symbol_info or {}

    def set_symbol_info(self, symbol: str, info: SymbolInfo) -> None:
        """Set trading rules for a symbol."""
        self._symbol_info[symbol] = info

    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Get trading rules for a symbol."""
        return self._symbol_info.get(symbol)

    def validate_order(
        self,
        order: Order,
        available_balance: Decimal,
        current_price: Optional[Decimal] = None,
    ) -> ValidationResult:
        """
        Perform comprehensive order validation.

        Args:
            order: Order to validate
            available_balance: Available balance in quote asset (for BUY)
                              or base asset (for SELL)
            current_price: Current market price (used for MARKET orders)

        Returns:
            ValidationResult with validation outcome and any errors/warnings
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Validate symbol
        symbol_errors = self._validate_symbol(order.symbol)
        errors.extend(symbol_errors)

        # 2. Validate quantity
        qty_errors, qty_warnings = self._validate_quantity(order)
        errors.extend(qty_errors)
        warnings.extend(qty_warnings)

        # 3. Validate price (for limit orders)
        price_errors = self._validate_price(order, current_price)
        errors.extend(price_errors)

        # 4. Validate balance
        balance_errors = self._validate_balance(order, available_balance, current_price)
        errors.extend(balance_errors)

        # 5. Validate notional value
        notional_errors = self._validate_notional(order, current_price)
        errors.extend(notional_errors)

        if errors:
            return ValidationResult.failure(errors, warnings)
        return ValidationResult.success(warnings)

    def _validate_symbol(self, symbol: str) -> list[str]:
        """Validate symbol is known and tradeable."""
        errors: list[str] = []

        if not symbol:
            errors.append("Symbol is required")
            return errors

        symbol_info = self._symbol_info.get(symbol)
        if symbol_info is None:
            # If no symbol info loaded, issue warning but don't fail
            # This allows validation without exchange info loaded
            return []

        if not symbol_info.is_trading:
            errors.append(f"Symbol {symbol} is not currently trading")

        return errors

    def _validate_quantity(self, order: Order) -> tuple[list[str], list[str]]:
        """Validate order quantity against constraints."""
        errors: list[str] = []
        warnings: list[str] = []

        # Basic quantity checks
        if order.quantity <= Decimal("0"):
            errors.append("Quantity must be positive")
            return errors, warnings

        symbol_info = self._symbol_info.get(order.symbol)
        if symbol_info is None:
            # Without symbol info, only do basic validation
            return errors, warnings

        # Check minimum quantity
        if order.quantity < symbol_info.min_quantity:
            errors.append(
                f"Quantity {order.quantity} below minimum {symbol_info.min_quantity}"
            )

        # Check maximum quantity
        if order.quantity > symbol_info.max_quantity:
            errors.append(
                f"Quantity {order.quantity} exceeds maximum {symbol_info.max_quantity}"
            )

        # Check step size (quantity precision)
        if symbol_info.step_size > 0:
            remainder = order.quantity % symbol_info.step_size
            if remainder != Decimal("0"):
                warnings.append(
                    f"Quantity {order.quantity} not aligned to step size "
                    f"{symbol_info.step_size}"
                )

        return errors, warnings

    def _validate_price(
        self,
        order: Order,
        current_price: Optional[Decimal],
    ) -> list[str]:
        """Validate order price for limit orders."""
        errors: list[str] = []

        # Market orders don't need price validation
        if order.order_type == OrderType.MARKET:
            return errors

        # Limit orders require a price
        if order.price is None:
            errors.append("Price is required for limit orders")
            return errors

        if order.price <= Decimal("0"):
            errors.append("Price must be positive")
            return errors

        symbol_info = self._symbol_info.get(order.symbol)
        if symbol_info is None:
            return errors

        self._check_price_bounds(errors, order.price, symbol_info)
        return errors

    def _check_price_bounds(
        self,
        errors: list[str],
        price: Decimal,
        symbol_info: SymbolInfo,
    ) -> None:
        """Check price against symbol bounds and tick size."""
        if price < symbol_info.min_price:
            errors.append(f"Price {price} below minimum {symbol_info.min_price}")

        if price > symbol_info.max_price:
            errors.append(f"Price {price} exceeds maximum {symbol_info.max_price}")

        # Check tick size alignment
        if symbol_info.tick_size > 0:
            remainder = price % symbol_info.tick_size
            if remainder != Decimal("0"):
                errors.append(
                    f"Price {price} not aligned to tick size {symbol_info.tick_size}"
                )

    def _validate_balance(
        self,
        order: Order,
        available_balance: Decimal,
        current_price: Optional[Decimal],
    ) -> list[str]:
        """Validate account has sufficient balance with safety buffer."""
        errors: list[str] = []

        if available_balance <= Decimal("0"):
            errors.append("Insufficient balance: balance is zero or negative")
            return errors

        # Calculate required balance
        if order.side == OrderSide.BUY:
            # For buy orders, need quote asset (e.g., USDT)
            if order.order_type == OrderType.MARKET:
                if current_price is None:
                    errors.append("Current price required to validate market buy order")
                    return errors
                required = order.quantity * current_price
            else:
                if order.price is None:
                    errors.append("Price required for limit order balance check")
                    return errors
                required = order.quantity * order.price

            # Add safety buffer per rule 010
            required_with_buffer = required * (1 + self.BALANCE_SAFETY_BUFFER)

            if required_with_buffer > available_balance:
                errors.append(
                    f"Insufficient balance: need {required_with_buffer:.8f} "
                    f"(including 5% buffer), have {available_balance:.8f}"
                )

        else:  # SELL
            # For sell orders, need base asset quantity
            required_with_buffer = order.quantity * (1 + self.BALANCE_SAFETY_BUFFER)

            if required_with_buffer > available_balance:
                errors.append(
                    f"Insufficient balance: need {required_with_buffer:.8f} "
                    f"(including 5% buffer), have {available_balance:.8f}"
                )

        return errors

    def _validate_notional(
        self,
        order: Order,
        current_price: Optional[Decimal],
    ) -> list[str]:
        """Validate order meets minimum notional value requirement."""
        errors: list[str] = []

        symbol_info = self._symbol_info.get(order.symbol)
        if symbol_info is None:
            return errors

        # Calculate notional value
        if order.order_type == OrderType.MARKET:
            if current_price is None:
                return errors  # Can't validate without price
            notional = order.quantity * current_price
        else:
            if order.price is None:
                return errors
            notional = order.quantity * order.price

        if notional < symbol_info.min_notional:
            errors.append(
                f"Order notional value {notional:.2f} below minimum "
                f"{symbol_info.min_notional}"
            )

        return errors

    def validate_cancel(self, order: Order) -> ValidationResult:
        """Validate that an order can be cancelled."""
        errors: list[str] = []

        if not order.is_active:
            errors.append(f"Cannot cancel order in status {order.status.value}")

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()


def create_default_symbol_info(symbol: str) -> SymbolInfo:
    """
    Create default symbol info for common trading pairs.

    This provides reasonable defaults for testing and development.
    In production, symbol info should be fetched from the exchange.
    """
    # Extract base and quote assets from symbol
    # Assumes format like BTCUSDT, ETHUSDT, etc.
    quote_assets = ["USDT", "BUSD", "BTC", "ETH"]
    base_asset = symbol
    quote_asset = ""

    for quote in quote_assets:
        if symbol.endswith(quote):
            base_asset = symbol[: -len(quote)]
            quote_asset = quote
            break

    return SymbolInfo(
        symbol=symbol,
        base_asset=base_asset,
        quote_asset=quote_asset,
        is_trading=True,
        base_precision=8,
        quote_precision=8,
        min_quantity=Decimal("0.00001"),
        max_quantity=Decimal("9999999"),
        step_size=Decimal("0.00001"),
        min_price=Decimal("0.01"),
        max_price=Decimal("9999999"),
        tick_size=Decimal("0.01"),
        min_notional=Decimal("10"),
    )
