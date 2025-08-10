"""
Helios Trading Bot - Core Constants

Centralized constants to avoid magic strings throughout the codebase.
This improves maintainability and reduces the risk of typos.
"""

from typing import Dict


# Database Configuration
class DatabaseConstants:
    """Database-related constants."""

    # Schema name
    DEFAULT_SCHEMA = "helios_trading"

    # Table names
    TABLE_CURRENT_PRICES = "current_prices"
    TABLE_OHLCV_1M = "ohlcv_1m"
    TABLE_OHLCV_5M = "ohlcv_5m"
    TABLE_OHLCV_1H = "ohlcv_1h"
    TABLE_OHLCV_4H = "ohlcv_4h"
    TABLE_OHLCV_1D = "ohlcv_1d"
    TABLE_TRADING_SESSIONS = "trading_sessions"
    TABLE_DATA_QUALITY_METRICS = "data_quality_metrics"

    # All table names for iteration
    ALL_TABLES = [
        TABLE_CURRENT_PRICES,
        TABLE_OHLCV_1M,
        TABLE_OHLCV_5M,
        TABLE_OHLCV_1H,
        TABLE_OHLCV_4H,
        TABLE_OHLCV_1D,
        TABLE_TRADING_SESSIONS,
        TABLE_DATA_QUALITY_METRICS,
    ]

    # OHLCV tables only
    OHLCV_TABLES = [
        TABLE_OHLCV_1M,
        TABLE_OHLCV_5M,
        TABLE_OHLCV_1H,
        TABLE_OHLCV_4H,
        TABLE_OHLCV_1D,
    ]


# Time Intervals
class TimeIntervals:
    """Time interval constants for market data."""

    # Binance API intervals
    INTERVAL_1M = "1m"
    INTERVAL_5M = "5m"
    INTERVAL_15M = "15m"
    INTERVAL_30M = "30m"
    INTERVAL_1H = "1h"
    INTERVAL_2H = "2h"
    INTERVAL_4H = "4h"
    INTERVAL_6H = "6h"
    INTERVAL_8H = "8h"
    INTERVAL_12H = "12h"
    INTERVAL_1D = "1d"
    INTERVAL_3D = "3d"
    INTERVAL_1W = "1w"
    INTERVAL_1M_MONTH = "1M"

    # Supported intervals for OHLCV storage
    SUPPORTED_INTERVALS = [
        INTERVAL_1M,
        INTERVAL_5M,
        INTERVAL_1H,
        INTERVAL_4H,
        INTERVAL_1D,
    ]

    # Mapping from interval to table name
    INTERVAL_TO_TABLE: Dict[str, str] = {
        INTERVAL_1M: DatabaseConstants.TABLE_OHLCV_1M,
        INTERVAL_5M: DatabaseConstants.TABLE_OHLCV_5M,
        INTERVAL_1H: DatabaseConstants.TABLE_OHLCV_1H,
        INTERVAL_4H: DatabaseConstants.TABLE_OHLCV_4H,
        INTERVAL_1D: DatabaseConstants.TABLE_OHLCV_1D,
    }

    # Mapping from table name to interval
    TABLE_TO_INTERVAL: Dict[str, str] = {v: k for k, v in INTERVAL_TO_TABLE.items()}


# Redis Key Prefixes
class RedisKeys:
    """Redis key prefixes for organized caching."""

    PREFIX_PRICE = "price"
    PREFIX_BID = "bid"
    PREFIX_ASK = "ask"
    PREFIX_VOLUME = "volume"
    PREFIX_CHANGE = "change"
    PREFIX_TICKER = "ticker"

    # Cache TTL values (in seconds)
    TTL_PRICE_DATA = 300  # 5 minutes
    TTL_TICKER_DATA = 600  # 10 minutes
    TTL_ACCOUNT_DATA = 1800  # 30 minutes


# Trading Symbols
class TradingSymbols:
    """Common trading symbol constants."""

    # Major pairs
    BTCUSDT = "BTCUSDT"
    ETHUSDT = "ETHUSDT"
    SOLUSDT = "SOLUSDT"
    AVAXUSDT = "AVAXUSDT"
    LINKUSDT = "LINKUSDT"
    DOTUSDT = "DOTUSDT"
    ADAUSDT = "ADAUSDT"

    # Default trading pairs for the bot
    DEFAULT_PAIRS = [SOLUSDT, AVAXUSDT, LINKUSDT, DOTUSDT, ADAUSDT]

    # Trading symbols for signal generation
    TRADING_SYMBOLS = [BTCUSDT, ETHUSDT, SOLUSDT, AVAXUSDT, LINKUSDT]


# API Configuration
class APIConstants:
    """Binance API related constants."""

    # Base URLs
    TESTNET_BASE_URL = "https://testnet.binance.vision"
    PRODUCTION_BASE_URL = "https://api.binance.com"

    # Endpoints
    ENDPOINT_TIME = "/api/v3/time"
    ENDPOINT_PING = "/api/v3/ping"
    ENDPOINT_EXCHANGE_INFO = "/api/v3/exchangeInfo"
    ENDPOINT_TICKER_24HR = "/api/v3/ticker/24hr"
    ENDPOINT_TICKER_PRICE = "/api/v3/ticker/price"
    ENDPOINT_KLINES = "/api/v3/klines"
    ENDPOINT_ACCOUNT = "/api/v3/account"

    # Rate limits
    DEFAULT_RATE_LIMIT_PER_MINUTE = 1200
    DEFAULT_RATE_LIMIT_PER_SECOND = 10

    # Request configuration
    DEFAULT_TIMEOUT_SECONDS = 30
    DEFAULT_CONNECT_TIMEOUT_SECONDS = 10
    MAX_RETRIES = 3
    BASE_BACKOFF_SECONDS = 1.0


# Environment Constants
class EnvironmentConstants:
    """Environment and configuration constants."""

    # Environment types
    ENV_DEVELOPMENT = "development"
    ENV_TESTNET = "testnet"
    ENV_PRODUCTION = "production"
    ENV_TEST = "test"

    # Log levels
    LOG_DEBUG = "DEBUG"
    LOG_INFO = "INFO"
    LOG_WARNING = "WARNING"
    LOG_ERROR = "ERROR"
    LOG_CRITICAL = "CRITICAL"

    # Default directories
    DEFAULT_DATA_DIR = "local/data"
    DEFAULT_LOG_DIR = "local/logs"
    DEFAULT_CONFIG_DIR = "local/configs"


# Signal Generation Constants
class SignalConstants:
    """Constants for signal generation."""

    # Signal types
    SIGNAL_BUY = "BUY"
    SIGNAL_SELL = "SELL"
    SIGNAL_NEUTRAL = "NEUTRAL"

    # Technical indicator periods
    DEFAULT_FAST_MA = 10
    DEFAULT_SLOW_MA = 20
    DEFAULT_ATR_PERIOD = 14
    DEFAULT_RSI_PERIOD = 14

    # Signal validation
    MIN_DATA_POINTS = 50  # Minimum data points needed for reliable signals


# Risk Management Constants
class RiskConstants:
    """Risk management constants."""

    # Default risk parameters
    DEFAULT_RISK_PER_TRADE = 0.01  # 1%
    DEFAULT_MAX_DRAWDOWN = 0.25  # 25%
    DEFAULT_DAILY_LOSS_LIMIT = 0.05  # 5%

    # Position sizing
    DEFAULT_MAX_POSITION_USD = 100.00
    DEFAULT_DAILY_LOSS_USD = 50.00

    # Grid trading
    DEFAULT_GRID_LEVELS = 10
    DEFAULT_GRID_SPACING_PERCENT = 1.0  # 1%


# Data Quality Constants
class DataQualityConstants:
    """Data quality and validation constants."""

    # Quality score thresholds
    QUALITY_EXCELLENT = 0.95
    QUALITY_GOOD = 0.85
    QUALITY_WARNING = 0.70
    QUALITY_ERROR = 0.50

    # Alert levels
    ALERT_INFO = "info"
    ALERT_WARNING = "warning"
    ALERT_ERROR = "error"
    ALERT_CRITICAL = "critical"

    # Data validation limits
    MAX_PRICE_DEVIATION = 0.10  # 10% from previous price
    MIN_VOLUME_THRESHOLD = 1000  # Minimum daily volume
    MAX_DATA_AGE_SECONDS = 300  # 5 minutes

    # Batch processing
    LARGE_BATCH_THRESHOLD = 1000  # Use transactions for batches larger than this


# File and Storage Constants
class StorageConstants:
    """File and storage related constants."""

    # R2/S3 key patterns
    R2_HISTORICAL_PREFIX = "historical"
    R2_ARCHIVE_PREFIX = "archive"
    R2_BACKUP_PREFIX = "backup"

    # File extensions
    EXT_PARQUET = ".parquet"
    EXT_CSV = ".csv"
    EXT_JSON = ".json"
    EXT_LOG = ".log"

    # Compression
    DEFAULT_COMPRESSION = "snappy"  # For Parquet files


# Performance Constants
class PerformanceConstants:
    """Performance and optimization constants."""

    # Connection pool sizes
    DEFAULT_DB_POOL_SIZE = 10
    DEFAULT_HTTP_POOL_SIZE = 100
    DEFAULT_HTTP_PER_HOST = 30

    # Timeouts
    DEFAULT_QUERY_TIMEOUT = 10
    DEFAULT_CONNECTION_TIMEOUT = 5
    DNS_CACHE_TTL = 300

    # Monitoring
    HEALTH_CHECK_INTERVAL = 60  # seconds
    METRICS_COLLECTION_INTERVAL = 30  # seconds


# Trading Session Status
class TradingSessionStatus:
    """Trading session status constants."""

    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"

    ALL_STATUSES = [ACTIVE, PAUSED, STOPPED, COMPLETED, ERROR]


# Database Schema Constants
class DatabaseSchemaConstants:
    """Constants for database schema operations."""

    # Table types
    TABLE_TYPE_BASE = "BASE TABLE"

    # Time descriptions for table comments
    TIME_DESC_1M = "1 minute"
    TIME_DESC_5M = "5 minute"
    TIME_DESC_1H = "1 hour"
    TIME_DESC_4H = "4 hour"
    TIME_DESC_1D = "1 day"

    # Retention and cleanup
    DEFAULT_RETENTION_DAYS = 30
    MINIMUM_TABLES_FOR_HEALTH = 3
    SCHEMA_VERIFICATION_DELAY = 0.5  # seconds

    # Index prefixes
    INDEX_PREFIX = "idx_"

    # Constraint validation intervals
    PRICE_STALENESS_HOURS = 1  # Maximum hours for price data to be considered fresh

    # Cleanup timing
    CLEANUP_HOUR = 0
    CLEANUP_MINUTE = 0
    CLEANUP_SECOND = 0
    CLEANUP_MICROSECOND = 0
