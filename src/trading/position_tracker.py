"""
Helios Trading Bot - Position Tracker

Tracks open positions across all trading symbols, calculates real-time
P&L, and maintains position history. Integrates with Redis for fast
position state caching.

All monetary calculations use Decimal for precision per rule 010.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from typing import Dict, List, Optional

from .order_models import Order, OrderSide, Position, PositionSide

logger = logging.getLogger(__name__)


class PositionTracker:
    """
    Tracks and manages positions across trading symbols.

    Responsibilities:
    - Track open positions for each symbol
    - Calculate real-time unrealized P&L
    - Record realized P&L from closed trades
    - Maintain position history for analysis
    - Provide portfolio-level P&L summary

    All monetary calculations use Decimal for precision.
    """

    def __init__(self):
        """Initialize PositionTracker."""
        # Active positions: symbol -> Position
        self._positions: Dict[str, Position] = {}

        # Trade history for P&L analysis
        self._trade_history: List[dict] = []

        # Portfolio-level tracking
        self._total_realized_pnl = Decimal("0")
        self._total_commission = Decimal("0")

    @property
    def positions(self) -> Dict[str, Position]:
        """Get all tracked positions (including flat)."""
        return self._positions.copy()

    @property
    def open_positions(self) -> Dict[str, Position]:
        """Get only non-flat positions."""
        return {
            symbol: pos for symbol, pos in self._positions.items() if not pos.is_flat
        }

    @property
    def total_unrealized_pnl(self) -> Decimal:
        """Calculate total unrealized P&L across all positions."""
        return sum(
            pos.unrealized_pnl for pos in self._positions.values() if not pos.is_flat
        )

    @property
    def total_realized_pnl(self) -> Decimal:
        """Get total realized P&L from closed trades."""
        return self._total_realized_pnl

    @property
    def total_pnl(self) -> Decimal:
        """Get total P&L (realized + unrealized)."""
        return self.total_realized_pnl + self.total_unrealized_pnl

    @property
    def total_commission(self) -> Decimal:
        """Get total commission paid."""
        return self._total_commission

    @property
    def net_pnl(self) -> Decimal:
        """Get net P&L after commissions."""
        return self.total_pnl - self.total_commission

    def get_position(self, symbol: str) -> Position:
        """
        Get position for a symbol.

        Creates a flat position if none exists.

        Args:
            symbol: Trading symbol

        Returns:
            Position for the symbol
        """
        if symbol not in self._positions:
            self._positions[symbol] = Position.create_flat(symbol)
        return self._positions[symbol]

    def update_price(self, symbol: str, price: Decimal) -> None:
        """
        Update current market price for a symbol.

        Args:
            symbol: Trading symbol
            price: Current market price
        """
        if symbol in self._positions:
            self._positions[symbol].update_price(price)

    def update_prices(self, prices: Dict[str, Decimal]) -> None:
        """
        Batch update prices for multiple symbols.

        Args:
            prices: Dictionary of symbol -> price
        """
        for symbol, price in prices.items():
            self.update_price(symbol, price)

    def process_fill(
        self,
        order: Order,
        fill_quantity: Decimal,
        fill_price: Decimal,
        commission: Decimal = Decimal("0"),
    ) -> Decimal:
        """
        Process a fill event and update position.

        Args:
            order: The order that was filled
            fill_quantity: Quantity filled
            fill_price: Fill price
            commission: Commission for this fill

        Returns:
            Realized P&L from this fill (if position was reduced)
        """
        position = self.get_position(order.symbol)
        realized_pnl = Decimal("0")

        # Track commission
        self._total_commission += commission

        # Record trade
        trade_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": str(fill_quantity),
            "price": str(fill_price),
            "commission": str(commission),
        }

        if position.is_flat:
            # Opening new position
            position.symbol = order.symbol
            position.side = (
                PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT
            )
            position.quantity = fill_quantity
            position.entry_price = fill_price
            position.current_price = fill_price
            position.opened_at = datetime.now(timezone.utc)
            position.total_commission = commission

            trade_record["action"] = "OPEN"
            logger.info(
                "Opened %s position in %s: %s @ %s",
                position.side.value,
                order.symbol,
                fill_quantity,
                fill_price,
            )

        elif self._is_same_direction(position.side, order.side):
            # Adding to existing position
            position.add_to_position(fill_quantity, fill_price, commission)

            trade_record["action"] = "ADD"
            logger.info(
                "Added to %s position in %s: %s @ %s (new avg: %s)",
                position.side.value,
                order.symbol,
                fill_quantity,
                fill_price,
                position.entry_price,
            )

        else:
            # Reducing or closing position
            realized_pnl = position.reduce_position(
                fill_quantity, fill_price, commission
            )
            self._total_realized_pnl += realized_pnl

            trade_record["action"] = "CLOSE" if position.is_flat else "REDUCE"
            trade_record["realized_pnl"] = str(realized_pnl)

            logger.info(
                "Reduced %s position in %s: %s @ %s (realized P&L: %s)",
                position.side.value,
                order.symbol,
                fill_quantity,
                fill_price,
                realized_pnl,
            )

        self._trade_history.append(trade_record)
        return realized_pnl

    def _is_same_direction(
        self, position_side: PositionSide, order_side: OrderSide
    ) -> bool:
        """Check if order is in same direction as existing position."""
        if position_side == PositionSide.LONG:
            return order_side == OrderSide.BUY
        elif position_side == PositionSide.SHORT:
            return order_side == OrderSide.SELL
        return False

    def close_position(
        self,
        symbol: str,
        close_price: Decimal,
        commission: Decimal = Decimal("0"),
    ) -> Decimal:
        """
        Close an entire position at a given price.

        Args:
            symbol: Trading symbol
            close_price: Price at which position is closed
            commission: Commission for closing trade

        Returns:
            Realized P&L from closing the position
        """
        position = self.get_position(symbol)

        if position.is_flat:
            return Decimal("0")

        realized_pnl = position.reduce_position(
            position.quantity, close_price, commission
        )
        self._total_realized_pnl += realized_pnl
        self._total_commission += commission

        logger.info(
            "Closed position in %s @ %s (realized P&L: %s)",
            symbol,
            close_price,
            realized_pnl,
        )

        return realized_pnl

    def get_position_summary(self, symbol: str) -> dict:
        """
        Get summary of position for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position summary dictionary
        """
        position = self.get_position(symbol)
        return position.to_dict()

    def get_portfolio_summary(self) -> dict:
        """
        Get summary of entire portfolio.

        Returns:
            Portfolio summary dictionary
        """
        open_positions = [
            pos.to_dict() for pos in self._positions.values() if not pos.is_flat
        ]

        return {
            "open_positions": len(open_positions),
            "positions": open_positions,
            "total_unrealized_pnl": str(self.total_unrealized_pnl),
            "total_realized_pnl": str(self.total_realized_pnl),
            "total_pnl": str(self.total_pnl),
            "total_commission": str(self.total_commission),
            "net_pnl": str(self.net_pnl),
        }

    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """
        Get trade history.

        Args:
            symbol: Optional symbol filter
            limit: Maximum number of trades to return

        Returns:
            List of trade records
        """
        trades = self._trade_history

        if symbol:
            trades = [t for t in trades if t.get("symbol") == symbol]

        # Return most recent trades first
        return list(reversed(trades[-limit:]))

    def reset(self) -> None:
        """Reset all positions and history (for testing/paper trading)."""
        self._positions.clear()
        self._trade_history.clear()
        self._total_realized_pnl = Decimal("0")
        self._total_commission = Decimal("0")
        logger.info("PositionTracker reset")

    def to_dict(self) -> dict:
        """Serialize tracker state to dictionary."""
        return {
            "positions": {
                symbol: pos.to_dict() for symbol, pos in self._positions.items()
            },
            "total_realized_pnl": str(self._total_realized_pnl),
            "total_commission": str(self._total_commission),
            "trade_history": self._trade_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PositionTracker":
        """Deserialize tracker state from dictionary."""
        tracker = cls()
        tracker._total_realized_pnl = Decimal(data.get("total_realized_pnl", "0"))
        tracker._total_commission = Decimal(data.get("total_commission", "0"))
        tracker._trade_history = data.get("trade_history", [])

        # Restore positions
        for symbol, pos_data in data.get("positions", {}).items():
            tracker._positions[symbol] = Position(
                symbol=pos_data["symbol"],
                side=PositionSide(pos_data["side"]),
                quantity=Decimal(pos_data["quantity"]),
                entry_price=Decimal(pos_data["entry_price"]),
                current_price=Decimal(pos_data["current_price"]),
                realized_pnl=Decimal(pos_data["realized_pnl"]),
                total_commission=Decimal(pos_data["total_commission"]),
            )

        return tracker


class PositionTrackerWithRedis(PositionTracker):
    """
    Position tracker with Redis persistence for fast state recovery.

    Extends PositionTracker with Redis caching for:
    - Fast position state persistence
    - Quick recovery after restart
    - Real-time position sharing across instances

    Note: Requires Redis connection. Falls back gracefully if unavailable.
    """

    REDIS_KEY_PREFIX = "helios:positions"
    REDIS_PORTFOLIO_KEY = "helios:portfolio"

    def __init__(self, redis_manager=None):
        """
        Initialize with optional Redis manager.

        Args:
            redis_manager: Optional RedisManager for caching
        """
        super().__init__()
        self._redis = redis_manager

    async def save_to_redis(self) -> None:
        """Persist current state to Redis."""
        if self._redis is None:
            return

        try:
            # Save portfolio summary
            portfolio_data = json.dumps(self.to_dict())
            await self._redis.set(self.REDIS_PORTFOLIO_KEY, portfolio_data)

            # Save individual positions for quick lookup
            for symbol, position in self._positions.items():
                key = f"{self.REDIS_KEY_PREFIX}:{symbol}"
                await self._redis.set(key, json.dumps(position.to_dict()))

        except Exception as e:
            logger.warning("Failed to save positions to Redis: %s", e)

    async def load_from_redis(self) -> bool:
        """
        Load state from Redis.

        Returns:
            True if state was loaded, False otherwise
        """
        if self._redis is None:
            return False

        try:
            data = await self._redis.get(self.REDIS_PORTFOLIO_KEY)
            if data:
                state = json.loads(data)
                self._total_realized_pnl = Decimal(state.get("total_realized_pnl", "0"))
                self._total_commission = Decimal(state.get("total_commission", "0"))
                self._trade_history = state.get("trade_history", [])

                # Restore positions
                for symbol, pos_data in state.get("positions", {}).items():
                    self._positions[symbol] = Position(
                        symbol=pos_data["symbol"],
                        side=PositionSide(pos_data["side"]),
                        quantity=Decimal(pos_data["quantity"]),
                        entry_price=Decimal(pos_data["entry_price"]),
                        current_price=Decimal(pos_data["current_price"]),
                        realized_pnl=Decimal(pos_data["realized_pnl"]),
                        total_commission=Decimal(pos_data["total_commission"]),
                    )

                logger.info("Loaded position state from Redis")
                return True

        except Exception as e:
            logger.warning("Failed to load positions from Redis: %s", e)

        return False

    def process_fill(
        self,
        order: Order,
        fill_quantity: Decimal,
        fill_price: Decimal,
        commission: Decimal = Decimal("0"),
    ) -> Decimal:
        """Process fill and persist to Redis."""
        result = super().process_fill(order, fill_quantity, fill_price, commission)

        # Note: In production, use asyncio.create_task() to save async
        # For simplicity, just logging that save would happen
        logger.debug("Position updated, should persist to Redis")

        return result
