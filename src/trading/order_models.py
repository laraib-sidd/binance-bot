"""
Helios Trading Bot - Order and Position Models

Dataclasses for representing orders and positions with proper Decimal precision
for all financial calculations per rule 010-trading-bot-specific.

All monetary values use Decimal to avoid floating-point precision errors.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class OrderSide(str, Enum):
    """Order side - buy or sell."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    STOP_MARKET = "STOP_MARKET"


class OrderStatus(str, Enum):
    """Order lifecycle status."""

    PENDING = "PENDING"  # Created but not yet submitted to exchange
    SUBMITTED = "SUBMITTED"  # Submitted to exchange, awaiting acknowledgment
    OPEN = "OPEN"  # Acknowledged by exchange, waiting to fill
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Partially executed
    FILLED = "FILLED"  # Fully executed
    CANCELLED = "CANCELLED"  # Cancelled by user or system
    REJECTED = "REJECTED"  # Rejected by exchange or validation
    EXPIRED = "EXPIRED"  # Time-in-force expired


class PositionSide(str, Enum):
    """Position side enumeration."""

    LONG = "LONG"  # Holding asset (bought)
    SHORT = "SHORT"  # Borrowed and sold (not used in spot)
    FLAT = "FLAT"  # No position


def generate_order_id() -> str:
    """Generate a unique order ID with timestamp prefix for sorting."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    unique_part = uuid.uuid4().hex[:12]
    return f"HLO-{timestamp}-{unique_part}"


@dataclass
class Order:
    """
    Represents a trading order with full lifecycle tracking.

    All monetary values use Decimal for precision per rule 010.
    """

    # Required fields
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal

    # Optional fields with defaults
    order_id: str = field(default_factory=generate_order_id)
    price: Optional[Decimal] = None  # Required for LIMIT orders
    stop_price: Optional[Decimal] = None  # Required for STOP orders
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Execution details (updated as order fills)
    filled_quantity: Decimal = field(default_factory=lambda: Decimal("0"))
    average_fill_price: Optional[Decimal] = None
    commission: Decimal = field(default_factory=lambda: Decimal("0"))
    commission_asset: Optional[str] = None

    # Exchange tracking
    exchange_order_id: Optional[str] = None
    client_order_id: Optional[str] = None

    # Metadata
    time_in_force: str = "GTC"  # Good Till Cancelled
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate order after initialization."""
        # Ensure quantity is Decimal
        if not isinstance(self.quantity, Decimal):
            self.quantity = Decimal(str(self.quantity))

        # Ensure price is Decimal if provided
        if self.price is not None and not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))

        # Ensure stop_price is Decimal if provided
        if self.stop_price is not None and not isinstance(self.stop_price, Decimal):
            self.stop_price = Decimal(str(self.stop_price))

        # Ensure filled_quantity is Decimal
        if not isinstance(self.filled_quantity, Decimal):
            self.filled_quantity = Decimal(str(self.filled_quantity))

        # Ensure commission is Decimal
        if not isinstance(self.commission, Decimal):
            self.commission = Decimal(str(self.commission))

    @property
    def remaining_quantity(self) -> Decimal:
        """Calculate remaining unfilled quantity."""
        return self.quantity - self.filled_quantity

    @property
    def fill_percentage(self) -> Decimal:
        """Calculate fill percentage (0-100)."""
        if self.quantity == 0:
            return Decimal("0")
        return (self.filled_quantity / self.quantity) * Decimal("100")

    @property
    def is_active(self) -> bool:
        """Check if order is still active (can be filled or cancelled)."""
        return self.status in (
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        )

    @property
    def is_complete(self) -> bool:
        """Check if order lifecycle is complete."""
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        )

    @property
    def notional_value(self) -> Optional[Decimal]:
        """Calculate notional value of the order (quantity * price)."""
        if self.price is not None:
            return self.quantity * self.price
        if self.average_fill_price is not None:
            return self.quantity * self.average_fill_price
        return None

    @property
    def filled_notional_value(self) -> Optional[Decimal]:
        """Calculate filled notional value."""
        if self.average_fill_price is not None:
            return self.filled_quantity * self.average_fill_price
        return None

    def update_fill(
        self,
        filled_qty: Decimal,
        fill_price: Decimal,
        commission: Decimal = Decimal("0"),
        commission_asset: Optional[str] = None,
    ) -> None:
        """
        Update order with a fill event.

        Args:
            filled_qty: Quantity filled in this execution
            fill_price: Price of this fill
            commission: Commission charged for this fill
            commission_asset: Asset used for commission
        """
        # Update average fill price (weighted average)
        total_filled = self.filled_quantity + filled_qty
        if total_filled > 0:
            if self.average_fill_price is None:
                self.average_fill_price = fill_price
            else:
                old_value = self.filled_quantity * self.average_fill_price
                new_value = filled_qty * fill_price
                self.average_fill_price = (old_value + new_value) / total_filled

        self.filled_quantity = total_filled
        self.commission += commission
        if commission_asset:
            self.commission_asset = commission_asset

        # Update status based on fill
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED

        self.updated_at = datetime.now(timezone.utc)

    def mark_submitted(self, exchange_order_id: str) -> None:
        """Mark order as submitted to exchange."""
        self.status = OrderStatus.SUBMITTED
        self.exchange_order_id = exchange_order_id
        self.updated_at = datetime.now(timezone.utc)

    def mark_open(self) -> None:
        """Mark order as acknowledged and open on exchange."""
        self.status = OrderStatus.OPEN
        self.updated_at = datetime.now(timezone.utc)

    def mark_cancelled(self) -> None:
        """Mark order as cancelled."""
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc)

    def mark_rejected(self, reason: Optional[str] = None) -> None:
        """Mark order as rejected."""
        self.status = OrderStatus.REJECTED
        if reason:
            self.notes = f"Rejected: {reason}"
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert order to dictionary for serialization."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": str(self.quantity),
            "price": str(self.price) if self.price else None,
            "stop_price": str(self.stop_price) if self.stop_price else None,
            "status": self.status.value,
            "filled_quantity": str(self.filled_quantity),
            "average_fill_price": (
                str(self.average_fill_price) if self.average_fill_price else None
            ),
            "commission": str(self.commission),
            "commission_asset": self.commission_asset,
            "exchange_order_id": self.exchange_order_id,
            "time_in_force": self.time_in_force,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": self.notes,
        }


@dataclass
class Position:
    """
    Represents an open position in a trading symbol.

    Tracks entry price, current price, and P&L calculations.
    All monetary values use Decimal for precision per rule 010.
    """

    # Required fields
    symbol: str
    side: PositionSide
    quantity: Decimal
    entry_price: Decimal

    # Tracking fields
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # P&L tracking
    current_price: Decimal = field(default_factory=lambda: Decimal("0"))
    realized_pnl: Decimal = field(default_factory=lambda: Decimal("0"))
    total_commission: Decimal = field(default_factory=lambda: Decimal("0"))

    def __post_init__(self) -> None:
        """Ensure all monetary values are Decimal."""
        if not isinstance(self.quantity, Decimal):
            self.quantity = Decimal(str(self.quantity))
        if not isinstance(self.entry_price, Decimal):
            self.entry_price = Decimal(str(self.entry_price))
        if not isinstance(self.current_price, Decimal):
            self.current_price = Decimal(str(self.current_price))
        if not isinstance(self.realized_pnl, Decimal):
            self.realized_pnl = Decimal(str(self.realized_pnl))
        if not isinstance(self.total_commission, Decimal):
            self.total_commission = Decimal(str(self.total_commission))

        # Initialize current_price to entry_price if not set
        if self.current_price == Decimal("0"):
            self.current_price = self.entry_price

    @property
    def is_flat(self) -> bool:
        """Check if position is flat (no holdings)."""
        return self.side == PositionSide.FLAT or self.quantity == Decimal("0")

    @property
    def notional_value(self) -> Decimal:
        """Calculate current notional value of position."""
        return self.quantity * self.current_price

    @property
    def entry_notional_value(self) -> Decimal:
        """Calculate entry notional value of position."""
        return self.quantity * self.entry_price

    @property
    def unrealized_pnl(self) -> Decimal:
        """
        Calculate unrealized P&L based on current price.

        For LONG: (current - entry) * quantity
        For SHORT: (entry - current) * quantity
        """
        if self.is_flat:
            return Decimal("0")

        price_diff = self.current_price - self.entry_price

        if self.side == PositionSide.LONG:
            return price_diff * self.quantity
        elif self.side == PositionSide.SHORT:
            return -price_diff * self.quantity
        else:
            return Decimal("0")

    @property
    def unrealized_pnl_percent(self) -> Decimal:
        """Calculate unrealized P&L as percentage of entry value."""
        if self.is_flat or self.entry_notional_value == 0:
            return Decimal("0")

        return (self.unrealized_pnl / self.entry_notional_value) * Decimal("100")

    @property
    def total_pnl(self) -> Decimal:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def net_pnl(self) -> Decimal:
        """Calculate net P&L after commissions."""
        return self.total_pnl - self.total_commission

    def update_price(self, price: Decimal) -> None:
        """Update current market price."""
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        self.current_price = price
        self.updated_at = datetime.now(timezone.utc)

    def add_to_position(
        self,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal = Decimal("0"),
    ) -> None:
        """
        Add to existing position (averaging in).

        Args:
            quantity: Additional quantity
            price: Price of the addition
            commission: Commission for this trade
        """
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        if not isinstance(price, Decimal):
            price = Decimal(str(price))

        # Calculate new average entry price
        total_quantity = self.quantity + quantity
        if total_quantity > 0:
            old_value = self.quantity * self.entry_price
            new_value = quantity * price
            self.entry_price = (old_value + new_value) / total_quantity

        self.quantity = total_quantity
        self.total_commission += commission
        self.updated_at = datetime.now(timezone.utc)

    def reduce_position(
        self,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal = Decimal("0"),
    ) -> Decimal:
        """
        Reduce position and realize P&L.

        Args:
            quantity: Quantity to reduce
            price: Exit price
            commission: Commission for this trade

        Returns:
            Realized P&L from this reduction
        """
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        if not isinstance(price, Decimal):
            price = Decimal(str(price))

        # Calculate realized P&L for this portion
        price_diff = price - self.entry_price
        if self.side == PositionSide.LONG:
            pnl = price_diff * quantity
        else:  # SHORT
            pnl = -price_diff * quantity

        self.realized_pnl += pnl
        self.quantity -= quantity
        self.total_commission += commission

        # If fully closed, mark as flat
        if self.quantity <= Decimal("0"):
            self.quantity = Decimal("0")
            self.side = PositionSide.FLAT

        self.updated_at = datetime.now(timezone.utc)
        return pnl

    def to_dict(self) -> dict:
        """Convert position to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": str(self.quantity),
            "entry_price": str(self.entry_price),
            "current_price": str(self.current_price),
            "unrealized_pnl": str(self.unrealized_pnl),
            "unrealized_pnl_percent": str(self.unrealized_pnl_percent),
            "realized_pnl": str(self.realized_pnl),
            "total_pnl": str(self.total_pnl),
            "net_pnl": str(self.net_pnl),
            "total_commission": str(self.total_commission),
            "notional_value": str(self.notional_value),
            "opened_at": self.opened_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def create_flat(cls, symbol: str) -> "Position":
        """Create a flat (no position) instance for a symbol."""
        return cls(
            symbol=symbol,
            side=PositionSide.FLAT,
            quantity=Decimal("0"),
            entry_price=Decimal("0"),
        )
