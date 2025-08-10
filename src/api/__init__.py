"""
Helios Trading Bot - API Integration Package

This package handles all external API integrations, starting with Binance.
Provides secure, rate-limited, and robust API connectivity.

Modules:
    binance_client: Main Binance API client wrapper
    exceptions: Custom API exceptions and error handling
    rate_limiter: API rate limiting and request management
    models: Data models for API responses
"""

from .binance_client import BinanceClient
from .exceptions import (
    AuthenticationError,
    BinanceAPIError,
    NetworkError,
    RateLimitError,
)
from .models import AccountInfo, ExchangeInfo, KlineData, SymbolInfo, TickerData
from .rate_limiter import get_rate_limiter_status, is_rate_limiter_healthy

__all__ = [
    "BinanceClient",
    "BinanceAPIError",
    "RateLimitError",
    "AuthenticationError",
    "NetworkError",
    "TickerData",
    "KlineData",
    "AccountInfo",
    "ExchangeInfo",
    "SymbolInfo",
    "get_rate_limiter_status",
    "is_rate_limiter_healthy",
]
