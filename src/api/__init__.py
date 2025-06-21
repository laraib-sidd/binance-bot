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

from .exceptions import (
    BinanceAPIError,
    RateLimitError,
    AuthenticationError,
    NetworkError,
)

__all__ = [
    "BinanceAPIError",
    "RateLimitError", 
    "AuthenticationError",
    "NetworkError",
] 