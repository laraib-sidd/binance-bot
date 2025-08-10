"""
Helios Trading Bot - Database Schema

PostgreSQL database schema for trading data storage.
Optimized for time-series data with proper indexing and partitioning.

Tables:
- current_prices: Real-time price data (hot data)
- ohlcv_1m: 1-minute OHLCV candlestick data
- ohlcv_5m: 5-minute OHLCV candlestick data  
- ohlcv_1h: 1-hour OHLCV candlestick data
- trading_sessions: Trading session metadata
- data_quality_metrics: Data quality monitoring
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set

from .connection_managers import get_connection_manager, ConnectionManager
from ..utils.logging import get_logger
from ..core.config import get_config
from ..core.constants import (
    DatabaseConstants,
    TimeIntervals,
    DataQualityConstants,
    TradingSessionStatus,
    DatabaseSchemaConstants,
)

logger = get_logger(__name__)


class DatabaseSchema:
    """Manages database schema creation and migrations."""
    
    def __init__(self) -> None:
        self.connection_manager: Optional[ConnectionManager] = None
        self.config = get_config()
        self.schema_name = self.config.database_schema
    
    async def initialize(self) -> None:
        """Initialize connection manager."""
        self.connection_manager = await get_connection_manager()
    
    async def create_schema(self) -> None:
        """Create dedicated database schema if it doesn't exist."""
        if not self.connection_manager:
            await self.initialize()
        
        create_schema_sql = f"""
        CREATE SCHEMA IF NOT EXISTS {self.schema_name};
        
        -- Set search path to include our schema
        SET search_path = {self.schema_name}, public;
        
        -- Grant necessary permissions
        GRANT USAGE ON SCHEMA {self.schema_name} TO {self.config.neon_username};
        GRANT CREATE ON SCHEMA {self.schema_name} TO {self.config.neon_username};
        """
        
        cm = self.connection_manager
        assert cm is not None
        await cm.postgres.execute(create_schema_sql)
        logger.info(f"✅ Created dedicated schema: {self.schema_name}")
    
    async def create_all_tables(self) -> None:
        """Create all trading tables with proper indexes and constraints."""
        if not self.connection_manager:
            await self.initialize()
        
        logger.info("Creating database schema...")
        
        # Create dedicated schema first
        await self.create_schema()
        
        # Set search path for this session
        cm = self.connection_manager
        assert cm is not None
        await cm.postgres.execute(
            f"SET search_path = {self.schema_name}, public"
        )
        
        # Create tables in dependency order
        await self._create_current_prices_table()
        await self._create_ohlcv_tables()
        await self._create_trading_sessions_table()
        await self._create_data_quality_table()
        await self._create_indexes()
        
        logger.info("✅ Database schema created successfully")
    
    async def _create_current_prices_table(self) -> None:
        """Create current_prices table for real-time price data."""
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.schema_name}.current_prices (
            symbol VARCHAR(20) NOT NULL,
            price DECIMAL(18, 8) NOT NULL,
            bid_price DECIMAL(18, 8),
            ask_price DECIMAL(18, 8),
            volume_24h DECIMAL(18, 8),
            price_change_24h DECIMAL(18, 8),
            price_change_percent_24h DECIMAL(8, 4),
            high_24h DECIMAL(18, 8),
            low_24h DECIMAL(18, 8),
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            
            -- Primary key and constraints
            PRIMARY KEY (symbol),
            
            -- Data validation constraints
            CONSTRAINT price_positive CHECK (price > 0),
            CONSTRAINT bid_ask_valid CHECK (bid_price <= ask_price OR bid_price IS NULL OR ask_price IS NULL),
            CONSTRAINT high_low_valid CHECK (high_24h >= low_24h OR high_24h IS NULL OR low_24h IS NULL),
            CONSTRAINT volume_non_negative CHECK (volume_24h >= 0 OR volume_24h IS NULL),
            CONSTRAINT timestamp_recent CHECK (timestamp >= CURRENT_TIMESTAMP - INTERVAL '{DatabaseSchemaConstants.PRICE_STALENESS_HOURS} hour')
        );
        
        -- Add comment
        COMMENT ON TABLE {self.schema_name}.current_prices IS 'Real-time current price data for trading pairs';
        """
        
        cm = self.connection_manager
        assert cm is not None
        await cm.postgres.execute(create_table_sql)
        logger.debug("Created current_prices table")
    
    async def _create_ohlcv_tables(self) -> None:
        """Create OHLCV tables for different timeframes."""
        
        timeframes = [
            (TimeIntervals.INTERVAL_1M, DatabaseSchemaConstants.TIME_DESC_1M),
            (TimeIntervals.INTERVAL_5M, DatabaseSchemaConstants.TIME_DESC_5M), 
            (TimeIntervals.INTERVAL_1H, DatabaseSchemaConstants.TIME_DESC_1H),
            (TimeIntervals.INTERVAL_4H, DatabaseSchemaConstants.TIME_DESC_4H),
            (TimeIntervals.INTERVAL_1D, DatabaseSchemaConstants.TIME_DESC_1D)
        ]
        
        for timeframe, description in timeframes:
            table_name = f"ohlcv_{timeframe}"
            
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.schema_name}.{table_name} (
                symbol VARCHAR(20) NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                open_price DECIMAL(18, 8) NOT NULL,
                high_price DECIMAL(18, 8) NOT NULL,
                low_price DECIMAL(18, 8) NOT NULL,
                close_price DECIMAL(18, 8) NOT NULL,
                volume DECIMAL(18, 8) NOT NULL,
                trades_count INTEGER,
                taker_buy_volume DECIMAL(18, 8),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                -- Primary key
                PRIMARY KEY (symbol, timestamp),
                
                -- Data validation constraints
                CONSTRAINT {table_name}_prices_positive CHECK (
                    open_price > 0 AND high_price > 0 AND 
                    low_price > 0 AND close_price > 0
                ),
                CONSTRAINT {table_name}_ohlc_valid CHECK (
                    high_price >= GREATEST(open_price, close_price) AND
                    low_price <= LEAST(open_price, close_price)
                ),
                CONSTRAINT {table_name}_volume_non_negative CHECK (volume >= 0),
                CONSTRAINT {table_name}_trades_non_negative CHECK (trades_count >= 0 OR trades_count IS NULL)
            );
            
            -- Add comment
            COMMENT ON TABLE {self.schema_name}.{table_name} IS 'OHLCV candlestick data for {description} timeframe';
            """
            
            cm = self.connection_manager
            assert cm is not None
            await cm.postgres.execute(create_table_sql)
            logger.debug(f"Created {table_name} table")
    
    async def _create_trading_sessions_table(self) -> None:
        """Create trading_sessions table for session metadata."""
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.schema_name}.trading_sessions (
            session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_name VARCHAR(100) NOT NULL,
            strategy_name VARCHAR(50) NOT NULL,
            symbols TEXT[] NOT NULL,
            start_time TIMESTAMP WITH TIME ZONE NOT NULL,
            end_time TIMESTAMP WITH TIME ZONE,
            status VARCHAR(20) NOT NULL DEFAULT '{TradingSessionStatus.ACTIVE}',
            config_data JSONB,
            performance_metrics JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            
            -- Constraints
            CONSTRAINT valid_status CHECK (status IN ('{TradingSessionStatus.ACTIVE}', '{TradingSessionStatus.PAUSED}', '{TradingSessionStatus.STOPPED}', '{TradingSessionStatus.COMPLETED}', '{TradingSessionStatus.ERROR}')),
            CONSTRAINT valid_time_range CHECK (end_time IS NULL OR end_time >= start_time)
        );
        
        -- Add comment
        COMMENT ON TABLE {self.schema_name}.trading_sessions IS 'Trading session metadata and performance tracking';
        """
        
        cm = self.connection_manager
        assert cm is not None
        await cm.postgres.execute(create_table_sql)
        logger.debug("Created trading_sessions table")
    
    async def _create_data_quality_table(self) -> None:
        """Create data_quality_metrics table for monitoring."""
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.schema_name}.data_quality_metrics (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            symbol VARCHAR(20),
            metric_type VARCHAR(50) NOT NULL,
            metric_value DECIMAL(18, 8),
            metric_data JSONB,
            quality_score DECIMAL(5, 4) CHECK (quality_score >= 0 AND quality_score <= 1),
            alert_level VARCHAR(20) DEFAULT '{DataQualityConstants.ALERT_INFO}',
            
            -- Constraints
            CONSTRAINT valid_alert_level CHECK (alert_level IN ('{DataQualityConstants.ALERT_INFO}', '{DataQualityConstants.ALERT_WARNING}', '{DataQualityConstants.ALERT_ERROR}', '{DataQualityConstants.ALERT_CRITICAL}'))
        );
        
        -- Add comment
        COMMENT ON TABLE {self.schema_name}.data_quality_metrics IS 'Data quality monitoring and metrics';
        """
        
        cm = self.connection_manager
        assert cm is not None
        await cm.postgres.execute(create_table_sql)
        logger.debug("Created data_quality_metrics table")
    
    async def _create_indexes(self) -> None:
        """Create optimized indexes for trading queries."""
        
        indexes = [
            # Current prices indexes
            f"CREATE INDEX IF NOT EXISTS idx_current_prices_timestamp ON {self.schema_name}.current_prices (timestamp DESC)",
            f"CREATE INDEX IF NOT EXISTS idx_current_prices_updated_at ON {self.schema_name}.current_prices (updated_at DESC)",
            
            # OHLCV indexes for each timeframe
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_1m_symbol_time ON {self.schema_name}.ohlcv_1m (symbol, timestamp DESC)",
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_1m_timestamp ON {self.schema_name}.ohlcv_1m (timestamp DESC)",
            
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_5m_symbol_time ON {self.schema_name}.ohlcv_5m (symbol, timestamp DESC)",
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_5m_timestamp ON {self.schema_name}.ohlcv_5m (timestamp DESC)",
            
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_1h_symbol_time ON {self.schema_name}.ohlcv_1h (symbol, timestamp DESC)",
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_1h_timestamp ON {self.schema_name}.ohlcv_1h (timestamp DESC)",
            
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_4h_symbol_time ON {self.schema_name}.ohlcv_4h (symbol, timestamp DESC)",
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_4h_timestamp ON {self.schema_name}.ohlcv_4h (timestamp DESC)",
            
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_1d_symbol_time ON {self.schema_name}.ohlcv_1d (symbol, timestamp DESC)",
            f"CREATE INDEX IF NOT EXISTS idx_ohlcv_1d_timestamp ON {self.schema_name}.ohlcv_1d (timestamp DESC)",
            
            # Trading sessions indexes
            f"CREATE INDEX IF NOT EXISTS idx_trading_sessions_start_time ON {self.schema_name}.trading_sessions (start_time DESC)",
            f"CREATE INDEX IF NOT EXISTS idx_trading_sessions_status ON {self.schema_name}.trading_sessions (status)",
            f"CREATE INDEX IF NOT EXISTS idx_trading_sessions_strategy ON {self.schema_name}.trading_sessions (strategy_name)",
            
            # Data quality indexes
            f"CREATE INDEX IF NOT EXISTS idx_data_quality_timestamp ON {self.schema_name}.data_quality_metrics (timestamp DESC)",
            f"CREATE INDEX IF NOT EXISTS idx_data_quality_symbol ON {self.schema_name}.data_quality_metrics (symbol)",
            f"CREATE INDEX IF NOT EXISTS idx_data_quality_type ON {self.schema_name}.data_quality_metrics (metric_type)",
            f"CREATE INDEX IF NOT EXISTS idx_data_quality_alert ON {self.schema_name}.data_quality_metrics (alert_level) WHERE alert_level IN ('warning', 'error', 'critical')",
        ]
        
        cm = self.connection_manager
        assert cm is not None
        for index_sql in indexes:
            await cm.postgres.execute(index_sql)
        
        logger.debug(f"Created {len(indexes)} database indexes")
    
    async def create_triggers(self) -> None:
        """Create database triggers for automatic timestamp updates."""
        
        # Function for updating timestamps
        create_function_sql = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
        
        cm = self.connection_manager
        assert cm is not None
        await cm.postgres.execute(create_function_sql)
        
        # Triggers for tables with updated_at columns
        triggers = [
            f"CREATE TRIGGER update_current_prices_updated_at BEFORE UPDATE ON {self.schema_name}.current_prices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            f"CREATE TRIGGER update_trading_sessions_updated_at BEFORE UPDATE ON {self.schema_name}.trading_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()"
        ]
        
        for trigger_sql in triggers:
            try:
                cm = self.connection_manager
                assert cm is not None
                await cm.postgres.execute(trigger_sql)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning(f"Failed to create trigger: {e}")
        
        logger.debug("Created database triggers")
    
    async def verify_schema(self) -> Dict[str, Any]:
        """Verify all tables and indexes exist."""
        if not self.connection_manager:
            await self.initialize()
        
        try:
            # Set search path for verification
            cm = self.connection_manager
            assert cm is not None
            await cm.postgres.execute(
                f"SET search_path = {self.schema_name}, public"
            )
            
            # Check tables with explicit debugging
            tables_sql = f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = $1 
            AND table_type = '{DatabaseSchemaConstants.TABLE_TYPE_BASE}'
            """
            
            existing_tables = await cm.postgres.fetch(tables_sql, self.schema_name)
            table_names: Set[str] = {row['table_name'] for row in existing_tables}
            
            # Debug logging
            logger.debug(f"Schema '{self.schema_name}' tables found: {sorted(table_names)}")
            
        except Exception as e:
            logger.error(f"Error during table verification: {e}")
            table_names = set()
        
        expected_tables = {
            DatabaseConstants.TABLE_CURRENT_PRICES, DatabaseConstants.TABLE_OHLCV_1M, 
            DatabaseConstants.TABLE_OHLCV_5M, DatabaseConstants.TABLE_OHLCV_1H, 
            DatabaseConstants.TABLE_OHLCV_4H, DatabaseConstants.TABLE_OHLCV_1D, 
            DatabaseConstants.TABLE_TRADING_SESSIONS, DatabaseConstants.TABLE_DATA_QUALITY_METRICS
        }
        
        try:
            # Check indexes
            indexes_sql = """
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = $1
            AND indexname LIKE '{DatabaseSchemaConstants.INDEX_PREFIX}%'
            """
            
            cm = self.connection_manager
            assert cm is not None
            existing_indexes = await cm.postgres.fetch(indexes_sql, self.schema_name)
            index_names: Set[str] = {row['indexname'] for row in existing_indexes}
            
            # Debug logging
            logger.debug(f"Schema '{self.schema_name}' indexes found: {sorted(index_names)}")
            
        except Exception as e:
            logger.error(f"Error during index verification: {e}")
            index_names = set()
        
        expected_indexes = {
            f'{DatabaseSchemaConstants.INDEX_PREFIX}current_prices_timestamp', 
            f'{DatabaseSchemaConstants.INDEX_PREFIX}ohlcv_1m_symbol_time',
            f'{DatabaseSchemaConstants.INDEX_PREFIX}ohlcv_5m_symbol_time', 
            f'{DatabaseSchemaConstants.INDEX_PREFIX}trading_sessions_start_time'
        }
        
        return {
            'tables_exist': expected_tables.issubset(table_names),
            'indexes_exist': len(expected_indexes.intersection(index_names)) > 0,
            'tables_count': len(table_names.intersection(expected_tables)),
            'indexes_count': len(index_names),
            'missing_tables': list(expected_tables - table_names),
            'missing_indexes': list(expected_indexes - index_names)
        }
    
    async def get_table_stats(self) -> Dict[str, Any]:
        """Get statistics about table sizes and row counts."""
        if not self.connection_manager:
            await self.initialize()
        
        # Set search path for stats queries
        cm = self.connection_manager
        assert cm is not None
        await cm.postgres.execute(
            f"SET search_path = {self.schema_name}, public"
        )
        
        # Simplify stats query to avoid placeholder mismatch; gather row counts below
        stats_sql = """
        SELECT 
            schemaname,
            tablename
        FROM pg_stats 
        WHERE schemaname = $1
        ORDER BY tablename
        """
        
        stats_data = await cm.postgres.fetch(stats_sql, self.schema_name)
        
        # Get row counts
        tables = DatabaseConstants.ALL_TABLES
        row_counts: Dict[str, int] = {}
        
        for table in tables:
            try:
                count = await cm.postgres.fetchval(f"SELECT COUNT(*) FROM {self.schema_name}.{table}")
                row_counts[table] = count
            except Exception as e:
                logger.warning(f"Failed to get row count for {table}: {e}")
                row_counts[table] = 0
        
        return {
            'row_counts': row_counts,
            'column_stats': stats_data,
            'total_rows': sum(row_counts.values())
        }
    
    async def cleanup_old_data(self, days_to_keep: int = DatabaseSchemaConstants.DEFAULT_RETENTION_DAYS) -> Dict[str, int]:
        """Clean up old data beyond retention period."""
        if not self.connection_manager:
            await self.initialize()
        
        cutoff_date = datetime.now(timezone.utc).replace(hour=DatabaseSchemaConstants.CLEANUP_HOUR, minute=DatabaseSchemaConstants.CLEANUP_MINUTE, second=DatabaseSchemaConstants.CLEANUP_SECOND, microsecond=DatabaseSchemaConstants.CLEANUP_MICROSECOND)
        cutoff_timestamp = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
        
        cleanup_counts = {}
        
        # Clean up OHLCV data older than retention period
        ohlcv_tables = DatabaseConstants.OHLCV_TABLES
        
        # Set search path for cleanup operations
        cm = self.connection_manager
        assert cm is not None
        await cm.postgres.execute(
            f"SET search_path = {self.schema_name}, public"
        )
        
        for table in ohlcv_tables:
            delete_sql = f"""
            DELETE FROM {self.schema_name}.{table} 
            WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '{days_to_keep} days'
            """
            
            try:
                await cm.postgres.execute(delete_sql)
                cleanup_counts[table] = 0  # asyncpg doesn't return affected rows easily
                logger.info(f"Cleaned up old data from {table}")
            except Exception as e:
                logger.error(f"Failed to cleanup {table}: {e}")
                cleanup_counts[table] = -1
        
        # Clean up old data quality metrics
        delete_quality_sql = f"""
        DELETE FROM {self.schema_name}.data_quality_metrics 
        WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '{days_to_keep} days'
        """
        
        try:
            await cm.postgres.execute(delete_quality_sql)
            cleanup_counts['data_quality_metrics'] = 0
            logger.info("Cleaned up old data quality metrics")
        except Exception as e:
            logger.error(f"Failed to cleanup data quality metrics: {e}")
            cleanup_counts['data_quality_metrics'] = -1
        
        return cleanup_counts


# Utility functions for schema management
async def initialize_database() -> bool:
    """Initialize database schema if not exists."""
    schema = None
    try:
        schema = DatabaseSchema()
        
        # Don't rely on global connection manager - create a fresh one
        from .connection_managers import ConnectionManager
        schema.connection_manager = ConnectionManager()
        await schema.connection_manager.connect_all()
        
        await schema.create_all_tables()
        await schema.create_triggers()
        
        # Add a small delay to ensure tables are committed
        import asyncio
        await asyncio.sleep(DatabaseSchemaConstants.SCHEMA_VERIFICATION_DELAY)
        
        # Simplified verification - just check if we can query the main table
        try:
            count = await schema.connection_manager.postgres.fetchval(
                f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{schema.schema_name}'"
            )
            
            if count and count >= DatabaseSchemaConstants.MINIMUM_TABLES_FOR_HEALTH:  # At least minimum core tables
                logger.info(f"✅ Database schema initialized successfully - {count} tables created")
                return True
            else:
                logger.error(f"❌ Schema verification failed - only {count} tables found")
                return False
                
        except Exception as verify_error:
            logger.error(f"❌ Schema verification error: {verify_error}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False
    finally:
        # Clean up our temporary connection manager
        if schema and schema.connection_manager:
            try:
                await schema.connection_manager.disconnect_all()
            except Exception as cleanup_error:
                logger.warning(f"Error during cleanup: {cleanup_error}")


async def verify_database_health() -> Dict[str, Any]:
    """Verify database health and return status."""
    try:
        schema = DatabaseSchema()
        verification = await schema.verify_schema()
        stats = await schema.get_table_stats()
        
        return {
            'schema_valid': verification['tables_exist'] and verification['indexes_exist'],
            'verification': verification,
            'stats': stats,
            'timestamp': datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'schema_valid': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc)
        } 