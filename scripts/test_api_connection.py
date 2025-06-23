#!/usr/bin/env python3
"""
Helios Trading Bot - API Connection Test Script

Simple script to test Binance API connectivity with your testnet credentials.
This script will verify that your API keys work and the connection is successful.

Usage:
    uv run python scripts/test_api_connection.py
    # OR
    python scripts/test_api_connection.py

Requirements:
    - Valid testnet API keys in .env file
    - Internet connection
"""

import asyncio
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.binance_client import BinanceClient
from src.core.config import load_configuration


async def main():
    """Test API connection with user's credentials."""
    print("🚀 Helios Trading Bot - API Connection Test")
    print("=" * 50)

    try:
        # Load configuration
        print("📋 Loading configuration...")
        config = load_configuration()
        print(f"   Environment: {config.environment}")
        print(f"   Testnet mode: {config.binance_testnet}")

        if not config.binance_testnet:
            print("⚠️  WARNING: Not using testnet! This could access real money.")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != "y":
                print("Aborted for safety.")
                return

        # Create and test client
        print("\n🔗 Creating API client...")
        async with BinanceClient(config) as client:
            print(f"   Connected to: {client.get_base_url()}")

            # Test basic connectivity
            print("\n🧪 Testing basic connectivity...")
            ping_success = await client.ping()
            if ping_success:
                print("   ✅ Ping successful")
            else:
                print("   ❌ Ping failed")
                return

            # Test server time
            server_time = await client.get_server_time()
            print(f"   ✅ Server time: {server_time}")

            # Test authentication
            print("\n🔐 Testing authentication...")
            account_info = await client.get_account_info()
            print(f"   ✅ Account type: {account_info.account_type}")
            print(f"   ✅ Can trade: {account_info.can_trade}")
            print(f"   ✅ Assets with balance: {len(account_info.balances)}")

            # Show some balances (if any)
            if account_info.balances:
                print("\n💰 Account balances:")
                for asset, balance in list(account_info.balances.items())[:5]:
                    print(f"   {asset}: {balance}")
            else:
                print("   💡 No assets with balance (expected for new testnet account)")

            # Test market data
            print("\n📊 Testing market data...")
            try:
                ticker = await client.get_ticker_price("BTCUSDT")
                print(f"   ✅ BTC Price: ${ticker.price}")
                print(f"   ✅ 24h Change: {ticker.price_change_percent_24h:+.2f}%")

                # Test multiple symbols
                symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                prices = await client.get_current_prices(symbols)
                print(f"   ✅ Retrieved {len(prices)} prices:")
                for symbol, price in prices.items():
                    print(f"      {symbol}: ${price}")

            except Exception as e:
                print(f"   ⚠️ Market data test failed: {e}")

            # Overall connectivity test
            print("\n🔬 Running comprehensive connectivity test...")
            success = await client.test_connectivity()

            if success:
                print("\n🎉 ALL TESTS PASSED!")
                print("✅ Your API connection is working perfectly!")
                print("✅ Ready for Phase 1.2 completion!")
            else:
                print("\n❌ CONNECTIVITY TEST FAILED!")
                print("Please check your API keys and network connection.")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check your .env file has correct API keys")
        print("   2. Ensure API keys are from Binance testnet")
        print("   3. Verify internet connection")
        print("   4. Check that API keys have proper permissions")


if __name__ == "__main__":
    asyncio.run(main())
