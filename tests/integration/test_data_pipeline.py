"""
Integration Tests for Data Pipeline

Tests the complete data pipeline flow:
- Connection managers (PostgreSQL, Redis, R2)
- Database schema creation and validation
- Market data pipeline end-to-end
- Data quality and monitoring
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

import asyncpg
import pytest

from src.api.models import TickerData
from src.core.environment import get_config
from src.data.connection_managers import ConnectionManager
from src.data.database_schema import DatabaseSchema, initialize_database
from src.data.market_data_pipeline import MarketDataPipeline


class TestConnectionManagers:
    """Test connection managers for all services."""

    @pytest.fixture
    async def connection_manager(self):
        """Create connection manager for testing."""
        manager = ConnectionManager()
        await manager.connect_all()
        yield manager
        await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_postgresql_connection(self):
        """Test PostgreSQL connection and basic operations."""
        manager = ConnectionManager()
        await manager.postgres.connect()

        try:
            # Test basic query
            result = await manager.postgres.fetchval("SELECT 1")
            assert result == 1

            # Test health check
            health = await manager.postgres.health_check()
            assert health.is_healthy
            assert health.service == "postgresql"
            assert health.response_time_ms > 0

        finally:
            await manager.postgres.disconnect()

    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Test Redis connection and caching operations."""
        manager = ConnectionManager()
        await manager.redis.connect()

        try:
            # Test basic operations
            test_key = "test:pipeline:key"
            test_value = "test_value_123"

            # Set and get
            await manager.redis.set(test_key, test_value, ex=30)
            retrieved = await manager.redis.get(test_key)
            assert retrieved == test_value

            # Check existence
            exists = await manager.redis.exists(test_key)
            assert exists is True

            # Delete
            deleted = await manager.redis.delete(test_key)
            assert deleted == 1

            # Verify deletion
            exists_after = await manager.redis.exists(test_key)
            assert exists_after is False

            # Test pipeline operations
            pipeline_data = {
                "test:pipeline:1": "value1",
                "test:pipeline:2": "value2",
                "test:pipeline:3": "value3",
            }

            await manager.redis.pipeline_set(pipeline_data, ttl=60)

            # Verify pipeline data
            for key, expected_value in pipeline_data.items():
                value = await manager.redis.get(key)
                assert value == expected_value
                await manager.redis.delete(key)  # Cleanup

            # Test health check
            health = await manager.redis.health_check()
            assert health.is_healthy
            assert health.service == "redis"

        finally:
            await manager.redis.disconnect()

    @pytest.mark.asyncio
    async def test_r2_connection(self):
        """Test R2 connection and basic operations."""
        manager = ConnectionManager()
        await manager.r2.connect()

        try:
            # Test basic operations
            test_key = f"test/pipeline/{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            test_data = b"Test data for R2 integration test"

            # Upload object
            upload_success = await manager.r2.upload_object(
                key=test_key, data=test_data, content_type="text/plain"
            )
            assert upload_success is True

            # Download object
            downloaded_data = await manager.r2.download_object(test_key)
            assert downloaded_data == test_data

            # List objects
            objects = await manager.r2.list_objects(
                prefix="test/pipeline/", max_keys=10
            )
            assert test_key in objects

            # Delete object
            delete_success = await manager.r2.delete_object(test_key)
            assert delete_success is True

            # Verify deletion
            downloaded_after_delete = await manager.r2.download_object(test_key)
            assert downloaded_after_delete is None

            # Test health check
            health = await manager.r2.health_check()
            assert health.is_healthy
            assert health.service == "r2"

        finally:
            pass  # R2 doesn't need explicit disconnect

    @pytest.mark.asyncio
    async def test_connection_manager_lifecycle(self, connection_manager):
        """Test connection manager full lifecycle."""
        # Test all services are connected
        assert connection_manager.is_connected

        # Test health check for all services
        health_status = await connection_manager.health_check_all()

        for service, health in health_status.items():
            assert (
                health.is_healthy
            ), f"{service} is not healthy: {health.error_message}"
            assert health.response_time_ms > 0
            assert health.service == service


class TestDatabaseSchema:
    """Test database schema creation and validation."""

    @pytest.fixture
    async def db_schema(self):
        """Create database schema for testing."""
        schema = DatabaseSchema()
        await schema.initialize()
        return schema

    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test database schema initialization."""
        # Initialize database
        success = await initialize_database()
        assert success is True

        # Verify schema
        schema = DatabaseSchema()
        verification = await schema.verify_schema()

        assert verification["tables_exist"] is True
        assert verification["indexes_exist"] is True
        assert verification["tables_count"] >= 8  # All expected tables
        assert len(verification["missing_tables"]) == 0

    @pytest.mark.asyncio
    async def test_schema_verification(self, db_schema):
        """Test schema verification functionality."""
        # Create all tables
        await db_schema.create_all_tables()

        # Verify schema
        verification = await db_schema.verify_schema()

        # Check results
        assert verification["tables_exist"] is True
        assert verification["tables_count"] >= 8
        assert "current_prices" not in verification["missing_tables"]
        assert "ohlcv_1m" not in verification["missing_tables"]
        assert "trading_sessions" not in verification["missing_tables"]

    @pytest.mark.asyncio
    async def test_table_stats(self, db_schema):
        """Test table statistics gathering."""
        await db_schema.create_all_tables()

        stats = await db_schema.get_table_stats()

        assert "row_counts" in stats
        assert "total_rows" in stats
        assert isinstance(stats["row_counts"], dict)
        assert stats["total_rows"] >= 0

        # Check that all expected tables are in stats
        expected_tables = ["current_prices", "ohlcv_1m", "trading_sessions"]
        for table in expected_tables:
            assert table in stats["row_counts"]

    @pytest.mark.asyncio
    async def test_data_validation_constraints(self, db_schema):
        """Test database constraints and validation."""
        await db_schema.create_all_tables()

        # Test inserting valid data
        valid_insert = """
        INSERT INTO current_prices (
            symbol, price, timestamp
        ) VALUES ('BTCUSDT', 50000.50, CURRENT_TIMESTAMP)
        """

        await db_schema.connection_manager.postgres.execute(valid_insert)

        # Verify data was inserted
        count = await db_schema.connection_manager.postgres.fetchval(
            "SELECT COUNT(*) FROM current_prices WHERE symbol = 'BTCUSDT'"
        )
        assert count == 1

        # Test constraint violation (negative price should fail)
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            invalid_insert = """
            INSERT INTO current_prices (
                symbol, price, timestamp
            ) VALUES ('ETHUSDT', -100.00, CURRENT_TIMESTAMP)
            """
            await db_schema.connection_manager.postgres.execute(invalid_insert)

        # Cleanup
        await db_schema.connection_manager.postgres.execute(
            "DELETE FROM current_prices WHERE symbol = 'BTCUSDT'"
        )

    @pytest.mark.asyncio
    async def test_current_price_operations(self, db_schema):
        """Test basic current price operations."""
        await db_schema.create_all_tables()

        # Insert test data
        await db_schema.connection_manager.postgres.execute(
            """INSERT INTO current_prices
               (symbol, price, timestamp)
               VALUES ('TESTUSDT', 123.45, CURRENT_TIMESTAMP)
               ON CONFLICT (symbol) DO UPDATE SET price = EXCLUDED.price"""
        )

        # Verify data
        result = await db_schema.connection_manager.postgres.fetchrow(
            "SELECT * FROM current_prices WHERE symbol = 'TESTUSDT'"
        )

        assert result is not None
        assert result["symbol"] == "TESTUSDT"
        assert float(result["price"]) == 123.45


class TestMarketDataPipeline:
    """Test complete market data pipeline."""

    @pytest.fixture
    async def pipeline(self):
        """Create market data pipeline for testing."""
        pipeline = MarketDataPipeline()
        pipeline.symbols = ["BTCUSDT"]  # Use single symbol for testing
        await pipeline.initialize()
        yield pipeline
        await pipeline.stop_pipeline()

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = MarketDataPipeline()
        await pipeline.initialize()

        assert pipeline.connection_manager is not None
        assert pipeline.binance_client is not None
        assert pipeline.connection_manager.is_connected

        # Check health
        health = await pipeline.get_pipeline_health()
        assert health["status"] in ["running", "stopped"]
        assert "connections" in health
        assert "metrics" in health

    @pytest.mark.asyncio
    async def test_current_price_storage(self, pipeline):
        """Test storing current price data."""
        # Create test ticker data
        test_ticker = TickerData(
            symbol="BTCUSDT",
            price=Decimal("50000.25"),
            bid_price=Decimal("50000.00"),
            ask_price=Decimal("50000.50"),
            volume_24h=Decimal("1234.56"),
            price_change_24h=Decimal("1500.00"),
            price_change_percent_24h=Decimal("3.09"),
            high_24h=Decimal("51000.00"),
            low_24h=Decimal("48500.00"),
            timestamp=datetime.now(timezone.utc),
        )

        # Process through pipeline
        await pipeline._process_single_ticker("BTCUSDT", test_ticker)

        # Verify data was stored in PostgreSQL
        stored_price = await pipeline.connection_manager.postgres.fetchrow(
            "SELECT * FROM current_prices WHERE symbol = 'BTCUSDT'"
        )

        assert stored_price is not None
        assert Decimal(str(stored_price["price"])) == test_ticker.price
        assert stored_price["symbol"] == "BTCUSDT"

        # Verify data was cached in Redis
        cached_price = await pipeline.connection_manager.redis.get("price:BTCUSDT")
        assert cached_price is not None
        assert Decimal(cached_price) == test_ticker.price

        # Verify ticker JSON was cached
        ticker_json = await pipeline.connection_manager.redis.get("ticker:BTCUSDT")
        assert ticker_json is not None
        ticker_data = json.loads(ticker_json)
        assert ticker_data["symbol"] == "BTCUSDT"
        assert Decimal(ticker_data["price"]) == test_ticker.price

    @pytest.mark.asyncio
    async def test_data_quality_monitoring(self, pipeline):
        """Test data quality monitoring."""
        # Create test ticker with poor quality data
        poor_quality_ticker = TickerData(
            symbol="TESTUSDT",
            price=Decimal("100.00"),
            bid_price=None,  # Missing bid price
            ask_price=None,  # Missing ask price
            volume_24h=Decimal("0"),  # Zero volume
            price_change_24h=Decimal("0"),
            price_change_percent_24h=Decimal("0"),
            high_24h=Decimal("100.00"),
            low_24h=Decimal("100.00"),
            timestamp=datetime.now(timezone.utc)
            - timedelta(minutes=10),  # Old timestamp
        )

        # Process through pipeline
        await pipeline._process_single_ticker("TESTUSDT", poor_quality_ticker)

        # Check data quality metrics were stored
        quality_metrics = await pipeline.connection_manager.postgres.fetch(
            "SELECT * FROM data_quality_metrics WHERE symbol = 'TESTUSDT' ORDER BY timestamp DESC LIMIT 1"
        )

        assert len(quality_metrics) > 0
        metric = quality_metrics[0]
        assert metric["symbol"] == "TESTUSDT"
        assert metric["metric_type"] == "ticker_update"
        assert metric["quality_score"] < 1.0  # Should be less than perfect
        assert metric["alert_level"] in ["warning", "error"]  # Should trigger alert

    @pytest.mark.asyncio
    async def test_get_current_price_fallback(self, pipeline):
        """Test current price retrieval with fallback."""
        # Store test data in PostgreSQL
        await pipeline.connection_manager.postgres.execute(
            "INSERT INTO current_prices (symbol, price, timestamp) VALUES ('FALLBACKUSDT', 123.45, CURRENT_TIMESTAMP) ON CONFLICT (symbol) DO UPDATE SET price = EXCLUDED.price",
        )

        # Clear Redis cache to test PostgreSQL fallback
        await pipeline.connection_manager.redis.delete("price:FALLBACKUSDT")

        # Get price (should fallback to PostgreSQL)
        price = await pipeline.get_current_price("FALLBACKUSDT")

        assert price is not None
        assert price == Decimal("123.45")

        # Now cache the price in Redis
        await pipeline.connection_manager.redis.set(
            "price:FALLBACKUSDT", "456.78", ex=300
        )

        # Get price again (should use Redis cache)
        cached_price = await pipeline.get_current_price("FALLBACKUSDT")

        assert cached_price == Decimal("456.78")  # Should get Redis value

    @pytest.mark.asyncio
    async def test_historical_data_processing(self, pipeline):
        """Test historical data fetching and storage."""
        # This test requires actual Binance API access
        # Skip if running in CI/CD without API keys
        try:
            klines = await pipeline.fetch_historical_data("BTCUSDT", "1m", 10)

            if klines:  # Only test if we got data
                assert len(klines) <= 10
                assert all(kline.symbol == "BTCUSDT" for kline in klines)

                # Verify data was stored in PostgreSQL
                stored_data = await pipeline.get_recent_ohlcv("BTCUSDT", "1m", 5)
                assert len(stored_data) > 0

        except Exception as e:
            # Skip test if API access fails
            pytest.skip(f"Skipping historical data test due to API error: {e}")

    @pytest.mark.asyncio
    async def test_pipeline_metrics(self, pipeline):
        """Test that pipeline metrics are correctly updated."""
        # Get initial metrics
        initial_health = await pipeline.get_pipeline_health()
        assert initial_health["metrics"]["total_updates"] == 0

        # Process some test data
        await pipeline._process_current_prices()

        # Check that metrics have been updated
        updated_health = await pipeline.get_pipeline_health()
        updated_metrics = updated_health["metrics"]

        assert updated_metrics["successful_updates"] > 0
        assert updated_metrics["last_update"] is not None
        assert updated_metrics["avg_processing_time"] >= 0

    @pytest.mark.asyncio
    async def test_db_constraints(self, pipeline):
        """Test database constraints are enforced."""
        # Test constraint violation (negative price should fail)
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            invalid_insert = """
            INSERT INTO helios_trading.current_prices (
                symbol, price, bid_price, ask_price, volume_24h,
                price_change_24h, price_change_percent_24h, high_24h, low_24h, timestamp
            ) VALUES ('ETHUSDT', -100.00, NULL, NULL, 0, 0, 0, 100, 100, CURRENT_TIMESTAMP)
            """
            await pipeline.connection_manager.postgres.execute(invalid_insert)

    @pytest.mark.asyncio
    async def test_pipeline_health_check(self, pipeline):
        """Test the pipeline health check functionality."""
        # Get initial metrics
        initial_health = await pipeline.get_pipeline_health()
        assert initial_health["status"] == "running"

        # Process some test data
        await pipeline._process_current_prices()

        # Check that metrics have been updated
        updated_health = await pipeline.get_pipeline_health()
        updated_metrics = updated_health["metrics"]

        assert updated_metrics["successful_updates"] > 0
        assert updated_metrics["last_update"] is not None
        assert updated_metrics["avg_processing_time"] >= 0


class TestEndToEndIntegration:
    """Test complete end-to-end data pipeline integration."""

    @pytest.mark.asyncio
    async def test_complete_data_flow(self):
        """Test complete data flow from API to storage."""
        # Initialize pipeline
        pipeline = MarketDataPipeline()
        pipeline.symbols = ["BTCUSDT"]
        await pipeline.initialize()

        try:
            # Simulate receiving ticker data
            test_ticker = TickerData(
                symbol="BTCUSDT",
                price=Decimal("50000.0"),
                bid_price=Decimal("49999.0"),
                ask_price=Decimal("50001.0"),
                volume_24h=Decimal("1500.5"),
                price_change_24h=Decimal("750.0"),
                price_change_percent_24h=Decimal("1.52"),
                high_24h=Decimal("50500.0"),
                low_24h=Decimal("49200.0"),
                timestamp=datetime.now(timezone.utc),
            )

            # Process through complete pipeline
            await pipeline._process_single_ticker("BTCUSDT", test_ticker)

            # Verify data exists in PostgreSQL
            pg_data = await pipeline.connection_manager.postgres.fetchrow(
                "SELECT * FROM current_prices WHERE symbol = 'BTCUSDT'"
            )
            assert pg_data is not None
            assert Decimal(str(pg_data["price"])) == test_ticker.price

            # Verify data exists in Redis
            redis_price = await pipeline.connection_manager.redis.get("price:BTCUSDT")
            assert redis_price is not None
            assert Decimal(redis_price) == test_ticker.price

            # Verify data quality was recorded
            quality_data = await pipeline.connection_manager.postgres.fetch(
                "SELECT * FROM data_quality_metrics WHERE symbol = 'BTCUSDT' ORDER BY timestamp DESC LIMIT 1"
            )
            assert len(quality_data) > 0

            # Test price retrieval
            retrieved_price = await pipeline.get_current_price("BTCUSDT")
            assert retrieved_price == test_ticker.price

            # Test health check
            health = await pipeline.get_pipeline_health()
            assert health["status"] in ["running", "stopped"]
            assert all(conn.is_healthy for conn in health["connections"].values())

        finally:
            await pipeline.stop_pipeline()

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test pipeline error handling and recovery."""
        pipeline = MarketDataPipeline()
        await pipeline.initialize()

        try:
            # Test handling of invalid ticker data
            invalid_ticker = TickerData(
                symbol="INVALID",
                price=Decimal("-100"),  # Invalid negative price
                bid_price=None,
                ask_price=None,
                volume_24h=None,
                price_change_24h=None,
                price_change_percent_24h=None,
                high_24h=None,
                low_24h=None,
                timestamp=None,
            )

            # This should not crash the pipeline
            try:
                await pipeline._process_single_ticker("INVALID", invalid_ticker)
            except Exception as e:
                # Expected to fail, but pipeline should handle gracefully
                assert "price_positive" in str(e) or "constraint" in str(e).lower()

            # Pipeline should still be functional for valid data
            valid_ticker = TickerData(
                symbol="VALIDUSDT",
                price=Decimal("100.0"),
                bid_price=Decimal("99.9"),
                ask_price=Decimal("100.1"),
                volume_24h=Decimal("1000.0"),
                price_change_24h=Decimal("1.0"),
                price_change_percent_24h=Decimal("1.01"),
                high_24h=Decimal("101.0"),
                low_24h=Decimal("99.0"),
                timestamp=datetime.now(timezone.utc),
            )

            # This should work fine
            await pipeline._process_single_ticker("VALIDUSDT", valid_ticker)

            # Verify valid data was processed
            price = await pipeline.get_current_price("VALIDUSDT")
            assert price == Decimal("100.0")

        finally:
            await pipeline.stop_pipeline()


# Test configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def cleanup_test_data():
    """Cleanup test data after each test."""
    yield

    # Cleanup any test data created during tests
    try:
        manager = ConnectionManager()
        await manager.connect_all()

        # Clean up test symbols
        test_symbols = [
            "BTCUSDT",
            "TESTUSDT",
            "FALLBACKUSDT",
            "METRICSUSDT",
            "VALIDUSDT",
            "INVALID",
        ]

        for symbol in test_symbols:
            await manager.postgres.execute(
                "DELETE FROM current_prices WHERE symbol = $1", symbol
            )
            await manager.postgres.execute(
                "DELETE FROM data_quality_metrics WHERE symbol = $1", symbol
            )
            await manager.redis.delete(f"price:{symbol}")
            await manager.redis.delete(f"ticker:{symbol}")

        await manager.disconnect_all()

    except Exception as e:
        # Cleanup failures shouldn't fail the tests
        print(f"Cleanup warning: {e}")


# Skip integration tests if no credentials
@pytest.fixture(autouse=True)
def skip_if_no_credentials():
    """Skip integration tests if credentials are not available."""
    try:
        config = get_config()

        if not all(
            [
                config.get_postgresql_url(),
                config.get_redis_url(),
                config.r2_account_id,
                config.r2_api_token,
            ]
        ):
            pytest.skip("Integration tests require valid credentials")
    except Exception:
        pytest.skip("Cannot load configuration for integration tests")
