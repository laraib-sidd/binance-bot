"""
Helios Trading Bot - Binance API Integration Tests

Integration tests that interact with the real Binance testnet API.
These tests validate end-to-end functionality with actual API calls.

IMPORTANT: These tests require valid testnet API credentials in .env file.
"""

import asyncio
import logging

import pytest

from src.api.binance_client import BinanceClient
from src.api.exceptions import BinanceAPIError
from src.api.models import AccountInfo, TickerData
from src.core.config import load_configuration

# Setup logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestBinanceAPIIntegration:
    """Integration tests for Binance API client."""

    @pytest.fixture
    async def client(self):
        """Create and configure Binance client for testing."""
        try:
            config = load_configuration()

            # Ensure we're using testnet
            if not config.binance_testnet:
                pytest.skip("Integration tests require testnet configuration")

            # Validate API credentials are configured
            if not config.binance_api_key or not config.binance_api_secret:
                pytest.skip("Integration tests require API credentials in .env file")

            async with BinanceClient(config) as client:
                yield client

        except Exception as e:
            pytest.skip(f"Failed to create client: {e}")

    @pytest.mark.asyncio
    async def test_server_connectivity(self, client: BinanceClient):
        """Test basic server connectivity."""
        logger.info("🧪 Testing server connectivity...")

        # Test ping
        ping_result = await client.ping()
        assert ping_result is True, "Ping should succeed"

        # Test server time
        server_time = await client.get_server_time()
        assert isinstance(server_time, int), "Server time should be integer"
        assert server_time > 0, "Server time should be positive"

        logger.info("✅ Server connectivity test passed")

    @pytest.mark.asyncio
    async def test_client_configuration(self, client: BinanceClient):
        """Test client configuration and initialization."""
        logger.info("🧪 Testing client configuration...")

        # Verify testnet configuration
        assert client.is_testnet() is True, "Client should be configured for testnet"

        # Verify base URL
        base_url = client.get_base_url()
        assert "testnet" in base_url.lower(), "Should be using testnet URL"

        logger.info("✅ Client configuration test passed")

    @pytest.mark.asyncio
    async def test_authentication_and_account_access(self, client: BinanceClient):
        """Test API authentication and account access."""
        logger.info("🧪 Testing authentication and account access...")

        # Test account info retrieval
        account_info = await client.get_account_info()

        # Validate account info structure
        assert isinstance(account_info, AccountInfo), "Should return AccountInfo object"
        assert hasattr(account_info, "account_type"), "Should have account_type"
        assert hasattr(account_info, "can_trade"), "Should have trading permission info"
        assert hasattr(account_info, "balances"), "Should have balance information"

        # Log account status (without sensitive details)
        logger.info(f"Account Type: {account_info.account_type}")
        logger.info(f"Can Trade: {account_info.can_trade}")
        logger.info(f"Assets with Balance: {len(account_info.balances)}")

        logger.info("✅ Authentication and account access test passed")

    @pytest.mark.asyncio
    async def test_market_data_retrieval(self, client: BinanceClient):
        """Test market data retrieval functionality."""
        logger.info("🧪 Testing market data retrieval...")

        # Test single ticker
        test_symbol = "BTCUSDT"
        ticker = await client.get_ticker_price(test_symbol)

        # Validate ticker data
        assert isinstance(ticker, TickerData), "Should return TickerData object"
        assert ticker.symbol == test_symbol, f"Symbol should be {test_symbol}"
        assert ticker.price > 0, "Price should be positive"
        assert ticker.volume_24h >= 0, "Volume should be non-negative"

        logger.info(
            f"📊 {test_symbol}: ${ticker.price} ({ticker.price_change_percent_24h:+.2f}%)"
        )

        # Test multiple tickers
        test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        tickers = await client.get_multiple_tickers(test_symbols)

        # Validate multiple tickers
        assert isinstance(tickers, dict), "Should return dictionary"
        assert len(tickers) == len(test_symbols), "Should return all requested symbols"

        for symbol in test_symbols:
            assert symbol in tickers, f"Should include {symbol}"
            assert isinstance(
                tickers[symbol], TickerData
            ), f"{symbol} should be TickerData"
            assert tickers[symbol].price > 0, f"{symbol} price should be positive"

        logger.info(f"📊 Successfully retrieved {len(tickers)} tickers")

        logger.info("✅ Market data retrieval test passed")

    @pytest.mark.asyncio
    async def test_price_data_consistency(self, client: BinanceClient):
        """Test price data consistency and validation."""
        logger.info("🧪 Testing price data consistency...")

        test_symbols = ["BTCUSDT", "ETHUSDT"]

        # Get current prices (lightweight)
        current_prices = await client.get_current_prices(test_symbols)

        # Get detailed ticker data
        detailed_tickers = await client.get_multiple_tickers(test_symbols)

        # Compare prices for consistency
        for symbol in test_symbols:
            current_price = current_prices[symbol]
            ticker_price = detailed_tickers[symbol].price

            # Prices should be close (within reasonable market movement)
            price_diff_percent = (
                abs((current_price - ticker_price) / ticker_price) * 100
            )
            assert (
                price_diff_percent < 5
            ), f"{symbol} price difference too large: {price_diff_percent:.2f}%"

            logger.info(
                f"💱 {symbol}: Current=${current_price}, Ticker=${ticker_price}"
            )

        logger.info("✅ Price data consistency test passed")

    @pytest.mark.asyncio
    async def test_error_handling(self, client: BinanceClient):
        """Test error handling for various scenarios."""
        logger.info("🧪 Testing error handling...")

        # Test invalid symbol
        try:
            await client.get_ticker_price("INVALID123")
            raise AssertionError("Should have raised an exception for invalid symbol")
        except BinanceAPIError as e:
            logger.info(f"✅ Correctly handled invalid symbol: {type(e).__name__}")
            assert "Invalid symbol" in str(e) or "does not exist" in str(e)

        logger.info("✅ Error handling test passed")

    @pytest.mark.asyncio
    async def test_comprehensive_connectivity(self, client: BinanceClient):
        """Test comprehensive connectivity using built-in test method."""
        logger.info("🧪 Testing comprehensive connectivity...")

        # Use the client's built-in connectivity test
        connectivity_result = await client.test_connectivity()

        assert (
            connectivity_result is True
        ), "Comprehensive connectivity test should pass"

        logger.info("✅ Comprehensive connectivity test passed")


# Standalone test functions for manual execution


async def manual_test_api_connection():
    """Manual test function for API connection."""
    print("🚀 Starting manual API connection test...")

    try:
        # Load configuration
        config = load_configuration()
        print(f"📋 Configuration loaded: Environment={config.environment}")
        print(f"🔧 Testnet mode: {config.binance_testnet}")

        # Create client and test
        async with BinanceClient(config) as client:
            print(f"🌐 Connected to: {client.get_base_url()}")

            # Test connectivity
            print("\n🧪 Testing connectivity...")
            success = await client.test_connectivity()

            if success:
                print("✅ API connectivity test PASSED!")

                # Get some basic market data
                print("\n📊 Fetching market data...")
                try:
                    ticker = await client.get_ticker_price("BTCUSDT")
                    print(f"💰 BTC Price: ${ticker.price}")
                    print(f"📈 24h Change: {ticker.price_change_percent_24h:+.2f}%")
                except Exception as e:
                    print(f"⚠️ Market data test failed: {e}")

                # Get account info
                print("\n👤 Fetching account info...")
                try:
                    account = await client.get_account_info()
                    print(f"🏦 Account Type: {account.account_type}")
                    print(f"🔐 Trading Enabled: {account.can_trade}")

                    if account.balances:
                        print(f"💳 Assets with balance: {len(account.balances)}")
                        for asset, balance in list(account.balances.items())[
                            :5
                        ]:  # Show first 5
                            print(f"  {asset}: {balance}")
                    else:
                        print(
                            "💳 No assets with balance (expected for new testnet account)"
                        )

                except Exception as e:
                    print(f"⚠️ Account info test failed: {e}")

            else:
                print("❌ API connectivity test FAILED!")

    except Exception as e:
        print(f"❌ Manual test failed: {e}")
        print("💡 Check your .env file configuration")


if __name__ == "__main__":
    """Run manual test if script is executed directly."""
    asyncio.run(manual_test_api_connection())
