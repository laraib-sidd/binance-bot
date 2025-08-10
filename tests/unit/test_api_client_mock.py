"""
Helios Trading Bot - Mocked Binance API Client Tests

Unit tests using mocked BinanceClient for fast, reliable testing
without network dependencies or API keys.
"""

from decimal import Decimal
import time
from unittest.mock import patch

import pytest

from src.api.binance_client import BinanceClient
from src.api.exceptions import BinanceAPIError, NetworkError
from src.api.models import AccountInfo, KlineData, TickerData
from src.core.config import TradingConfig


@pytest.fixture
def mock_config() -> TradingConfig:
    """Create a mock configuration for testing."""
    return TradingConfig(
        binance_api_key="test_api_key_64_chars_long_abcdefghijklmnopqrstuvwxyz1234",
        binance_api_secret="test_secret_64_chars_long_abcdefghijklmnopqrstuvwxyz1234",
        binance_testnet=True,
        environment="test",
        # Add minimal required database config to pass validation
        neon_host="test_host",
        neon_database="test_db",
        neon_username="test_user",
        neon_password="test_pass",
        upstash_redis_host="test_redis",
        upstash_redis_password="test_redis_pass",
        r2_account_id="test_account",
        r2_access_key="test_access",
        r2_secret_key="test_secret",
        r2_bucket_name="test_bucket",
    )


@pytest.fixture
def mock_ticker_data() -> dict:
    """Create mock ticker data for testing."""
    # Use current timestamp to avoid validation errors
    current_time_ms = int(time.time() * 1000)
    return {
        "symbol": "BTCUSDT",
        "lastPrice": "45000.50",  # Correct field name for TickerData
        "bidPrice": "44999.00",
        "askPrice": "45001.00",
        "volume": "1234567.89",
        "priceChange": "500.50",
        "priceChangePercent": "1.13",
        "highPrice": "45500.00",
        "lowPrice": "44000.00",
        "openTime": current_time_ms - 86400000,  # 24 hours ago
        "closeTime": current_time_ms,  # Current time
    }


@pytest.fixture
def mock_account_data() -> dict:
    """Create mock account data for testing."""
    return {
        "accountType": "SPOT",
        "canTrade": True,
        "canWithdraw": True,
        "canDeposit": True,
        "updateTime": 1640995200000,  # Required field for AccountInfo
        "totalWalletBalance": "11000.0",
        "totalUnrealizedProfit": "0.0",
        "balances": [
            {"asset": "BTC", "free": "1.0", "locked": "0.0"},
            {"asset": "USDT", "free": "10000.0", "locked": "0.0"},
        ],
    }


@pytest.fixture
def mock_kline_data() -> list[list[object]]:
    """Create mock kline data for testing."""
    return [
        [
            1640995200000,  # Open time
            "44000.00",  # Open
            "45000.00",  # High
            "43500.00",  # Low
            "44500.00",  # Close
            "1000.00",  # Volume
            1641001200000,  # Close time
            "44250000.00",  # Quote asset volume
            1000,  # Number of trades
            "500.00",  # Taker buy base asset volume
            "22125000.00",  # Taker buy quote asset volume
            "0",  # Ignore
        ]
    ]


class TestMockedBinanceClient:
    """Test BinanceClient with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_config: TradingConfig) -> None:
        """Test client initialization and configuration."""
        client = BinanceClient(mock_config)

        assert client.config == mock_config
        assert client.is_testnet() is True
        assert "testnet" in client.get_base_url().lower()

    @pytest.mark.asyncio
    async def test_get_server_time_success(self, mock_config: TradingConfig) -> None:
        """Test successful server time retrieval."""
        expected_time = 1640995200000

        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.return_value = {"serverTime": expected_time}

            client = BinanceClient(mock_config)
            result = await client.get_server_time()

            assert result == expected_time
            mock_request.assert_called_once_with("GET", "/api/v3/time")

    @pytest.mark.asyncio
    async def test_get_ticker_price_success(
        self, mock_config: TradingConfig, mock_ticker_data: dict
    ) -> None:
        """Test successful ticker price retrieval."""
        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.return_value = mock_ticker_data

            client = BinanceClient(mock_config)
            result = await client.get_ticker_price("BTCUSDT")

            assert isinstance(result, TickerData)
            assert result.symbol == "BTCUSDT"
            assert result.price == Decimal("45000.50")
            assert result.bid_price == Decimal("44999.00")
            assert result.ask_price == Decimal("45001.00")

            mock_request.assert_called_once_with(
                "GET", "/api/v3/ticker/24hr", {"symbol": "BTCUSDT"}
            )

    @pytest.mark.asyncio
    async def test_get_multiple_tickers_success(
        self, mock_config: TradingConfig, mock_ticker_data: dict
    ) -> None:
        """Test successful multiple ticker retrieval."""
        symbols = ["BTCUSDT", "ETHUSDT"]
        # Create proper ETHUSDT data with matching price ranges
        eth_data = {**mock_ticker_data}
        eth_data.update(
            {
                "symbol": "ETHUSDT",
                "lastPrice": "3000.00",
                "bidPrice": "2999.00",
                "askPrice": "3001.00",
                "highPrice": "3100.00",
                "lowPrice": "2900.00",
            }
        )

        mock_response = [
            {**mock_ticker_data, "symbol": "BTCUSDT"},
            eth_data,
        ]

        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.return_value = mock_response

            client = BinanceClient(mock_config)
            result = await client.get_multiple_tickers(symbols)

            assert isinstance(result, dict)
            assert len(result) == 2
            assert "BTCUSDT" in result
            assert "ETHUSDT" in result
            assert result["BTCUSDT"].price == Decimal("45000.50")
            assert result["ETHUSDT"].price == Decimal("3000.00")

    @pytest.mark.asyncio
    async def test_get_account_info_success(
        self, mock_config: TradingConfig, mock_account_data: dict
    ) -> None:
        """Test successful account info retrieval."""
        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.return_value = mock_account_data

            client = BinanceClient(mock_config)
            result = await client.get_account_info()

            assert isinstance(result, AccountInfo)
            assert result.account_type == "SPOT"
            assert result.can_trade is True
            assert len(result.balances) == 2

            mock_request.assert_called_once_with("GET", "/api/v3/account", signed=True)

    @pytest.mark.asyncio
    async def test_get_kline_data_success(
        self, mock_config: TradingConfig, mock_kline_data: list[list[object]]
    ) -> None:
        """Test successful kline data retrieval."""
        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.return_value = mock_kline_data

            client = BinanceClient(mock_config)
            result = await client.get_kline_data("BTCUSDT", "1h", 100)

            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], KlineData)
            assert result[0].symbol == "BTCUSDT"
            assert result[0].open_price == Decimal("44000.00")
            assert result[0].close_price == Decimal("44500.00")

    @pytest.mark.asyncio
    async def test_get_current_prices_success(self, mock_config: TradingConfig) -> None:
        """Test successful current prices retrieval."""
        symbols = ["BTCUSDT", "ETHUSDT"]
        mock_responses = [
            {"price": "45000.50"},
            {"price": "3000.00"},
        ]

        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.side_effect = mock_responses

            client = BinanceClient(mock_config)
            result = await client.get_current_prices(symbols)

            assert isinstance(result, dict)
            assert len(result) == 2
            assert result["BTCUSDT"] == Decimal("45000.50")
            assert result["ETHUSDT"] == Decimal("3000.00")

    @pytest.mark.asyncio
    async def test_ping_success(self, mock_config: TradingConfig) -> None:
        """Test successful ping."""
        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.return_value = {}

            client = BinanceClient(mock_config)
            result = await client.ping()

            assert result is True
            mock_request.assert_called_once_with("GET", "/api/v3/ping")

    @pytest.mark.asyncio
    async def test_ping_failure(self, mock_config: TradingConfig) -> None:
        """Test ping failure handling."""
        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.side_effect = NetworkError("Network error")

            client = BinanceClient(mock_config)
            result = await client.ping()

            assert result is False

    @pytest.mark.asyncio
    async def test_test_connectivity_success(
        self, mock_config: TradingConfig, mock_account_data: dict
    ) -> None:
        """Test successful connectivity test."""
        with (
            patch.object(BinanceClient, "get_server_time") as mock_server_time,
            patch.object(BinanceClient, "get_account_info") as mock_account_info,
        ):
            mock_server_time.return_value = 1640995200000
            mock_account_info.return_value = AccountInfo.from_binance_response(
                mock_account_data
            )

            client = BinanceClient(mock_config)
            result = await client.test_connectivity()

            assert result is True
            mock_server_time.assert_called_once()
            mock_account_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connectivity_failure(self, mock_config: TradingConfig) -> None:
        """Test connectivity test failure handling."""
        with patch.object(BinanceClient, "get_server_time") as mock_server_time:
            mock_server_time.side_effect = BinanceAPIError("API error")

            client = BinanceClient(mock_config)
            result = await client.test_connectivity()

            assert result is False

    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_config: TradingConfig) -> None:
        """Test network error handling."""
        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.side_effect = NetworkError("Connection failed")

            client = BinanceClient(mock_config)

            with pytest.raises(NetworkError):
                await client.get_server_time()

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_config: TradingConfig) -> None:
        """Test API error handling."""
        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.side_effect = BinanceAPIError("Invalid symbol")

            client = BinanceClient(mock_config)

            with pytest.raises(BinanceAPIError):
                await client.get_ticker_price("INVALID")

    @pytest.mark.asyncio
    async def test_session_management(self, mock_config: TradingConfig) -> None:
        """Test HTTP session management."""
        client = BinanceClient(mock_config)

        # Test session creation
        await client._ensure_session()
        assert client._session is not None
        assert not client._session.closed

        # Test session cleanup
        await client.close()
        assert client._session.closed

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config: TradingConfig) -> None:
        """Test client as async context manager."""
        async with BinanceClient(mock_config) as client:
            assert client._session is not None
            assert not client._session.closed

        # Session should be closed after context exit
        assert client._session.closed

    @pytest.mark.asyncio
    async def test_signature_generation(self, mock_config: TradingConfig) -> None:
        """Test HMAC signature generation."""
        client = BinanceClient(mock_config)

        query_string = "symbol=BTCUSDT&timestamp=1640995200000"
        signature = client._generate_signature(query_string)

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest length

    @pytest.mark.asyncio
    async def test_query_string_building(self, mock_config: TradingConfig) -> None:
        """Test query string building."""
        client = BinanceClient(mock_config)

        params = {"symbol": "BTCUSDT", "limit": 100}
        query_string = client._build_query_string(params, include_timestamp=False)

        assert "symbol=BTCUSDT" in query_string
        assert "limit=100" in query_string
        assert "timestamp" not in query_string

        # Test with timestamp
        query_string_with_ts = client._build_query_string(
            params, include_timestamp=True
        )
        assert "timestamp=" in query_string_with_ts


class TestMockedDataValidation:
    """Test data validation with mocked responses."""

    @pytest.mark.asyncio
    async def test_ticker_validation_success(
        self, mock_config: TradingConfig, mock_ticker_data: dict
    ) -> None:
        """Test successful ticker data validation."""
        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.return_value = mock_ticker_data

            client = BinanceClient(mock_config)
            ticker = await client.get_ticker_price("BTCUSDT")

            # Should not raise validation errors
            ticker.validate()

    @pytest.mark.asyncio
    async def test_ticker_validation_failure(self, mock_config: TradingConfig) -> None:
        """Test ticker data validation failure."""
        current_time_ms = int(time.time() * 1000)
        invalid_ticker_data = {
            "symbol": "BTCUSDT",
            "lastPrice": "-100.00",  # Invalid negative price
            "bidPrice": "44999.00",
            "askPrice": "45001.00",
            "volume": "1234567.89",
            "priceChange": "500.50",
            "priceChangePercent": "1.13",
            "highPrice": "45500.00",
            "lowPrice": "44000.00",
            "openTime": current_time_ms - 86400000,
            "closeTime": current_time_ms,
        }

        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.return_value = invalid_ticker_data

            client = BinanceClient(mock_config)
            # This should raise validation error automatically in get_ticker_price
            with pytest.raises(ValueError, match="Invalid price"):
                await client.get_ticker_price("BTCUSDT")

    @pytest.mark.asyncio
    async def test_account_validation_success(
        self, mock_config: TradingConfig, mock_account_data: dict
    ) -> None:
        """Test successful account data validation."""
        with patch.object(BinanceClient, "_make_request") as mock_request:
            mock_request.return_value = mock_account_data

            client = BinanceClient(mock_config)
            account = await client.get_account_info()

            # Should not raise validation errors
            account.validate()
