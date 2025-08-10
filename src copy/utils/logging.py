"""
Helios Trading Bot - Comprehensive Logging System

This module provides a robust logging framework for the Helios trading bot,
including structured logging, multiple output formats, log rotation, and
trading-specific logging features.

Features:
- Structured logging with JSON output
- Multiple log levels and handlers
- Trading-specific log formatters
- Log rotation and archiving
- Performance monitoring
- Security-aware logging (no sensitive data)
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
import json
import logging
import logging.handlers
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Union

# Import configuration if available
try:
    from ..core.config import TradingConfig, get_config

    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


@dataclass
class LogEntry:
    """Structured log entry for trading operations."""

    timestamp: str
    level: str
    logger: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    trading_pair: Optional[str] = None
    order_id: Optional[str] = None
    price: Optional[str] = None  # String to avoid Decimal serialization issues
    quantity: Optional[str] = None
    side: Optional[str] = None  # 'BUY' or 'SELL'
    strategy: Optional[str] = None
    session_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


class TradingLogFormatter(logging.Formatter):
    """Custom log formatter for trading operations."""

    def __init__(self, format_type: str = "standard"):
        self.format_type = format_type

        if format_type == "json":
            super().__init__()
        elif format_type == "compact":
            super().__init__(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        else:  # standard
            super().__init__(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record."""
        if self.format_type == "json":
            return self._format_json(record)
        else:
            return super().format(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": getattr(record, "module", None),
            "function": getattr(record, "funcName", None),
            "filename": record.filename,
            "line_number": record.lineno,
        }

        # Add trading-specific fields if present
        trading_fields = [
            "trading_pair",
            "order_id",
            "price",
            "quantity",
            "side",
            "strategy",
            "session_id",
            "extra_data",
        ]

        for field in trading_fields:
            if hasattr(record, field):
                value = getattr(record, field)
                if value is not None:
                    log_data[field] = (
                        str(value) if isinstance(value, Decimal) else value
                    )

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, separators=(",", ":"))


class TradingLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for trading operations with context."""

    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]):
        super().__init__(logger, extra)
        self.session_id = extra.get("session_id")
        self.strategy = extra.get("strategy")

    def process(self, msg: str, kwargs: Any) -> Any:
        """Process log message and add trading context."""
        # Add session context to extra
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        kwargs["extra"].update(self.extra)

        return msg, kwargs

    def trading_action(
        self,
        action: str,
        trading_pair: str,
        price: Optional[Union[Decimal, float, str]] = None,
        quantity: Optional[Union[Decimal, float, str]] = None,
        side: Optional[str] = None,
        order_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log trading-specific action."""
        extra = {
            "trading_pair": trading_pair,
            "price": str(price) if price is not None else None,
            "quantity": str(quantity) if quantity is not None else None,
            "side": side,
            "order_id": order_id,
        }
        extra.update(kwargs)

        self.info(f"Trading Action: {action}", extra=extra)

    def market_data(
        self,
        trading_pair: str,
        price: Union[Decimal, float, str],
        volume: Optional[Union[Decimal, float, str]] = None,
        **kwargs: Any,
    ) -> None:
        """Log market data update."""
        extra = {
            "trading_pair": trading_pair,
            "price": str(price),
            "volume": str(volume) if volume is not None else None,
        }
        extra.update(kwargs)

        self.debug(f"Market Data: {trading_pair} @ {price}", extra=extra)

    def signal(
        self,
        signal_type: str,
        trading_pair: str,
        strength: Optional[float] = None,
        indicators: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Log trading signal."""
        extra = {
            "trading_pair": trading_pair,
            "signal_type": signal_type,
            "strength": strength,
            "indicators": indicators,
        }
        extra.update(kwargs)

        self.info(f"Signal: {signal_type} for {trading_pair}", extra=extra)

    def performance(
        self,
        metric: str,
        value: Union[str, float, int],
        trading_pair: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Log performance metric."""
        extra = {
            "metric": metric,
            "value": str(value),
            "trading_pair": trading_pair,
        }
        extra.update(kwargs)

        self.info(f"Performance: {metric} = {value}", extra=extra)


class LoggingManager:
    """Manages logging configuration and setup for the trading bot."""

    def __init__(self, config: Optional[TradingConfig] = None):
        self.config = config
        self.log_directory = Path("local/logs")
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: Dict[str, logging.Handler] = {}

        # Ensure log directory exists
        self.log_directory.mkdir(parents=True, exist_ok=True)

        # Initialize logging
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup comprehensive logging configuration."""
        # Determine log level
        if self.config:
            log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        else:
            log_level = getattr(
                logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO
            )

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Setup handlers
        self._setup_console_handler(log_level)
        self._setup_file_handlers(log_level)
        self._setup_error_handler()
        self._setup_trading_handler()

        # Setup specific loggers
        self._setup_component_loggers()

    def _setup_console_handler(self, log_level: int) -> None:
        """Setup console output handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(TradingLogFormatter("compact"))

        # Add filter to prevent sensitive data logging
        console_handler.addFilter(self._sensitive_data_filter)

        logging.getLogger().addHandler(console_handler)
        self.handlers["console"] = console_handler

    def _setup_file_handlers(self, log_level: int) -> None:
        """Setup file-based log handlers with rotation."""
        # Main application log with rotation
        main_log_file = self.log_directory / "helios_trading_bot.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        main_handler.setLevel(log_level)
        main_handler.setFormatter(TradingLogFormatter("standard"))
        main_handler.addFilter(self._sensitive_data_filter)

        logging.getLogger().addHandler(main_handler)
        self.handlers["main_file"] = main_handler

        # Session-specific log
        session_log_file = self.log_directory / f"session_{self.session_id}.log"
        session_handler = logging.FileHandler(session_log_file, encoding="utf-8")
        session_handler.setLevel(log_level)
        session_handler.setFormatter(TradingLogFormatter("standard"))
        session_handler.addFilter(self._sensitive_data_filter)

        logging.getLogger().addHandler(session_handler)
        self.handlers["session_file"] = session_handler

    def _setup_error_handler(self) -> None:
        """Setup dedicated error log handler."""
        error_log_file = self.log_directory / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(TradingLogFormatter("standard"))

        logging.getLogger().addHandler(error_handler)
        self.handlers["error_file"] = error_handler

    def _setup_trading_handler(self) -> None:
        """Setup dedicated trading operations log handler."""
        trading_log_file = (
            self.log_directory / f"trading_{datetime.now().strftime('%Y%m%d')}.log"
        )
        trading_handler = logging.handlers.TimedRotatingFileHandler(
            trading_log_file,
            when="midnight",
            interval=1,
            backupCount=30,  # Keep 30 days
            encoding="utf-8",
        )
        trading_handler.setLevel(logging.INFO)
        trading_handler.setFormatter(TradingLogFormatter("json"))

        # Only log trading-related messages
        trading_handler.addFilter(
            lambda record: hasattr(record, "trading_pair")
            or "trading" in record.name.lower()
            or "signal" in record.name.lower()
            or "strategy" in record.name.lower()
        )

        logging.getLogger().addHandler(trading_handler)
        self.handlers["trading_file"] = trading_handler

    def _setup_component_loggers(self) -> None:
        """Setup loggers for specific components."""
        components = [
            "helios.core",
            "helios.api",
            "helios.data",
            "helios.strategies",
            "helios.risk",
            "helios.backtest",
            "helios.signals",
        ]

        for component in components:
            logger = logging.getLogger(component)
            logger.setLevel(logging.DEBUG)  # Component loggers can be more verbose
            self.loggers[component] = logger

    def _sensitive_data_filter(self, record: logging.LogRecord) -> bool:
        """Filter out sensitive data from logs."""
        sensitive_keywords = [
            "api_key",
            "api_secret",
            "password",
            "token",
            "secret",
            "private_key",
            "auth",
            "credential",
        ]

        message = record.getMessage().lower()
        return not any(keyword in message for keyword in sensitive_keywords)

    def get_logger(
        self, name: str, strategy: Optional[str] = None
    ) -> TradingLoggerAdapter:
        """Get a logger with trading context."""
        logger = logging.getLogger(name)

        extra = {
            "session_id": self.session_id,
            "strategy": strategy,
        }

        return TradingLoggerAdapter(logger, extra)

    def log_system_info(self) -> None:
        """Log system information at startup."""
        logger = self.get_logger("helios.system")

        logger.info(f"Helios Trading Bot - Session {self.session_id} starting")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        logger.info(f"Log directory: {self.log_directory.absolute()}")

        if self.config:
            logger.info(f"Environment: {self.config.environment}")
            logger.info(f"Testnet mode: {self.config.binance_testnet}")
            logger.info(f"Trading pairs: {len(self.config.default_trading_pairs)}")

        logger.info("Logging system initialized")

    def cleanup(self) -> None:
        """Cleanup logging resources."""
        logger = self.get_logger("helios.system")
        logger.info(f"Helios Trading Bot - Session {self.session_id} ending")

        # Close all handlers
        for handler in self.handlers.values():
            handler.close()

        # Remove handlers from root logger
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)


# Global logging manager instance
_logging_manager: Optional[LoggingManager] = None


def setup_logging(config: Optional[TradingConfig] = None) -> LoggingManager:
    """
    Setup and configure logging for the trading bot.

    Args:
        config: Trading configuration (optional)

    Returns:
        LoggingManager: Configured logging manager
    """
    global _logging_manager

    if _logging_manager is None:
        # Try to get config if not provided
        if config is None and CONFIG_AVAILABLE:
            try:
                config = get_config()
            except RuntimeError:
                pass  # No config loaded, proceed without it

        _logging_manager = LoggingManager(config)
        _logging_manager.log_system_info()

    return _logging_manager


def get_logger(name: str, strategy: Optional[str] = None) -> TradingLoggerAdapter:
    """
    Get a logger with trading context.

    Args:
        name: Logger name
        strategy: Strategy name (optional)

    Returns:
        TradingLoggerAdapter: Logger with trading context
    """
    if _logging_manager is None:
        setup_logging()
    assert _logging_manager is not None
    return _logging_manager.get_logger(name, strategy)


def cleanup_logging() -> None:
    """Cleanup logging resources."""
    global _logging_manager

    if _logging_manager is not None:
        _logging_manager.cleanup()
        _logging_manager = None


# Convenience function for quick logging setup
def quick_setup(log_level: str = "INFO") -> TradingLoggerAdapter:
    """
    Quick logging setup for scripts and testing.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        TradingLoggerAdapter: Default logger
    """
    os.environ["LOG_LEVEL"] = log_level.upper()
    setup_logging()
    return get_logger("helios.main")


if __name__ == "__main__":
    # Example usage and testing
    print("🔍 Testing Helios Trading Bot Logging System...")

    # Setup logging
    logger = quick_setup("DEBUG")

    # Test basic logging
    logger.info("Logging system test started")
    logger.debug("Debug message test")
    logger.warning("Warning message test")

    # Test trading-specific logging
    logger.trading_action(
        action="ORDER_PLACED",
        trading_pair="BTCUSDT",
        price=45000.50,
        quantity=0.001,
        side="BUY",
        order_id="12345",
    )

    logger.market_data("BTCUSDT", 45000.50, volume=1.5)

    logger.signal(
        "BUY_SIGNAL", "BTCUSDT", strength=0.85, indicators={"rsi": 25, "ma_cross": True}
    )

    logger.performance("daily_pnl", 150.75, trading_pair="BTCUSDT")

    try:
        # Test error logging
        raise ValueError("Test error for logging")
    except Exception as e:
        logger.error(f"Test error caught: {e}", exc_info=True)

    logger.info("Logging system test completed")

    # Cleanup
    cleanup_logging()

    print("✅ Logging system test completed successfully!")
