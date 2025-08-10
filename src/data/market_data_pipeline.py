"""
Helios Trading Bot - Market Data Pipeline

Comprehensive data pipeline for market data flow:
API → Validation → PostgreSQL → Redis → R2

Features:
- Real-time market data ingestion from Binance
- Multi-tier storage (hot/warm/cold)
- Data validation and quality monitoring
- TTL-based caching with Redis
- Historical data archiving to R2
- Performance monitoring and health checks
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any, Dict, List, Optional, TypedDict

import polars as pl

from ..api.binance_client import BinanceClient
from ..api.models import KlineData, TickerData
from ..core.config import get_config
from ..core.constants import (
    DatabaseConstants,
    DataQualityConstants,
    RedisKeys,
    StorageConstants,
    TimeIntervals,
)
from ..utils.logging import get_logger
from .connection_managers import ConnectionManager, get_connection_manager
from .database_schema import initialize_database

logger = get_logger(__name__)

class MarketDataPipeline:
    """
    Main market data pipeline orchestrator.

    Manages the complete flow:
    Binance API → Validation → PostgreSQL → Redis → R2 Archive
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.connection_manager: Optional[ConnectionManager] = None
        self.binance_client: Optional[BinanceClient] = None
        self.is_running = False
        self.symbols = self.config.trading_symbols

        # Performance metrics
        class PipelineMetrics(TypedDict):
            total_updates: int
            successful_updates: int
            failed_updates: int
            last_update: Optional[datetime]
            avg_processing_time: float

        self.metrics: PipelineMetrics = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'last_update': None,
            'avg_processing_time': 0.0
        }

    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("Initializing market data pipeline...")

        # Initialize database schema
        await initialize_database()

        # Get connection manager
        self.connection_manager = await get_connection_manager()

        # Initialize Binance client
        self.binance_client = BinanceClient(self.config)

        logger.info("✅ Market data pipeline initialized")

    async def start_realtime_pipeline(self) -> None:
        """Start real-time market data pipeline."""
        if not self.connection_manager or not self.binance_client:
            await self.initialize()

        logger.info(f"🚀 Starting real-time pipeline for {len(self.symbols)} symbols")
        self.is_running = True

        try:
            while self.is_running:
                start_time = datetime.now()

                # Fetch current market data
                await self._process_current_prices()

                # Update metrics
                processing_time = (datetime.now() - start_time).total_seconds()
                self._update_metrics(processing_time)

                # Wait for next update cycle
                await asyncio.sleep(self.config.polling_interval_seconds)

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.is_running = False
            raise

    async def _process_current_prices(self) -> None:
        """Process current price data through the pipeline."""
        try:
            # Fetch data from Binance
            client = self.binance_client
            assert client is not None
            tickers = await client.get_multiple_tickers(self.symbols)

            if not tickers:
                logger.warning("No ticker data received from Binance")
                return

            # Process each ticker through the pipeline
            tasks = []
            for symbol, ticker_data in tickers.items():
                task = self._process_single_ticker(symbol, ticker_data)
                tasks.append(task)

            # Execute all updates in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successes/failures
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful

            self.metrics['successful_updates'] += successful
            self.metrics['failed_updates'] += failed

            if failed > 0:
                logger.warning(f"Failed to process {failed}/{len(results)} tickers")

        except Exception as e:
            logger.error(f"Failed to process current prices: {e}")
            self.metrics['failed_updates'] += len(self.symbols)

    async def _process_single_ticker(self, symbol: str, ticker_data: TickerData) -> None:
        """Process single ticker through the complete pipeline."""
        try:
            # Step 1: Store in PostgreSQL (warm storage)
            await self._store_current_price_postgres(symbol, ticker_data)

            # Step 2: Cache in Redis (hot storage)
            await self._cache_price_redis(symbol, ticker_data)

            # Step 3: Update data quality metrics
            await self._update_data_quality(symbol, ticker_data)

        except Exception as e:
            logger.error(f"Failed to process ticker {symbol}: {e}")
            raise

    async def _store_current_price_postgres(self, symbol: str, ticker_data: TickerData) -> None:
        """Store current price in PostgreSQL."""
        # Use configured schema rather than a hardcoded default
        schema = self.config.database_schema
        upsert_sql = f"""
        INSERT INTO {schema}.{DatabaseConstants.TABLE_CURRENT_PRICES} (
            symbol, price, bid_price, ask_price, volume_24h,
            price_change_24h, price_change_percent_24h,
            high_24h, low_24h, timestamp
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (symbol) DO UPDATE SET
            price = EXCLUDED.price,
            bid_price = EXCLUDED.bid_price,
            ask_price = EXCLUDED.ask_price,
            volume_24h = EXCLUDED.volume_24h,
            price_change_24h = EXCLUDED.price_change_24h,
            price_change_percent_24h = EXCLUDED.price_change_percent_24h,
            high_24h = EXCLUDED.high_24h,
            low_24h = EXCLUDED.low_24h,
            timestamp = EXCLUDED.timestamp,
            updated_at = CURRENT_TIMESTAMP
        """

        cm = self.connection_manager
        assert cm is not None
        await cm.postgres.execute(
            upsert_sql,
            symbol,
            ticker_data.price,
            ticker_data.bid_price,
            ticker_data.ask_price,
            ticker_data.volume_24h,
            ticker_data.price_change_24h,
            ticker_data.price_change_percent_24h,
            ticker_data.high_24h,
            ticker_data.low_24h,
            ticker_data.timestamp
        )

    async def _cache_price_redis(self, symbol: str, ticker_data: TickerData) -> None:
        """Cache price data in Redis with appropriate TTL."""

        # Cache individual price components with different TTLs using constants
        price_data = {
            f"{RedisKeys.PREFIX_PRICE}:{symbol}": str(ticker_data.price),
            f"{RedisKeys.PREFIX_BID}:{symbol}": str(ticker_data.bid_price),
            f"{RedisKeys.PREFIX_ASK}:{symbol}": str(ticker_data.ask_price),
            f"{RedisKeys.PREFIX_VOLUME}:{symbol}": str(ticker_data.volume_24h),
            f"{RedisKeys.PREFIX_CHANGE}:{symbol}": str(ticker_data.price_change_percent_24h)
        }

        # Use pipeline for efficient bulk operations
        cm = self.connection_manager
        assert cm is not None
        await cm.redis.pipeline_set(
            price_data,
            ttl=RedisKeys.TTL_PRICE_DATA
        )

        # Also cache complete ticker data as JSON
        ticker_json = json.dumps({
            'symbol': symbol,
            'price': str(ticker_data.price),
            'bid_price': str(ticker_data.bid_price),
            'ask_price': str(ticker_data.ask_price),
            'volume_24h': str(ticker_data.volume_24h),
            'price_change_24h': str(ticker_data.price_change_24h),
            'price_change_percent_24h': str(ticker_data.price_change_percent_24h),
            'high_24h': str(ticker_data.high_24h),
            'low_24h': str(ticker_data.low_24h),
            'timestamp': ticker_data.timestamp.isoformat()
        })

        cm = self.connection_manager
        assert cm is not None
        await cm.redis.set(
            f"{RedisKeys.PREFIX_TICKER}:{symbol}",
            ticker_json,
            ex=RedisKeys.TTL_TICKER_DATA
        )

    async def _update_data_quality(self, symbol: str, ticker_data: TickerData) -> None:
        """Update data quality metrics."""
        try:
            # Calculate quality score based on data completeness and freshness
            quality_score = self._calculate_quality_score(ticker_data)

            # Determine alert level using constants
            alert_level = DataQualityConstants.ALERT_INFO
            if quality_score < DataQualityConstants.QUALITY_WARNING:
                alert_level = DataQualityConstants.ALERT_WARNING
            elif quality_score < DataQualityConstants.QUALITY_ERROR:
                alert_level = DataQualityConstants.ALERT_ERROR

            # Store quality metric
            schema = self.config.database_schema
            insert_sql = f"""
                INSERT INTO {schema}.{DatabaseConstants.TABLE_DATA_QUALITY_METRICS} (
                    symbol, metric_type, metric_value, quality_score, alert_level, metric_data
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """

            metric_data = {
                'price': str(ticker_data.price),
                'volume': str(ticker_data.volume_24h),
                'timestamp': ticker_data.timestamp.isoformat(),
                'bid_ask_spread': str(ticker_data.ask_price - ticker_data.bid_price) if ticker_data.ask_price and ticker_data.bid_price else None
            }

            cm = self.connection_manager
            assert cm is not None
            await cm.postgres.execute(
                insert_sql,
                symbol,
                'ticker_update',
                float(ticker_data.price),
                quality_score,
                alert_level,
                json.dumps(metric_data)
            )

        except Exception as e:
            logger.warning(f"Failed to update data quality for {symbol}: {e}")

    def _calculate_quality_score(self, ticker_data: TickerData) -> float:
        """Calculate data quality score (0.0 to 1.0)."""
        score = 1.0

        # Check data completeness
        if not ticker_data.bid_price or not ticker_data.ask_price:
            score -= 0.2

        if not ticker_data.volume_24h or ticker_data.volume_24h <= 0:
            score -= 0.3

        # Check data freshness (should be within last few minutes)
        if ticker_data.timestamp:
            age_seconds = (datetime.now(timezone.utc) - ticker_data.timestamp).total_seconds()
            if age_seconds > DataQualityConstants.MAX_DATA_AGE_SECONDS:
                score -= 0.3
            elif age_seconds > 60:  # 1 minute
                score -= 0.1

        # Check bid-ask spread reasonableness
        if ticker_data.bid_price and ticker_data.ask_price:
            spread_pct = ((ticker_data.ask_price - ticker_data.bid_price) / ticker_data.price) * 100
            if spread_pct > 1.0:  # Spread > 1%
                score -= 0.2
            elif spread_pct > 0.5:  # Spread > 0.5%
                score -= 0.1

        return max(0.0, score)

    async def fetch_historical_data(self, symbol: str, interval: str = '1m',
                                  limit: int = 1000) -> List[KlineData]:
        """Fetch historical OHLCV data and store in PostgreSQL."""
        if not self.binance_client:
            await self.initialize()

        logger.info(f"Fetching historical data for {symbol} ({interval}, {limit} candles)")

        try:
            # Fetch from Binance
            client = self.binance_client
            assert client is not None
            klines = await client.get_kline_data(symbol, interval, limit)

            if not klines:
                logger.warning(f"No historical data received for {symbol}")
                return []

            # Store in PostgreSQL
            await self._store_ohlcv_data(klines, interval)

            # Archive to R2 if this is a large dataset
            if len(klines) >= 500:
                await self._archive_to_r2(symbol, klines, interval)

            logger.info(f"✅ Stored {len(klines)} candles for {symbol}")
            return klines

        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            return []

    async def _store_ohlcv_data(self, klines: List[KlineData], interval: str) -> None:
        """Store OHLCV data in appropriate PostgreSQL table using batch insertion."""
        if not klines:
            return

        # Use constants instead of magic strings
        table_map = TimeIntervals.INTERVAL_TO_TABLE
        table_name = table_map.get(interval)
        if not table_name:
            logger.warning(f"Unsupported interval '{interval}' for OHLCV storage.")
            return

        schema = self.config.database_schema
        insert_sql = f"""
        INSERT INTO {schema}.{table_name} (
            symbol, timestamp, open_price, high_price, low_price, close_price,
            volume, trades_count, taker_buy_volume
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (symbol, timestamp) DO UPDATE SET
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            trades_count = EXCLUDED.trades_count,
            taker_buy_volume = EXCLUDED.taker_buy_volume
        """

        data_to_insert = [
            (
                kline.symbol,
                kline.open_time,
                kline.open_price,
                kline.high_price,
                kline.low_price,
                kline.close_price,
                kline.volume,
                kline.number_of_trades,
                None,  # taker_buy_volume not available
            )
            for kline in klines
        ]

        try:
            cm = self.connection_manager
            assert cm is not None
            await cm.postgres.executemany(insert_sql, data_to_insert)
            logger.debug(f"Successfully upserted {len(data_to_insert)} rows into {table_name}.")
        except Exception as e:
            logger.error(f"Batch insert into {table_name} failed: {e}")
            # As a fallback, we could implement row-by-row insertion here if needed.
            # For now, we just log the error.
            raise

    async def _archive_to_r2(self, symbol: str, klines: List[KlineData], interval: str) -> None:
        """Archive historical data to R2 storage."""
        try:
            # Convert to Polars DataFrame for efficient processing
            data = []
            for kline in klines:
                data.append({
                    'symbol': kline.symbol,
                    'timestamp': kline.open_time.isoformat(),
                    'open': float(kline.open_price),
                    'high': float(kline.high_price),
                    'low': float(kline.low_price),
                    'close': float(kline.close_price),
                    'volume': float(kline.volume),
                    'trades': kline.number_of_trades
                })

            df = pl.DataFrame(data)

            # Convert to Parquet bytes
            from io import BytesIO
            buffer = BytesIO()
            df.write_parquet(buffer)
            parquet_bytes = buffer.getvalue()

            # Generate R2 key with date partitioning
            date_str = klines[0].open_time.strftime('%Y/%m/%d')
            key = f"{StorageConstants.R2_HISTORICAL_PREFIX}/{symbol}/{interval}/{date_str}/ohlcv_{datetime.now().strftime('%H%M%S')}{StorageConstants.EXT_PARQUET}"

            # Upload to R2
            cm = self.connection_manager
            assert cm is not None
            success = await cm.r2.upload_object(
                key=key,
                data=parquet_bytes,
                content_type='application/octet-stream'
            )

            if success:
                logger.info(f"📦 Archived {len(klines)} candles to R2: {key}")
            else:
                logger.warning(f"Failed to archive data to R2: {key}")

        except Exception as e:
            logger.error(f"Failed to archive to R2: {e}")

    async def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current price with hot/warm fallback."""
        try:
            # Try Redis first (hot data)
            cm = self.connection_manager
            assert cm is not None
            cached_price = await cm.redis.get(f"{RedisKeys.PREFIX_PRICE}:{symbol}")
            if cached_price:
                return Decimal(cached_price)

            # Fallback to PostgreSQL (warm data)
            schema = self.config.database_schema
            cm = self.connection_manager
            assert cm is not None
            price = await cm.postgres.fetchval(
                f"SELECT price FROM {schema}.{DatabaseConstants.TABLE_CURRENT_PRICES} WHERE symbol = $1",
                symbol
            )

            return Decimal(str(price)) if price else None

        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None

    async def get_recent_ohlcv(self, symbol: str, interval: str = '1m',
                             limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent OHLCV data from PostgreSQL."""
        table_name = TimeIntervals.INTERVAL_TO_TABLE.get(interval, DatabaseConstants.TABLE_OHLCV_1M)

        try:
            schema = self.config.database_schema
            query = f"""
            SELECT symbol, timestamp, open_price, high_price, low_price,
                   close_price, volume, trades_count
            FROM {schema}.{table_name}
            WHERE symbol = $1
            ORDER BY timestamp DESC
            LIMIT $2
            """

            cm = self.connection_manager
            assert cm is not None
            rows = await cm.postgres.fetch(query, symbol, limit)
            return rows

        except Exception as e:
            logger.error(f"Failed to get OHLCV data for {symbol}: {e}")
            return []

    def _update_metrics(self, processing_time: float) -> None:
        """Update pipeline performance metrics."""
        self.metrics['total_updates'] += 1
        self.metrics['last_update'] = datetime.now()

        # Update average processing time (rolling average)
        current_avg: float = self.metrics['avg_processing_time']
        total_updates = self.metrics['total_updates']
        self.metrics['avg_processing_time'] = ((current_avg * (total_updates - 1)) + processing_time) / total_updates

    async def get_pipeline_health(self) -> Dict[str, Any]:
        """Get pipeline health status."""
        if not self.connection_manager:
            return {'status': 'not_initialized'}

        # Check connection health
        health_status = await self.connection_manager.health_check_all()

        # Calculate uptime
        uptime_seconds: float = 0.0
        if self.metrics['last_update']:
            uptime_seconds = (datetime.now() - self.metrics['last_update']).total_seconds()

        return {
            'status': 'running' if self.is_running else 'stopped',
            'connections': health_status,
            'metrics': self.metrics,
            'uptime_seconds': uptime_seconds,
            'symbols_tracked': len(self.symbols),
            'timestamp': datetime.now().isoformat()
        }

    async def stop_pipeline(self) -> None:
        """Stop the real-time pipeline."""
        logger.info("🛑 Stopping market data pipeline...")
        self.is_running = False

        if self.binance_client:
            await self.binance_client.close()

        # The connection manager is now managed externally, so we don't reset it here.
        self.connection_manager = None

        logger.info("Pipeline stopped")

# Utility functions
async def start_data_pipeline(symbols: Optional[List[str]] = None) -> MarketDataPipeline:
    """Start the market data pipeline with specified symbols."""
    pipeline = MarketDataPipeline()

    if symbols:
        pipeline.symbols = symbols

    await pipeline.initialize()
    return pipeline

async def fetch_and_store_historical_data(symbol: str, days: int = 7) -> bool:
    """Utility function to fetch and store historical data."""
    try:
        pipeline = MarketDataPipeline()
        await pipeline.initialize()

        # Fetch different timeframes
        intervals = TimeIntervals.SUPPORTED_INTERVALS

        for interval in intervals:
            # Calculate appropriate limit based on timeframe and days
            if interval == TimeIntervals.INTERVAL_1M:
                limit = min(1000, days * 24 * 60)  # 1440 candles per day max
            elif interval == TimeIntervals.INTERVAL_5M:
                limit = min(1000, days * 24 * 12)  # 288 candles per day
            elif interval == TimeIntervals.INTERVAL_1H:
                limit = min(1000, days * 24)       # 24 candles per day
            elif interval == TimeIntervals.INTERVAL_4H:
                limit = min(1000, days * 6)        # 6 candles per day
            else:  # 1d
                limit = min(1000, days)             # 1 candle per day

            await pipeline.fetch_historical_data(symbol, interval, limit)
            await asyncio.sleep(1)  # Rate limiting between requests

        return True

    except Exception as e:
        logger.error(f"Failed to fetch historical data for {symbol}: {e}")
        return False
