"""
Helios Trading Bot - Core Configuration Management

This module provides secure configuration loading and management for the Helios
trading bot. It handles API credentials, environment settings, and trading
parameters with built-in security and validation.

Security Features:
- Environment variable loading for sensitive data
- API key validation and secure storage
- Environment-specific configurations
- Comprehensive error handling and logging
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import json
from datetime import datetime

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Configure logging for this module
logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    """
    Comprehensive trading configuration with security and validation.
    
    This class manages all configuration aspects of the Helios trading bot,
    including API credentials, risk parameters, and trading settings.
    """
    
    # API Configuration
    binance_api_key: str = field(default="", repr=False)  # Hidden from repr for security
    binance_api_secret: str = field(default="", repr=False)  # Hidden from repr for security
    binance_testnet: bool = field(default=True)
    
    # PostgreSQL Configuration (Neon) - Individual Parameters
    neon_host: str = field(default="", repr=False)
    neon_database: str = field(default="", repr=False)
    neon_username: str = field(default="", repr=False)
    neon_password: str = field(default="", repr=False)
    neon_port: int = field(default=5432)
    neon_ssl_mode: str = field(default="require")
    
    # Redis Configuration (Upstash) - Individual Parameters
    upstash_redis_username: str = field(default="", repr=False)
    upstash_redis_host: str = field(default="", repr=False)
    upstash_redis_port: int = field(default=6379)
    upstash_redis_password: str = field(default="", repr=False)
    
    # Cloudflare R2 Configuration - Individual Parameters
    r2_account_id: str = field(default="", repr=False)
    r2_api_token: str = field(default="", repr=False)
    r2_access_key: str = field(default="", repr=False)  # S3-style access key
    r2_secret_key: str = field(default="", repr=False)  # S3-style secret key
    r2_bucket_name: str = field(default="", repr=False)
    r2_endpoint: str = field(default="", repr=False)
    r2_region: str = field(default="auto")
    
    # Environment Settings
    environment: str = field(default="development")  # development, testnet, production
    log_level: str = field(default="INFO")
    data_directory: str = field(default="local/data")
    
    # Trading Parameters
    default_trading_pairs: list = field(default_factory=lambda: [
        "SOLUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "ADAUSDT"
    ])
    trading_symbols: list = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT"
    ])
    max_concurrent_trades: int = field(default=5)
    polling_interval_seconds: int = field(default=30)
    
    # Risk Management
    max_position_size_usd: Decimal = field(default=Decimal("100.00"))
    max_daily_loss_usd: Decimal = field(default=Decimal("50.00"))
    max_account_drawdown_percent: Decimal = field(default=Decimal("25.00"))
    
    # Grid Trading Settings
    grid_levels: int = field(default=10)
    grid_spacing_percent: Decimal = field(default=Decimal("1.0"))
    
    # Signal Settings
    signal_check_interval_seconds: int = field(default=30)
    price_update_interval_seconds: int = field(default=5)
    
    # Validation settings
    _config_loaded_at: datetime = field(default_factory=datetime.now)
    _validation_errors: list = field(default_factory=list)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_configuration()
        if self._validation_errors:
            raise ValueError(f"Configuration validation failed: {self._validation_errors}")
    
    def _validate_configuration(self) -> None:
        """Comprehensive configuration validation."""
        self._validation_errors = []
        
        # API Key Validation
        if not self.binance_api_key:
            self._validation_errors.append("BINANCE_API_KEY is required")
        elif len(self.binance_api_key) < 32:
            self._validation_errors.append("BINANCE_API_KEY appears invalid (too short)")
            
        if not self.binance_api_secret:
            self._validation_errors.append("BINANCE_API_SECRET is required")
        elif len(self.binance_api_secret) < 32:
            self._validation_errors.append("BINANCE_API_SECRET appears invalid (too short)")
        
        # PostgreSQL (Neon) Validation - Individual Parameters
        if not self.neon_host:
            self._validation_errors.append("NEON_HOST is required")
        elif not self.neon_host.strip():
            self._validation_errors.append("NEON_HOST cannot be empty")
            
        if not self.neon_database:
            self._validation_errors.append("NEON_DATABASE is required")
        elif not self.neon_database.strip():
            self._validation_errors.append("NEON_DATABASE cannot be empty")
            
        if not self.neon_username:
            self._validation_errors.append("NEON_USERNAME is required")
        elif not self.neon_username.strip():
            self._validation_errors.append("NEON_USERNAME cannot be empty")
            
        if not self.neon_password:
            self._validation_errors.append("NEON_PASSWORD is required")
        elif len(self.neon_password) < 8:
            self._validation_errors.append("NEON_PASSWORD appears too short (minimum 8 characters)")
            
        if not (1 <= self.neon_port <= 65535):
            self._validation_errors.append("NEON_PORT must be between 1 and 65535")
            
        valid_ssl_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        if self.neon_ssl_mode not in valid_ssl_modes:
            self._validation_errors.append(f"NEON_SSL_MODE must be one of: {valid_ssl_modes}")
        
        # Redis (Upstash) Validation - Individual Parameters
        if not self.upstash_redis_host:
            self._validation_errors.append("UPSTASH_REDIS_HOST is required")
        elif not self.upstash_redis_host.strip():
            self._validation_errors.append("UPSTASH_REDIS_HOST cannot be empty")
            
        if not (1 <= self.upstash_redis_port <= 65535):
            self._validation_errors.append("UPSTASH_REDIS_PORT must be between 1 and 65535")
            
        if not self.upstash_redis_password:
            self._validation_errors.append("UPSTASH_REDIS_PASSWORD is required")
        elif len(self.upstash_redis_password) < 8:
            self._validation_errors.append("UPSTASH_REDIS_PASSWORD appears too short (minimum 8 characters)")
        
        # Cloudflare R2 Validation - Individual Parameters
        if not self.r2_account_id:
            self._validation_errors.append("R2_ACCOUNT_ID is required")
        elif len(self.r2_account_id) < 32:
            self._validation_errors.append("R2_ACCOUNT_ID appears invalid (too short)")
        
        # Check for either API token or access key/secret key pair
        has_api_token = bool(self.r2_api_token and len(self.r2_api_token) >= 32)
        has_access_keys = bool(self.r2_access_key and self.r2_secret_key)
        
        if not (has_api_token or has_access_keys):
            self._validation_errors.append("R2 authentication required: either R2_API_TOKEN or R2_ACCESS_KEY+R2_SECRET_KEY")
        
        if self.r2_api_token and len(self.r2_api_token) < 32:
            self._validation_errors.append("R2_API_TOKEN appears invalid (too short)")
            
        if not self.r2_bucket_name:
            self._validation_errors.append("R2_BUCKET_NAME is required")
        elif not self.r2_bucket_name.strip():
            self._validation_errors.append("R2_BUCKET_NAME cannot be empty")
            
        if not self.r2_endpoint:
            self._validation_errors.append("R2_ENDPOINT is required")
        elif not self.r2_endpoint.startswith('https://'):
            self._validation_errors.append("R2_ENDPOINT must start with https://")
        
        # Environment Validation
        valid_environments = ["development", "testnet", "production"]
        if self.environment not in valid_environments:
            self._validation_errors.append(f"Environment must be one of: {valid_environments}")
        
        # Risk Parameter Validation
        if self.max_position_size_usd <= 0:
            self._validation_errors.append("max_position_size_usd must be positive")
        
        if self.max_daily_loss_usd <= 0:
            self._validation_errors.append("max_daily_loss_usd must be positive")
        
        if not (0 < self.max_account_drawdown_percent <= 100):
            self._validation_errors.append("max_account_drawdown_percent must be between 0 and 100")
        
        # Trading Pair Validation
        if not self.default_trading_pairs:
            self._validation_errors.append("At least one trading pair must be specified")
        
        for pair in self.default_trading_pairs:
            if not isinstance(pair, str) or len(pair) < 6:
                self._validation_errors.append(f"Invalid trading pair format: {pair}")
        
        # Grid Trading Validation
        if self.grid_levels < 2:
            self._validation_errors.append("grid_levels must be at least 2")
        
        if self.grid_spacing_percent <= 0:
            self._validation_errors.append("grid_spacing_percent must be positive")
        
        # Interval Validation
        if self.signal_check_interval_seconds < 1:
            self._validation_errors.append("signal_check_interval_seconds must be at least 1")
        
        if self.price_update_interval_seconds < 1:
            self._validation_errors.append("price_update_interval_seconds must be at least 1")
    
    def get_postgresql_url(self) -> str:
        """Build PostgreSQL connection URL from individual parameters."""
        return (
            f"postgresql://{self.neon_username}:{self.neon_password}@"
            f"{self.neon_host}:{self.neon_port}/{self.neon_database}"
            f"?sslmode={self.neon_ssl_mode}"
        )
    
    def get_redis_url(self) -> str:
        """Build Redis connection URL from individual parameters."""
        auth_part = ""
        if self.upstash_redis_username:
            auth_part = f"{self.upstash_redis_username}:{self.upstash_redis_password}@"
        else:
            auth_part = f":{self.upstash_redis_password}@" if self.upstash_redis_password else ""
        
        # Use rediss:// (SSL) for Upstash Redis which requires SSL connections
        return f"rediss://{auth_part}{self.upstash_redis_host}:{self.upstash_redis_port}"
    
    def get_r2_config(self) -> Dict[str, str]:
        """Get Cloudflare R2 configuration as dictionary."""
        return {
            "account_id": self.r2_account_id,
            "api_token": self.r2_api_token,
            "access_key": self.r2_access_key,
            "secret_key": self.r2_secret_key,
            "bucket_name": self.r2_bucket_name,
            "endpoint": self.r2_endpoint,
            "region": self.r2_region
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "environment": self.environment,
            "binance_testnet": self.binance_testnet,
            "log_level": self.log_level,
            "data_directory": self.data_directory,
            "default_trading_pairs": self.default_trading_pairs,
            "max_concurrent_trades": self.max_concurrent_trades,
            "max_position_size_usd": str(self.max_position_size_usd),
            "max_daily_loss_usd": str(self.max_daily_loss_usd),
            "max_account_drawdown_percent": str(self.max_account_drawdown_percent),
            "grid_levels": self.grid_levels,
            "grid_spacing_percent": str(self.grid_spacing_percent),
            "signal_check_interval_seconds": self.signal_check_interval_seconds,
            "price_update_interval_seconds": self.price_update_interval_seconds,
            "config_loaded_at": self._config_loaded_at.isoformat(),
            "api_keys_configured": bool(self.binance_api_key and self.binance_api_secret),
            "database_configured": bool(self.neon_host and self.neon_database),
            "redis_configured": bool(self.upstash_redis_host and self.upstash_redis_password),
            "r2_configured": bool(self.r2_account_id and self.r2_bucket_name and 
                                (self.r2_api_token or (self.r2_access_key and self.r2_secret_key)))
        }
    
    def save_config_summary(self, filepath: str) -> None:
        """Save non-sensitive configuration summary to file."""
        config_summary = self.to_dict()
        
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(config_summary, f, indent=2)
        
        logger.info(f"Configuration summary saved to {filepath}")


class ConfigurationManager:
    """
    Manages configuration loading from various sources.
    
    This class handles loading configuration from environment variables,
    .env files, and provides secure credential management.
    """
    
    def __init__(self):
        self.config: Optional[TradingConfig] = None
        self._env_file_path: Optional[str] = None
    
    def load_from_environment(self) -> TradingConfig:
        """
        Load configuration from environment variables.
        
        Expected environment variables:
        - BINANCE_API_KEY: Binance API key
        - BINANCE_API_SECRET: Binance API secret
        - NEON_HOST: PostgreSQL host
        - NEON_DATABASE: PostgreSQL database name
        - NEON_USERNAME: PostgreSQL username
        - NEON_PASSWORD: PostgreSQL password
        - NEON_PORT: PostgreSQL port (default: 5432)
        - NEON_SSL_MODE: PostgreSQL SSL mode (default: require)
        - UPSTASH_REDIS_USERNAME: Redis username (optional)
        - UPSTASH_REDIS_HOST: Redis host
        - UPSTASH_REDIS_PORT: Redis port (default: 6379)
        - UPSTASH_REDIS_PASSWORD: Redis password
        - R2_ACCOUNT_ID: Cloudflare R2 account ID
        - R2_API_TOKEN: Cloudflare R2 API token
        - R2_ACCESS_KEY: Cloudflare R2 S3-style access key (alternative to API token)
        - R2_SECRET_KEY: Cloudflare R2 S3-style secret key (alternative to API token)
        - R2_BUCKET_NAME: Cloudflare R2 bucket name
        - R2_ENDPOINT: Cloudflare R2 endpoint URL
        - R2_REGION: Cloudflare R2 region (default: auto)
        - BINANCE_TESTNET: true/false for testnet usage
        - TRADING_ENVIRONMENT: development/testnet/production
        - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
        """
        logger.info("Loading configuration from environment variables")
        
        # Auto-load .env file if available
        if DOTENV_AVAILABLE and os.path.exists('.env'):
            logger.info("Loading .env file")
            load_dotenv()
        
        # Load API credentials (required)
        api_key = os.getenv("BINANCE_API_KEY", "").strip()
        api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
        
        # Load PostgreSQL (Neon) credentials - Individual parameters
        neon_host = os.getenv("NEON_HOST", "").strip()
        neon_database = os.getenv("NEON_DATABASE", "").strip()
        neon_username = os.getenv("NEON_USERNAME", "").strip()
        neon_password = os.getenv("NEON_PASSWORD", "").strip()
        neon_port = int(os.getenv("NEON_PORT", "5432"))
        neon_ssl_mode = os.getenv("NEON_SSL_MODE", "require").strip()
        
        # Load Redis (Upstash) credentials - Individual parameters
        redis_username = os.getenv("UPSTASH_REDIS_USERNAME", "").strip()
        redis_host = os.getenv("UPSTASH_REDIS_HOST", "").strip()
        redis_port = int(os.getenv("UPSTASH_REDIS_PORT", "6379"))
        redis_password = os.getenv("UPSTASH_REDIS_PASSWORD", "").strip()
        
        # Load Cloudflare R2 credentials - Individual parameters
        r2_account = os.getenv("R2_ACCOUNT_ID", "").strip()
        r2_token = os.getenv("R2_API_TOKEN", "").strip()
        r2_access_key = os.getenv("R2_ACCESS_KEY", "").strip()
        r2_secret_key = os.getenv("R2_SECRET_KEY", "").strip()
        r2_bucket = os.getenv("R2_BUCKET_NAME", "").strip()
        r2_endpoint = os.getenv("R2_ENDPOINT", "").strip()
        r2_region = os.getenv("R2_REGION", "auto").strip()
        
        # Load environment settings
        use_testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        environment = os.getenv("TRADING_ENVIRONMENT", "development").lower()
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        
        # Load trading parameters
        data_dir = os.getenv("DATA_DIRECTORY", "local/data")
        
        # Create configuration
        config = TradingConfig(
            binance_api_key=api_key,
            binance_api_secret=api_secret,
            binance_testnet=use_testnet,
            neon_host=neon_host,
            neon_database=neon_database,
            neon_username=neon_username,
            neon_password=neon_password,
            neon_port=neon_port,
            neon_ssl_mode=neon_ssl_mode,
            upstash_redis_username=redis_username,
            upstash_redis_host=redis_host,
            upstash_redis_port=redis_port,
            upstash_redis_password=redis_password,
            r2_account_id=r2_account,
            r2_api_token=r2_token,
            r2_access_key=r2_access_key,
            r2_secret_key=r2_secret_key,
            r2_bucket_name=r2_bucket,
            r2_endpoint=r2_endpoint,
            r2_region=r2_region,
            environment=environment,
            log_level=log_level,
            data_directory=data_dir
        )
        
        self.config = config
        logger.info(f"Configuration loaded successfully for environment: {environment}")
        return config
    
    def load_from_env_file(self, env_file_path: str = ".env") -> TradingConfig:
        """
        Load configuration from .env file.
        
        Args:
            env_file_path: Path to the .env file
        
        Returns:
            TradingConfig: Loaded configuration
        """
        logger.info(f"Loading configuration from .env file: {env_file_path}")
        
        if not os.path.exists(env_file_path):
            raise FileNotFoundError(f"Environment file not found: {env_file_path}")
        
        # Load .env file
        env_vars = {}
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
        
        # Set environment variables temporarily
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.getenv(key)
            os.environ[key] = value
        
        try:
            # Load configuration
            config = self.load_from_environment()
            self._env_file_path = env_file_path
            return config
        finally:
            # Restore original environment variables
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def validate_api_credentials(self) -> bool:
        """
        Validate that API credentials are properly configured.
        
        Returns:
            bool: True if credentials appear valid
        """
        if not self.config:
            return False
        
        return (
            bool(self.config.binance_api_key) and
            bool(self.config.binance_api_secret) and
            len(self.config.binance_api_key) >= 32 and
            len(self.config.binance_api_secret) >= 32
        )
    
    def get_safe_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary without sensitive data."""
        if not self.config:
            return {"error": "No configuration loaded"}
        
        return self.config.to_dict()


# Global configuration manager instance
config_manager = ConfigurationManager()


def get_config() -> TradingConfig:
    """
    Get the current trading configuration.
    
    Returns:
        TradingConfig: Current configuration
    
    Raises:
        RuntimeError: If configuration is not loaded
    """
    if not config_manager.config:
        raise RuntimeError("Configuration not loaded. Call load_configuration() first.")
    
    return config_manager.config


def load_configuration(env_file_path: str = ".env") -> TradingConfig:
    """
    Load configuration from environment or .env file.
    
    Args:
        env_file_path: Path to .env file (optional)
    
    Returns:
        TradingConfig: Loaded configuration
    """
    if os.path.exists(env_file_path):
        logger.info(f"Loading configuration from {env_file_path}")
        return config_manager.load_from_env_file(env_file_path)
    else:
        logger.info("Loading configuration from environment variables")
        return config_manager.load_from_environment()


def validate_configuration() -> bool:
    """
    Validate current configuration.
    
    Returns:
        bool: True if configuration is valid
    """
    try:
        config = get_config()
        return config_manager.validate_api_credentials()
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    try:
        config = load_configuration()
        print("✅ Configuration loaded successfully!")
        print(f"Environment: {config.environment}")
        print(f"Testnet: {config.binance_testnet}")
        print(f"Trading pairs: {config.default_trading_pairs}")
        print(f"API credentials configured: {config_manager.validate_api_credentials()}")
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}") 