"""
Helios Trading Bot - Grid Calculator

Calculates dynamic grid parameters based on market volatility (ATR).
Determines optimal grid bounds, spacing, and position sizes for each session.

The calculator adapts grid configuration to current market conditions,
ensuring grids are appropriately sized for the volatility environment.
"""

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
import logging
from typing import Optional

from .grid_models import GridConfig, GridLevel, GridSession, GridSide

logger = logging.getLogger(__name__)


@dataclass
class GridCalculationResult:
    """Result of grid parameter calculation."""

    success: bool
    session: Optional[GridSession] = None
    error_message: Optional[str] = None


class GridCalculator:
    """
    Calculates dynamic grid parameters based on volatility.

    Uses ATR (Average True Range) to determine:
    - Grid upper and lower bounds
    - Spacing between grid levels
    - Position size per level
    - Stop-loss and take-profit levels
    """

    def __init__(self, config: GridConfig):
        """
        Initialize GridCalculator.

        Args:
            config: Grid configuration parameters
        """
        self.config = config

    def calculate_grid(
        self,
        current_price: Decimal,
        atr_value: Decimal,
        available_capital: Decimal,
        price_precision: int = 2,
        quantity_precision: int = 5,
    ) -> GridCalculationResult:
        """
        Calculate complete grid parameters for a trading session.

        Args:
            current_price: Current market price of the asset
            atr_value: Current ATR (14-period recommended)
            available_capital: Capital available for this grid session
            price_precision: Decimal places for price (from exchange)
            quantity_precision: Decimal places for quantity (from exchange)

        Returns:
            GridCalculationResult with session or error
        """
        try:
            # Validate inputs
            if current_price <= 0:
                return GridCalculationResult(
                    success=False, error_message="Current price must be positive"
                )
            if atr_value <= 0:
                return GridCalculationResult(
                    success=False, error_message="ATR value must be positive"
                )
            if available_capital <= 0:
                return GridCalculationResult(
                    success=False, error_message="Available capital must be positive"
                )

            # Calculate grid range based on ATR
            grid_range = atr_value * self.config.range_multiplier
            upper_bound = current_price + grid_range
            lower_bound = current_price - grid_range

            # Ensure lower bound is positive
            if lower_bound <= 0:
                lower_bound = current_price * Decimal("0.5")
                logger.warning(
                    "Adjusted lower bound to prevent negative price: %s", lower_bound
                )

            # Calculate grid spacing
            total_range = upper_bound - lower_bound
            grid_spacing = total_range / Decimal(str(self.config.grid_levels))

            # Validate spacing against min/max constraints
            spacing_percent = grid_spacing / current_price
            if spacing_percent < self.config.min_spacing_percent:
                return GridCalculationResult(
                    success=False,
                    error_message=f"Grid spacing too small: {spacing_percent:.4%} "
                    f"(min: {self.config.min_spacing_percent:.4%})",
                )
            if spacing_percent > self.config.max_spacing_percent:
                return GridCalculationResult(
                    success=False,
                    error_message=f"Grid spacing too large: {spacing_percent:.4%} "
                    f"(max: {self.config.max_spacing_percent:.4%})",
                )

            # Calculate capital allocation
            session_capital = min(
                available_capital * self.config.risk_per_session,
                available_capital * self.config.max_position_size,
            )

            # Split capital across buy levels only (we sell what we buy)
            buy_levels_count = self.config.grid_levels // 2
            capital_per_level = session_capital / Decimal(str(buy_levels_count))

            # Calculate quantity per level (based on approximate mid-price)
            mid_price = (upper_bound + lower_bound) / 2
            quantity_per_level = capital_per_level / mid_price

            # Round to exchange precision
            quantity_per_level = self._round_to_precision(
                quantity_per_level, quantity_precision
            )

            # Create grid session
            session = GridSession(
                symbol=self.config.symbol,
                entry_price=self._round_to_precision(current_price, price_precision),
                upper_bound=self._round_to_precision(upper_bound, price_precision),
                lower_bound=self._round_to_precision(lower_bound, price_precision),
                grid_spacing=self._round_to_precision(grid_spacing, price_precision),
                atr_value=atr_value,
                allocated_capital=session_capital,
                order_size_per_level=quantity_per_level,
                max_duration_hours=self.config.max_session_duration_hours,
            )

            # Calculate stop-loss (below lower bound)
            session.stop_loss_price = self._round_to_precision(
                lower_bound * (1 - self.config.stop_loss_percent), price_precision
            )

            # Calculate take-profit P&L target
            session.take_profit_pnl = session_capital * self.config.take_profit_percent

            # Generate grid levels
            session.levels = self._generate_levels(
                current_price=current_price,
                upper_bound=upper_bound,
                lower_bound=lower_bound,
                grid_spacing=grid_spacing,
                quantity_per_level=quantity_per_level,
                price_precision=price_precision,
            )

            logger.info(
                "Grid calculated: %s levels, range [%s - %s], spacing %s",
                len(session.levels),
                session.lower_bound,
                session.upper_bound,
                session.grid_spacing,
            )

            return GridCalculationResult(success=True, session=session)

        except Exception as e:
            logger.exception("Failed to calculate grid: %s", e)
            return GridCalculationResult(
                success=False, error_message=f"Grid calculation failed: {e}"
            )

    def _generate_levels(
        self,
        current_price: Decimal,
        upper_bound: Decimal,
        lower_bound: Decimal,
        grid_spacing: Decimal,
        quantity_per_level: Decimal,
        price_precision: int,
    ) -> list[GridLevel]:
        """
        Generate individual grid levels.

        Buy levels are placed below current price (descending).
        Sell levels are placed above current price (ascending).
        """
        levels: list[GridLevel] = []
        buy_levels_count = self.config.grid_levels // 2
        sell_levels_count = self.config.grid_levels // 2

        # Generate buy levels (below current price)
        for i in range(buy_levels_count):
            # Level 0 is closest to current price
            price = current_price - (grid_spacing * Decimal(str(i + 1)))
            if price < lower_bound:
                price = lower_bound

            level = GridLevel(
                level_index=i,
                side=GridSide.BUY,
                price=self._round_to_precision(price, price_precision),
                quantity=quantity_per_level,
            )
            levels.append(level)

        # Generate sell levels (above current price)
        for i in range(sell_levels_count):
            # Level 0 is closest to current price
            price = current_price + (grid_spacing * Decimal(str(i + 1)))
            if price > upper_bound:
                price = upper_bound

            level = GridLevel(
                level_index=i,
                side=GridSide.SELL,
                price=self._round_to_precision(price, price_precision),
                quantity=quantity_per_level,
            )
            levels.append(level)

        return levels

    def recalculate_spacing(
        self,
        session: GridSession,
        new_atr: Decimal,
        current_price: Decimal,
    ) -> bool:
        """
        Check if grid should be recalculated due to volatility change.

        Returns True if volatility has changed significantly (>50%)
        and grid recalculation is recommended.

        Note: This does not modify the session, just provides a recommendation.
        """
        if session.atr_value == 0:
            return False

        atr_change = abs(new_atr - session.atr_value) / session.atr_value

        # Recommend recalculation if ATR changed by more than 50%
        if atr_change > Decimal("0.5"):
            logger.info(
                "ATR changed significantly: %.2f%% - recalculation recommended",
                float(atr_change * 100),
            )
            return True

        # Also check if price has moved outside grid bounds
        if current_price < session.lower_bound or current_price > session.upper_bound:
            logger.info("Price moved outside grid bounds - recalculation recommended")
            return True

        return False

    def calculate_profit_target_price(
        self, buy_price: Decimal, target_percent: Decimal = Decimal("0.01")
    ) -> Decimal:
        """
        Calculate the sell price for a grid level to achieve target profit.

        Args:
            buy_price: The price at which the buy order filled
            target_percent: Target profit percentage (default 1%)

        Returns:
            Target sell price
        """
        return buy_price * (1 + target_percent)

    @staticmethod
    def _round_to_precision(value: Decimal, precision: int) -> Decimal:
        """Round a Decimal to the specified number of decimal places."""
        if precision <= 0:
            return value.quantize(Decimal("1"), rounding=ROUND_DOWN)
        quantizer = Decimal(10) ** -precision
        return value.quantize(quantizer, rounding=ROUND_DOWN)


def calculate_atr_based_grid(
    symbol: str,
    current_price: Decimal,
    atr_14: Decimal,
    available_capital: Decimal,
    grid_levels: int = 8,
    range_multiplier: Decimal = Decimal("2.0"),
    price_precision: int = 2,
    quantity_precision: int = 5,
) -> GridCalculationResult:
    """
    Convenience function to calculate a grid with default settings.

    Args:
        symbol: Trading pair symbol
        current_price: Current market price
        atr_14: 14-period ATR value
        available_capital: Capital available for trading
        grid_levels: Number of grid levels (default 8)
        range_multiplier: ATR multiplier for range (default 2.0)
        price_precision: Exchange price precision
        quantity_precision: Exchange quantity precision

    Returns:
        GridCalculationResult with session or error
    """
    config = GridConfig(
        symbol=symbol,
        grid_levels=grid_levels,
        range_multiplier=range_multiplier,
    )

    calculator = GridCalculator(config)
    return calculator.calculate_grid(
        current_price=current_price,
        atr_value=atr_14,
        available_capital=available_capital,
        price_precision=price_precision,
        quantity_precision=quantity_precision,
    )
