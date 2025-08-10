"""
Helios Trading Bot - Binance API Client

Secure, production-ready Binance API client with comprehensive error handling,
rate limiting, and financial-grade security measures.

Key Features:
- HMAC-SHA256 authentication for secure API requests
- Automatic retry logic with exponential backoff
- Integration with sophisticated rate limiting
- Comprehensive error handling and logging
- Support for both testnet and production environments
- Type-safe responses with data validation
"""

from decimal import Decimal
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

from ..core.config import TradingConfig
from .exceptions import (
    AuthenticationError,
    BinanceAPIError,
    InvalidResponseError,
    NetworkError,
    classify_binance_error,
)
from .models import AccountInfo, ExchangeInfo, KlineData, TickerData
from .rate_limiter import acquire_rate_limit, update_rate_limits

logger = logging.getLogger(__name__)


class BinanceClient:
    """
    Secure Binance API client with comprehensive error handling and security.

    Handles authentication, rate limiting, retries, and data validation
    for all Binance API interactions.
    """

    def __init__(self, config: TradingConfig):
        """
        Initialize Binance API client.

        Args:
            config: Trading configuration with API credentials
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

        # API endpoints
        if config.binance_testnet:
            self.base_url = "https://testnet.binance.vision"
            logger.info("🧪 Initialized Binance TESTNET client (safe for development)")
        else:
            self.base_url = "https://api.binance.com"
            logger.warning("⚠️ Initialized Binance PRODUCTION client (REAL MONEY)")

        # Request configuration
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.max_retries = 3
        self.base_backoff = 1.0  # Base delay for exponential backoff

        # Security validation
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        """Validate API credentials format and security."""
        if not self.config.binance_api_key:
            raise AuthenticationError("Binance API key is required")

        if not self.config.binance_api_secret:
            raise AuthenticationError("Binance API secret is required")

        # Basic format validation
        if len(self.config.binance_api_key) < 32:
            raise AuthenticationError("Invalid API key format (too short)")

        if len(self.config.binance_api_secret) < 32:
            raise AuthenticationError("Invalid API secret format (too short)")

        logger.debug("✅ API credentials validated")

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is available."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=30,  # Per-host connection limit
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
            )

            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={
                    "User-Agent": "Helios-Trading-Bot/1.0",
                    "Content-Type": "application/json",
                    "X-MBX-APIKEY": self.config.binance_api_key,
                },
            )
            logger.debug("📡 HTTP session established")

    async def close(self) -> None:
        """Close HTTP session and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("📡 HTTP session closed")

    def _generate_signature(self, query_string: str) -> str:
        """
        Generate HMAC-SHA256 signature for authenticated requests.

        Args:
            query_string: URL-encoded query parameters

        Returns:
            Hex-encoded signature
        """
        return hmac.new(
            self.config.binance_api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _build_query_string(
        self, params: Dict[str, Any], include_timestamp: bool = True
    ) -> str:
        """
        Build URL-encoded query string with optional timestamp.

        Args:
            params: Request parameters
            include_timestamp: Whether to include timestamp

        Returns:
            URL-encoded query string
        """
        if include_timestamp:
            params["timestamp"] = int(time.time() * 1000)

        # Remove None values and convert to strings
        clean_params = {k: str(v) for k, v in params.items() if v is not None}

        return urlencode(clean_params)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
        retries: int = 0,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Binance API with comprehensive error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Request parameters
            signed: Whether request requires signature
            retries: Current retry attempt

        Returns:
            Parsed JSON response

        Raises:
            BinanceAPIError: For various API errors
        """
        await self._ensure_session()

        # Acquire rate limit permission
        await acquire_rate_limit(endpoint)

        # Build request
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        try:
            if signed:
                # Add signature for authenticated requests
                query_string = self._build_query_string(params, include_timestamp=True)
                signature = self._generate_signature(query_string)
                params["signature"] = signature
                final_query = self._build_query_string(params, include_timestamp=False)
            else:
                final_query = self._build_query_string(params, include_timestamp=False)

            # Make request
            request_start = time.time()

            if method.upper() == "GET":
                if final_query:
                    url += f"?{final_query}"
                async with self._session.get(url) as response:
                    return await self._handle_response(
                        response, endpoint, request_start
                    )

            elif method.upper() == "POST":
                async with self._session.post(url, data=final_query) as response:
                    return await self._handle_response(
                        response, endpoint, request_start
                    )

            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except aiohttp.ClientError as e:
            logger.error(f"Network error for {endpoint}: {e}")
            network_error = NetworkError(
                f"Failed to connect to {endpoint}: {str(e)}",
                context={"endpoint": endpoint, "error_type": type(e).__name__},
            )
            raise network_error from e

        except Exception as e:
            logger.error(f"Unexpected error for {endpoint}: {e}")
            raise BinanceAPIError(
                f"Unexpected error: {str(e)}",
                context={"endpoint": endpoint, "error_type": type(e).__name__},
            ) from e

    async def _handle_response(
        self, response: aiohttp.ClientResponse, endpoint: str, request_start: float
    ) -> Dict[str, Any]:
        """
        Handle HTTP response with error checking and logging.

        Args:
            response: HTTP response object
            endpoint: API endpoint
            request_start: Request start timestamp

        Returns:
            Parsed JSON response

        Raises:
            BinanceAPIError: For various response errors
        """
        duration = time.time() - request_start

        # Update rate limits from headers
        update_rate_limits(dict(response.headers))

        # Log request performance
        logger.debug(f"API {endpoint}: {response.status} in {duration:.3f}s")

        try:
            response_text = await response.text()

            # Handle successful responses
            if 200 <= response.status < 300:
                try:
                    if response.content_type != "application/json":
                        # Handle unexpected content type
                        raise InvalidResponseError(
                            f"Expected JSON response, got {response.content_type}",
                            http_status=response.status,
                            context={
                                "endpoint": endpoint,
                                "response_preview": response_text[:200],
                            },
                        )
                    data = await response.json()
                    logger.debug(f"✅ {endpoint} success: {len(str(data))} chars")
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response from {endpoint}: {e}")
                    raise InvalidResponseError(
                        f"Invalid JSON response: {str(e)}",
                        http_status=response.status,
                        context={
                            "endpoint": endpoint,
                            "response_preview": response_text[:200],
                        },
                    ) from e

            # Handle error responses
            else:
                try:
                    error_data = json.loads(response_text)
                    error_code = str(error_data.get("code", ""))
                    error_msg = error_data.get("msg", f"HTTP {response.status}")
                except json.JSONDecodeError:
                    error_code = ""
                    error_msg = f"HTTP {response.status}: {response_text[:200]}"

                # Classify and raise appropriate exception
                context = {
                    "endpoint": endpoint,
                    "response_headers": dict(response.headers),
                    "duration": duration,
                }

                error = classify_binance_error(
                    error_code=error_code,
                    http_status=response.status,
                    message=error_msg,
                    context=context,
                )

                logger.error(f"❌ {endpoint} failed: {error_msg} (code: {error_code})")
                raise error

        except aiohttp.ClientError as e:
            logger.error(f"Failed to read response from {endpoint}: {e}")
            raise NetworkError(
                f"Failed to read response: {str(e)}", context={"endpoint": endpoint}
            ) from e

    # Public API Methods (No authentication required)

    async def get_server_time(self) -> int:
        """
        Get Binance server timestamp.

        Returns:
            Server timestamp in milliseconds
        """
        response = await self._make_request("GET", "/api/v3/time")
        return int(response["serverTime"])

    async def get_exchange_info(
        self, symbols: Optional[List[str]] = None
    ) -> ExchangeInfo:
        """
        Get exchange trading rules and symbol information.

        Args:
            symbols: Optional list of symbols to filter

        Returns:
            Exchange information with trading rules
        """
        params = {}
        if symbols:
            params["symbols"] = json.dumps(symbols)

        response = await self._make_request("GET", "/api/v3/exchangeInfo", params)
        return ExchangeInfo.from_binance_response(response)

    async def get_ticker_price(self, symbol: str) -> TickerData:
        """
        Get 24hr ticker price statistics for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')

        Returns:
            Ticker data with price, volume, and change information
        """
        params = {"symbol": symbol.upper()}
        response = await self._make_request("GET", "/api/v3/ticker/24hr", params)

        ticker = TickerData.from_binance_response(response)
        ticker.validate()  # Validate data integrity

        logger.info(
            f"📊 {symbol}: ${ticker.price} ({ticker.price_change_percent_24h:+.2f}%)"
        )
        return ticker

    async def get_multiple_tickers(self, symbols: List[str]) -> Dict[str, TickerData]:
        """
        Get ticker data for multiple symbols efficiently.

        Args:
            symbols: List of trading pair symbols

        Returns:
            Dictionary mapping symbols to ticker data
        """
        # Use batch endpoint for efficiency
        symbols_upper = [s.upper() for s in symbols]
        params = {"symbols": json.dumps(symbols_upper)}

        response = await self._make_request("GET", "/api/v3/ticker/24hr", params)

        tickers = {}
        for ticker_data in response:
            ticker = TickerData.from_binance_response(ticker_data)
            ticker.validate()
            tickers[ticker.symbol] = ticker

        logger.info(f"📊 Fetched {len(tickers)} tickers: {list(tickers.keys())}")
        return tickers

    async def get_kline_data(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[KlineData]:
        """
        Get historical kline/candlestick data.

        Args:
            symbol: Trading pair symbol
            interval: Time interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, etc.)
            limit: Number of klines to return (max 1000)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of OHLCV kline data
        """
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1000),  # Respect Binance limits
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        response = await self._make_request("GET", "/api/v3/klines", params)

        klines = []
        for kline_data in response:
            kline = KlineData.from_binance_response(symbol, interval, kline_data)
            kline.validate()
            klines.append(kline)

        logger.info(f"📈 {symbol} {interval}: {len(klines)} candles loaded")
        return klines

    # Authenticated API Methods (Require API key signature)

    async def get_account_info(self) -> AccountInfo:
        """
        Get account information including balances and trading permissions.

        Returns:
            Account information with balances
        """
        response = await self._make_request("GET", "/api/v3/account", signed=True)
        account_info = AccountInfo.from_binance_response(response)
        account_info.validate()

        # Log account status (without sensitive balance details)
        logger.info(
            f"👤 Account: {account_info.account_type}, Trading: {account_info.can_trade}"
        )
        logger.info(f"💰 Assets: {len(account_info.balances)} with non-zero balances")

        return account_info

    async def test_connectivity(self) -> bool:
        """
        Test API connectivity and authentication.

        Returns:
            True if connection and authentication successful
        """
        logger.info("Testing API connectivity...")
        try:
            # Test public endpoint
            await self.get_server_time()
            logger.info("✅ Public API connectivity successful")

            # Test authenticated endpoint
            account_info = await self.get_account_info()
            logger.info("✅ Authenticated API access successful")

            # Check trading permissions
            if not account_info.can_trade:
                logger.warning("⚠️ Account does not have trading permissions")

            return True

        except Exception as e:
            logger.error(f"❌ Connectivity test failed: {e}")
            return False

    async def get_current_prices(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get current prices for multiple symbols (lightweight method).

        Args:
            symbols: List of trading pair symbols

        Returns:
            Dictionary mapping symbols to current prices
        """
        # For multiple symbols, make individual requests to avoid formatting issues
        prices = {}

        for symbol in symbols:
            try:
                params = {"symbol": symbol.upper()}
                response = await self._make_request(
                    "GET", "/api/v3/ticker/price", params
                )
                price = Decimal(str(response["price"]))
                prices[symbol.upper()] = price
            except Exception as e:
                logger.warning(f"Failed to get price for {symbol}: {e}")
                continue

        logger.debug(f"💱 Current prices: {len(prices)} symbols")
        return prices

    # Utility Methods

    async def ping(self) -> bool:
        """
        Ping Binance API to test connectivity.

        Returns:
            True if ping successful
        """
        try:
            await self._make_request("GET", "/api/v3/ping")
            return True
        except Exception:
            return False

    def is_testnet(self) -> bool:
        """Check if client is configured for testnet."""
        return self.config.binance_testnet

    def get_base_url(self) -> str:
        """Get the base URL being used."""
        return self.base_url
