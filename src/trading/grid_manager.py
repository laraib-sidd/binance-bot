"""
Helios Trading Bot - Grid Manager

Manages grid trading sessions: deploying order ladders, handling fills,
and monitoring session status. Integrates with OrderManager for execution
and PositionTracker for P&L.

This is the core orchestrator for the Signal-Driven Dynamic Grid strategy.
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional

from .exceptions import OrderExecutionError, OrderValidationError
from .grid_calculator import GridCalculator
from .grid_models import (
    GridConfig,
    GridLevel,
    GridLevelStatus,
    GridSession,
    GridStatus,
)
from .order_manager import OrderManager
from .order_models import Order, OrderSide, OrderType

logger = logging.getLogger(__name__)


class GridManagerError(Exception):
    """Base exception for grid manager errors."""

    pass


class GridSessionNotFoundError(GridManagerError):
    """Raised when a grid session is not found."""

    pass


class GridDeploymentError(GridManagerError):
    """Raised when grid deployment fails."""

    pass


class GridManager:
    """
    Manages grid trading sessions.

    Responsibilities:
    - Deploy grid orders based on calculated parameters
    - Monitor and handle order fills
    - Place corresponding profit-taking orders
    - Track session P&L and statistics
    - Enforce session stop-loss and take-profit
    """

    def __init__(
        self,
        order_manager: OrderManager,
        default_config: Optional[GridConfig] = None,
    ):
        """
        Initialize GridManager.

        Args:
            order_manager: OrderManager for order execution
            default_config: Default grid configuration
        """
        self._order_manager = order_manager
        self._default_config = default_config or GridConfig(symbol="BTCUSDT")

        # Active sessions by session_id
        self._sessions: Dict[str, GridSession] = {}

        # Mapping from order_id to (session_id, level_id)
        self._order_to_level: Dict[str, tuple[str, str]] = {}

        logger.info("GridManager initialized")

    @property
    def active_sessions(self) -> List[GridSession]:
        """Get all active grid sessions."""
        return [s for s in self._sessions.values() if s.is_active]

    @property
    def all_sessions(self) -> List[GridSession]:
        """Get all grid sessions."""
        return list(self._sessions.values())

    def get_session(self, session_id: str) -> GridSession:
        """Get a specific grid session by ID."""
        if session_id not in self._sessions:
            raise GridSessionNotFoundError(f"Session not found: {session_id}")
        return self._sessions[session_id]

    async def create_session(
        self,
        symbol: str,
        current_price: Decimal,
        atr_value: Decimal,
        available_capital: Decimal,
        config: Optional[GridConfig] = None,
        price_precision: int = 2,
        quantity_precision: int = 5,
    ) -> GridSession:
        """
        Create a new grid session (but don't deploy yet).

        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            atr_value: Current ATR value
            available_capital: Capital available for grid
            config: Optional custom grid config
            price_precision: Exchange price precision
            quantity_precision: Exchange quantity precision

        Returns:
            Created GridSession (status: PENDING)
        """
        grid_config = config or self._default_config
        grid_config.symbol = symbol

        calculator = GridCalculator(grid_config)
        result = calculator.calculate_grid(
            current_price=current_price,
            atr_value=atr_value,
            available_capital=available_capital,
            price_precision=price_precision,
            quantity_precision=quantity_precision,
        )

        if not result.success or not result.session:
            raise GridDeploymentError(
                f"Failed to calculate grid: {result.error_message}"
            )

        session = result.session
        self._sessions[session.session_id] = session

        logger.info(
            "Created grid session %s: %d levels, range [%s - %s]",
            session.session_id[:8],
            len(session.levels),
            session.lower_bound,
            session.upper_bound,
        )

        return session

    async def deploy_session(self, session_id: str) -> GridSession:
        """
        Deploy a pending grid session by placing all orders.

        Args:
            session_id: ID of the session to deploy

        Returns:
            Updated GridSession with orders placed
        """
        session = self.get_session(session_id)

        if session.status != GridStatus.PENDING:
            raise GridDeploymentError(
                f"Session {session_id} is not pending (status: {session.status.value})"
            )

        logger.info("Deploying grid session %s", session_id[:8])

        # Place buy orders for all buy levels
        deployed_count = 0
        failed_count = 0

        for level in session.buy_levels:
            try:
                order = await self._place_grid_order(
                    session=session,
                    level=level,
                    side=OrderSide.BUY,
                )
                level.order_id = order.order_id
                level.exchange_order_id = order.exchange_order_id
                level.status = GridLevelStatus.OPEN

                # Track order to level mapping
                self._order_to_level[order.order_id] = (
                    session.session_id,
                    level.level_id,
                )
                deployed_count += 1

            except (OrderValidationError, OrderExecutionError) as e:
                logger.warning(
                    "Failed to place order for level %s: %s", level.level_id, e
                )
                level.status = GridLevelStatus.CANCELLED
                failed_count += 1

        if deployed_count == 0:
            raise GridDeploymentError("Failed to deploy any grid orders")

        # Start the session
        session.start()

        logger.info(
            "Deployed grid session %s: %d orders placed, %d failed",
            session_id[:8],
            deployed_count,
            failed_count,
        )

        return session

    async def _place_grid_order(
        self,
        session: GridSession,
        level: GridLevel,
        side: OrderSide,
    ) -> Order:
        """Place an order for a grid level."""
        order = await self._order_manager.place_order(
            symbol=session.symbol,
            side=side,
            quantity=level.quantity,
            order_type=OrderType.LIMIT,
            price=level.price,
        )
        return order

    async def handle_order_fill(
        self,
        order_id: str,
        fill_price: Decimal,
        fill_quantity: Decimal,
        commission: Decimal = Decimal("0"),
    ) -> Optional[Order]:
        """
        Handle an order fill event.

        When a buy order fills, place corresponding sell order.
        When a sell order fills, record the profit.

        Args:
            order_id: The order that was filled
            fill_price: Actual fill price
            fill_quantity: Actual fill quantity
            commission: Commission charged

        Returns:
            New sell order if buy was filled, None otherwise
        """
        # Find the session and level for this order
        if order_id not in self._order_to_level:
            logger.warning("Order %s not found in grid tracking", order_id)
            return None

        session_id, level_id = self._order_to_level[order_id]
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("Session %s not found for order %s", session_id, order_id)
            return None

        # Find the level
        level = next((lvl for lvl in session.levels if lvl.level_id == level_id), None)
        if not level:
            logger.warning("Level %s not found in session %s", level_id, session_id)
            return None

        fill_time = datetime.now(timezone.utc)

        if level.status == GridLevelStatus.OPEN:
            # This is a buy order fill
            level.mark_buy_filled(fill_price, fill_time)
            logger.info(
                "Grid buy filled: session=%s, level=%s, price=%s",
                session_id[:8],
                level.level_index,
                fill_price,
            )

            # Place corresponding sell order (with profit target)
            try:
                sell_price = self._calculate_sell_price(
                    buy_price=fill_price,
                    grid_spacing=session.grid_spacing,
                )
                sell_order = await self._order_manager.place_order(
                    symbol=session.symbol,
                    side=OrderSide.SELL,
                    quantity=level.quantity,
                    order_type=OrderType.LIMIT,
                    price=sell_price,
                )

                level.order_id = sell_order.order_id
                level.exchange_order_id = sell_order.exchange_order_id

                # Update tracking
                self._order_to_level[sell_order.order_id] = (session_id, level_id)

                logger.info(
                    "Grid sell placed: session=%s, level=%s, price=%s",
                    session_id[:8],
                    level.level_index,
                    sell_price,
                )
                return sell_order

            except (OrderValidationError, OrderExecutionError) as e:
                logger.error("Failed to place sell order: %s", e)
                return None

        elif level.status == GridLevelStatus.BUY_FILLED:
            # This is a sell order fill - complete the cycle
            pnl = level.mark_sell_filled(fill_price, fill_time, commission)
            session.record_trade(pnl)
            session.update_pnl(fill_price)

            logger.info(
                "Grid cycle complete: session=%s, level=%s, pnl=%s",
                session_id[:8],
                level.level_index,
                pnl,
            )

            # Check if take-profit target reached
            if session.realized_pnl >= session.take_profit_pnl:
                logger.info(
                    "Take-profit target reached: %s >= %s",
                    session.realized_pnl,
                    session.take_profit_pnl,
                )
                await self.stop_session(session_id, "Take-profit target reached")

            return None

        return None

    def _calculate_sell_price(
        self, buy_price: Decimal, grid_spacing: Decimal
    ) -> Decimal:
        """Calculate sell price for a filled buy order."""
        # Sell at one grid spacing above buy price (capturing the grid profit)
        return buy_price + grid_spacing

    async def check_session_conditions(
        self, session_id: str, current_price: Decimal
    ) -> Dict[str, Any]:
        """
        Check session conditions and determine if any action needed.

        Returns:
            Dict with status and any required actions
        """
        session = self.get_session(session_id)
        result: Dict[str, Any] = {
            "session_id": session_id,
            "status": session.status.value,
            "actions": [],
        }

        if not session.is_active:
            return result

        # Update P&L
        session.update_pnl(current_price)
        result["current_pnl"] = str(session.total_pnl)

        # Check expiration
        if session.is_expired:
            result["actions"].append("expire")
            await self.stop_session(session_id, "Session expired")
            result["status"] = GridStatus.EXPIRED.value
            return result

        # Check stop-loss
        if current_price <= session.stop_loss_price:
            result["actions"].append("stop_loss")
            await self.stop_session(session_id, "Stop-loss triggered")
            result["status"] = GridStatus.STOPPED.value
            return result

        # Check take-profit
        if session.realized_pnl >= session.take_profit_pnl:
            result["actions"].append("take_profit")
            await self.stop_session(session_id, "Take-profit reached")
            result["status"] = GridStatus.COMPLETED.value
            return result

        # Check if all levels completed
        if len(session.completed_levels) == len(session.buy_levels):
            result["actions"].append("all_filled")
            session.complete()
            result["status"] = GridStatus.COMPLETED.value
            return result

        return result

    async def stop_session(self, session_id: str, reason: str = "") -> GridSession:
        """
        Stop a grid session and cancel all open orders.

        Args:
            session_id: Session to stop
            reason: Reason for stopping

        Returns:
            Updated GridSession
        """
        session = self.get_session(session_id)

        if not session.is_active:
            logger.warning("Session %s is not active", session_id[:8])
            return session

        logger.info("Stopping grid session %s: %s", session_id[:8], reason)

        # Cancel all open orders
        cancelled_count = 0
        for level in session.levels:
            if level.is_active and level.order_id:
                try:
                    await self._order_manager.cancel_order(level.order_id)
                    level.status = GridLevelStatus.CANCELLED
                    cancelled_count += 1
                except Exception as e:
                    logger.warning("Failed to cancel order %s: %s", level.order_id, e)

        session.stop(reason)

        logger.info(
            "Stopped grid session %s: cancelled %d orders, P&L: %s",
            session_id[:8],
            cancelled_count,
            session.total_pnl,
        )

        return session

    async def stop_all_sessions(self, reason: str = "Manual stop") -> int:
        """
        Stop all active grid sessions.

        Returns:
            Number of sessions stopped
        """
        stopped = 0
        for session in self.active_sessions:
            await self.stop_session(session.session_id, reason)
            stopped += 1
        return stopped

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of a grid session."""
        session = self.get_session(session_id)
        return {
            "session_id": session.session_id,
            "symbol": session.symbol,
            "status": session.status.value,
            "entry_price": str(session.entry_price),
            "grid_range": f"{session.lower_bound} - {session.upper_bound}",
            "grid_spacing": str(session.grid_spacing),
            "levels_total": len(session.levels),
            "levels_completed": len(session.completed_levels),
            "levels_active": len(session.active_levels),
            "fill_rate": f"{session.fill_rate:.1f}%",
            "realized_pnl": str(session.realized_pnl),
            "unrealized_pnl": str(session.unrealized_pnl),
            "total_pnl": str(session.total_pnl),
            "win_rate": f"{session.win_rate:.1f}%",
            "total_trades": session.total_trades,
            "duration": str(
                (session.ended_at or datetime.now(timezone.utc)) - session.created_at
            ),
        }

    def get_all_sessions_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all sessions."""
        return [self.get_session_summary(session_id) for session_id in self._sessions]
