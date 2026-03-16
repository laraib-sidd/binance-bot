"""
Helios Trading Bot - Grid Trading Models

Core data structures for the Signal-Driven Dynamic Grid Trading strategy.
Defines grid configuration, levels, and session tracking with Decimal precision.

Grid trading works by placing buy orders below current price and sell orders
above, profiting from price oscillations within the grid range.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
import uuid


class GridStatus(Enum):
    """Status of a grid trading session."""

    PENDING = "pending"  # Grid calculated but not deployed
    ACTIVE = "active"  # Grid orders placed and monitoring
    PAUSED = "paused"  # Temporarily stopped (e.g., high volatility)
    COMPLETED = "completed"  # All grid levels filled or target reached
    STOPPED = "stopped"  # Manually stopped or hit stop-loss
    EXPIRED = "expired"  # Time limit reached


class GridLevelStatus(Enum):
    """Status of an individual grid level."""

    PENDING = "pending"  # Order not yet placed
    OPEN = "open"  # Buy/sell order active on exchange
    BUY_FILLED = "buy_filled"  # Buy order filled, waiting for sell
    SELL_FILLED = "sell_filled"  # Complete cycle (buy then sell)
    CANCELLED = "cancelled"  # Order cancelled


class GridSide(Enum):
    """Side of the grid relative to entry price."""

    BUY = "buy"  # Below entry price (buy orders)
    SELL = "sell"  # Above entry price (sell orders)


@dataclass
class GridConfig:
    """
    Configuration for a dynamic grid trading session.

    Grid parameters are calculated dynamically based on ATR (Average True Range)
    to adapt to current market volatility.
    """

    # Core parameters
    symbol: str
    grid_levels: int = 8  # Total number of grid levels (buy + sell)
    range_multiplier: Decimal = Decimal("2.0")  # ATR multiplier for grid range

    # Risk parameters
    risk_per_session: Decimal = Decimal("0.01")  # 1% of capital per session
    max_position_size: Decimal = Decimal("0.05")  # 5% max position
    safety_buffer: Decimal = Decimal("0.02")  # 2% buffer on stop-loss

    # Session parameters
    max_session_duration_hours: int = 4  # Auto-exit after 4 hours
    take_profit_percent: Decimal = Decimal("0.03")  # 3% session profit target
    stop_loss_percent: Decimal = Decimal("0.02")  # 2% below grid bottom

    # Grid spacing
    min_spacing_percent: Decimal = Decimal("0.005")  # 0.5% minimum spacing
    max_spacing_percent: Decimal = Decimal("0.03")  # 3% maximum spacing

    def validate(self) -> List[str]:
        """Validate grid configuration parameters."""
        errors = []

        if self.grid_levels < 4:
            errors.append("Grid levels must be at least 4")
        if self.grid_levels > 20:
            errors.append("Grid levels should not exceed 20")
        if self.grid_levels % 2 != 0:
            errors.append("Grid levels should be even (equal buy/sell)")

        if self.range_multiplier < Decimal("1.0"):
            errors.append("Range multiplier must be at least 1.0")
        if self.range_multiplier > Decimal("5.0"):
            errors.append("Range multiplier should not exceed 5.0")

        if self.risk_per_session <= Decimal("0"):
            errors.append("Risk per session must be positive")
        if self.risk_per_session > Decimal("0.05"):
            errors.append("Risk per session should not exceed 5%")

        if self.stop_loss_percent <= Decimal("0"):
            errors.append("Stop loss must be positive")

        return errors


@dataclass
class GridLevel:
    """
    Individual level within a trading grid.

    Each level represents a price point where an order is placed.
    Buy levels are below entry, sell levels are above.
    """

    level_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    level_index: int = 0  # 0 = closest to entry, higher = further away
    side: GridSide = GridSide.BUY

    # Price configuration
    price: Decimal = Decimal("0")
    quantity: Decimal = Decimal("0")

    # Order tracking
    order_id: Optional[str] = None  # Our internal order ID
    exchange_order_id: Optional[str] = None
    status: GridLevelStatus = GridLevelStatus.PENDING

    # Fill tracking
    buy_fill_price: Optional[Decimal] = None
    buy_fill_time: Optional[datetime] = None
    sell_fill_price: Optional[Decimal] = None
    sell_fill_time: Optional[datetime] = None

    # P&L for this level
    realized_pnl: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")

    @property
    def is_complete(self) -> bool:
        """Check if this grid level has completed a full cycle."""
        return self.status == GridLevelStatus.SELL_FILLED

    @property
    def is_active(self) -> bool:
        """Check if this level has an active order."""
        return self.status in (GridLevelStatus.OPEN, GridLevelStatus.BUY_FILLED)

    def mark_buy_filled(self, fill_price: Decimal, fill_time: datetime) -> None:
        """Mark the buy order as filled."""
        self.buy_fill_price = Decimal(str(fill_price))
        self.buy_fill_time = fill_time
        self.status = GridLevelStatus.BUY_FILLED

    def mark_sell_filled(
        self, fill_price: Decimal, fill_time: datetime, commission: Decimal
    ) -> Decimal:
        """
        Mark the sell order as filled and calculate P&L.

        Returns:
            Realized P&L from this grid cycle
        """
        self.sell_fill_price = Decimal(str(fill_price))
        self.sell_fill_time = fill_time
        self.commission = Decimal(str(commission))
        self.status = GridLevelStatus.SELL_FILLED

        # Calculate P&L
        if self.buy_fill_price:
            gross_pnl = (self.sell_fill_price - self.buy_fill_price) * self.quantity
            self.realized_pnl = gross_pnl - self.commission
        return self.realized_pnl

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "level_id": self.level_id,
            "level_index": self.level_index,
            "side": self.side.value,
            "price": str(self.price),
            "quantity": str(self.quantity),
            "order_id": self.order_id,
            "exchange_order_id": self.exchange_order_id,
            "status": self.status.value,
            "buy_fill_price": str(self.buy_fill_price) if self.buy_fill_price else None,
            "buy_fill_time": (
                self.buy_fill_time.isoformat() if self.buy_fill_time else None
            ),
            "sell_fill_price": (
                str(self.sell_fill_price) if self.sell_fill_price else None
            ),
            "sell_fill_time": (
                self.sell_fill_time.isoformat() if self.sell_fill_time else None
            ),
            "realized_pnl": str(self.realized_pnl),
            "commission": str(self.commission),
        }


@dataclass
class GridSession:
    """
    Complete grid trading session tracking.

    A session represents one deployment of a grid, from entry signal
    through completion or stop-out.
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    status: GridStatus = GridStatus.PENDING

    # Grid boundaries (calculated from ATR)
    entry_price: Decimal = Decimal("0")
    upper_bound: Decimal = Decimal("0")
    lower_bound: Decimal = Decimal("0")
    grid_spacing: Decimal = Decimal("0")

    # ATR used for calculation
    atr_value: Decimal = Decimal("0")

    # Capital allocation
    allocated_capital: Decimal = Decimal("0")
    order_size_per_level: Decimal = Decimal("0")

    # Grid levels
    levels: List[GridLevel] = field(default_factory=list)

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    max_duration_hours: int = 4

    # P&L tracking
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")

    # Stop levels
    stop_loss_price: Decimal = Decimal("0")
    take_profit_pnl: Decimal = Decimal("0")

    # Statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status == GridStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        """Check if session has exceeded max duration."""
        if not self.started_at:
            return False
        elapsed = datetime.now(timezone.utc) - self.started_at
        return elapsed.total_seconds() > (self.max_duration_hours * 3600)

    @property
    def buy_levels(self) -> List[GridLevel]:
        """Get all buy-side grid levels."""
        return [lvl for lvl in self.levels if lvl.side == GridSide.BUY]

    @property
    def sell_levels(self) -> List[GridLevel]:
        """Get all sell-side grid levels."""
        return [lvl for lvl in self.levels if lvl.side == GridSide.SELL]

    @property
    def active_levels(self) -> List[GridLevel]:
        """Get levels with active orders."""
        return [lvl for lvl in self.levels if lvl.is_active]

    @property
    def completed_levels(self) -> List[GridLevel]:
        """Get levels that completed full buy-sell cycle."""
        return [lvl for lvl in self.levels if lvl.is_complete]

    @property
    def fill_rate(self) -> Decimal:
        """Calculate percentage of levels that completed cycles."""
        if not self.levels:
            return Decimal("0")
        completed = len(self.completed_levels)
        total = len(self.levels)
        return Decimal(str(completed / total * 100))

    @property
    def total_pnl(self) -> Decimal:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def win_rate(self) -> Decimal:
        """Calculate win rate of completed trades."""
        if self.total_trades == 0:
            return Decimal("0")
        return Decimal(str(self.winning_trades / self.total_trades * 100))

    def start(self) -> None:
        """Mark session as started."""
        self.started_at = datetime.now(timezone.utc)
        self.status = GridStatus.ACTIVE

    def stop(self, reason: str = "") -> None:
        """Stop the session."""
        self.ended_at = datetime.now(timezone.utc)
        self.status = GridStatus.STOPPED

    def complete(self) -> None:
        """Mark session as completed (target reached or all levels filled)."""
        self.ended_at = datetime.now(timezone.utc)
        self.status = GridStatus.COMPLETED

    def expire(self) -> None:
        """Mark session as expired (time limit)."""
        self.ended_at = datetime.now(timezone.utc)
        self.status = GridStatus.EXPIRED

    def update_pnl(self, current_price: Decimal) -> None:
        """
        Update P&L calculations based on current price.

        Args:
            current_price: Current market price
        """
        # Sum realized P&L from completed levels
        self.realized_pnl = sum(
            (lvl.realized_pnl for lvl in self.levels if lvl.is_complete),
            Decimal("0"),
        )
        self.total_commission = sum(
            (lvl.commission for lvl in self.levels),
            Decimal("0"),
        )

        # Calculate unrealized P&L from open positions (buy filled but not sold)
        self.unrealized_pnl = Decimal("0")
        for level in self.levels:
            if level.status == GridLevelStatus.BUY_FILLED and level.buy_fill_price:
                unrealized = (current_price - level.buy_fill_price) * level.quantity
                self.unrealized_pnl += unrealized

    def record_trade(self, pnl: Decimal) -> None:
        """Record a completed trade for statistics."""
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        elif pnl < 0:
            self.losing_trades += 1

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "symbol": self.symbol,
            "status": self.status.value,
            "entry_price": str(self.entry_price),
            "upper_bound": str(self.upper_bound),
            "lower_bound": str(self.lower_bound),
            "grid_spacing": str(self.grid_spacing),
            "atr_value": str(self.atr_value),
            "allocated_capital": str(self.allocated_capital),
            "order_size_per_level": str(self.order_size_per_level),
            "levels": [lvl.to_dict() for lvl in self.levels],
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "max_duration_hours": self.max_duration_hours,
            "realized_pnl": str(self.realized_pnl),
            "unrealized_pnl": str(self.unrealized_pnl),
            "total_commission": str(self.total_commission),
            "stop_loss_price": str(self.stop_loss_price),
            "take_profit_pnl": str(self.take_profit_pnl),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "fill_rate": str(self.fill_rate),
            "win_rate": str(self.win_rate),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GridSession":
        """Create GridSession from dictionary."""
        session = cls(
            session_id=data["session_id"],
            symbol=data["symbol"],
            status=GridStatus(data["status"]),
            entry_price=Decimal(data["entry_price"]),
            upper_bound=Decimal(data["upper_bound"]),
            lower_bound=Decimal(data["lower_bound"]),
            grid_spacing=Decimal(data["grid_spacing"]),
            atr_value=Decimal(data["atr_value"]),
            allocated_capital=Decimal(data["allocated_capital"]),
            order_size_per_level=Decimal(data["order_size_per_level"]),
            max_duration_hours=data["max_duration_hours"],
            realized_pnl=Decimal(data["realized_pnl"]),
            unrealized_pnl=Decimal(data["unrealized_pnl"]),
            total_commission=Decimal(data["total_commission"]),
            stop_loss_price=Decimal(data["stop_loss_price"]),
            take_profit_pnl=Decimal(data["take_profit_pnl"]),
            total_trades=data["total_trades"],
            winning_trades=data["winning_trades"],
            losing_trades=data["losing_trades"],
        )

        # Parse timestamps
        session.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            session.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("ended_at"):
            session.ended_at = datetime.fromisoformat(data["ended_at"])

        # Parse levels
        for lvl_data in data.get("levels", []):
            level = GridLevel(
                level_id=lvl_data["level_id"],
                level_index=lvl_data["level_index"],
                side=GridSide(lvl_data["side"]),
                price=Decimal(lvl_data["price"]),
                quantity=Decimal(lvl_data["quantity"]),
                order_id=lvl_data.get("order_id"),
                exchange_order_id=lvl_data.get("exchange_order_id"),
                status=GridLevelStatus(lvl_data["status"]),
                realized_pnl=Decimal(lvl_data["realized_pnl"]),
                commission=Decimal(lvl_data["commission"]),
            )
            if lvl_data.get("buy_fill_price"):
                level.buy_fill_price = Decimal(lvl_data["buy_fill_price"])
            if lvl_data.get("buy_fill_time"):
                level.buy_fill_time = datetime.fromisoformat(lvl_data["buy_fill_time"])
            if lvl_data.get("sell_fill_price"):
                level.sell_fill_price = Decimal(lvl_data["sell_fill_price"])
            if lvl_data.get("sell_fill_time"):
                level.sell_fill_time = datetime.fromisoformat(
                    lvl_data["sell_fill_time"]
                )
            session.levels.append(level)

        return session
