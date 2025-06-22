#!/usr/bin/env python3
"""
Helios Trading Bot - Phase 1.3 Data Pipeline Testing Script

This script tests the complete data pipeline implementation:
1. Connection managers (Neon PostgreSQL, Upstash Redis, Cloudflare R2)
2. Database schema creation and validation
3. Market data pipeline functionality
4. Data quality monitoring
5. Performance metrics

Usage:
    python scripts/test_data_pipeline.py
    
Features:
- Comprehensive testing of all pipeline components
- Real-time feedback with progress indicators
- Detailed error reporting and diagnostics
- Performance benchmarking
- Data validation and quality checks
"""

import asyncio
import sys
import time
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import json

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.connection_managers import ConnectionManager
from src.data.database_schema import initialize_database, DatabaseSchema
from src.data.market_data_pipeline import MarketDataPipeline
from src.api.models import TickerData
from src.core.config import load_configuration, get_config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PipelineTestSuite:
    """Comprehensive test suite for data pipeline."""
    
    def __init__(self):
        self.results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'errors': [],
            'performance_metrics': {},
            'start_time': datetime.now()
        }
        
    def print_header(self, title: str):
        """Print formatted test section header."""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")
    
    def print_status(self, message: str, status: str = "info"):
        """Print formatted status message."""
        icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',  
            'error': '❌',
            'running': '🔄'
        }
        
        icon = icons.get(status, 'ℹ️')
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {icon} {message}")
    
    def record_test_result(self, test_name: str, success: bool, error: str = None, metrics: Dict = None):
        """Record test result."""
        self.results['tests_run'] += 1
        if success:
            self.results['tests_passed'] += 1
            self.print_status(f"Test passed: {test_name}", "success")
        else:
            self.results['tests_failed'] += 1
            self.print_status(f"Test failed: {test_name}", "error")
            if error:
                self.results['errors'].append({
                    'test': test_name,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                })
                self.print_status(f"Error details: {error}", "error")
        
        if metrics:
            self.results['performance_metrics'][test_name] = metrics
    
    async def test_configuration(self) -> bool:
        """Test 1: Configuration and Environment Variables."""
        self.print_header("Test 1: Configuration Validation")
        
        try:
            # Load configuration first
            config = load_configuration()
            
            # Check required environment variables
            required_vars = [
                ('neon_database_url', 'NEON_DATABASE_URL'),
                ('upstash_redis_url', 'UPSTASH_REDIS_URL'),
                ('r2_account_id', 'R2_ACCOUNT_ID'),
                ('r2_api_token', 'R2_API_TOKEN'),
                ('r2_bucket_name', 'R2_BUCKET_NAME')
            ]
            
            missing_vars = []
            for attr, env_var in required_vars:
                value = getattr(config, attr, None)
                if not value:
                    missing_vars.append(env_var)
                else:
                    # Mask sensitive data for display
                    masked_value = value[:10] + "..." + value[-10:] if len(value) > 20 else value[:5] + "..."
                    self.print_status(f"{env_var}: {masked_value}")
            
            if missing_vars:
                error_msg = f"Missing environment variables: {', '.join(missing_vars)}"
                self.record_test_result("Configuration Check", False, error_msg)
                return False
            
            self.record_test_result("Configuration Check", True)
            return True
            
        except Exception as e:
            self.record_test_result("Configuration Check", False, str(e))
            return False
    
    async def test_connection_managers(self) -> bool:
        """Test 2: Connection Managers."""
        self.print_header("Test 2: Connection Managers")
        
        manager = None
        try:
            start_time = time.time()
            manager = ConnectionManager()
            
            # Test individual connections
            self.print_status("Testing PostgreSQL connection...", "running")
            await manager.postgres.connect()
            pg_health = await manager.postgres.health_check()
            
            self.print_status("Testing Redis connection...", "running")
            await manager.redis.connect()
            redis_health = await manager.redis.health_check()
            
            self.print_status("Testing R2 connection...", "running")
            await manager.r2.connect()
            r2_health = await manager.r2.health_check()
            
            connection_time = time.time() - start_time
            
            # Validate health
            all_healthy = all([
                pg_health.is_healthy,
                redis_health.is_healthy,
                r2_health.is_healthy
            ])
            
            if all_healthy:
                self.print_status(f"PostgreSQL: {pg_health.response_time_ms:.1f}ms")
                self.print_status(f"Redis: {redis_health.response_time_ms:.1f}ms")
                self.print_status(f"R2: {r2_health.response_time_ms:.1f}ms")
                
                self.record_test_result(
                    "Connection Managers",
                    True,
                    metrics={
                        'total_connection_time': connection_time,
                        'postgresql_response_time': pg_health.response_time_ms,
                        'redis_response_time': redis_health.response_time_ms,
                        'r2_response_time': r2_health.response_time_ms
                    }
                )
                return True
            else:
                unhealthy = []
                if not pg_health.is_healthy:
                    unhealthy.append(f"PostgreSQL: {pg_health.error_message}")
                if not redis_health.is_healthy:
                    unhealthy.append(f"Redis: {redis_health.error_message}")
                if not r2_health.is_healthy:
                    unhealthy.append(f"R2: {r2_health.error_message}")
                
                error_msg = "Unhealthy connections: " + "; ".join(unhealthy)
                self.record_test_result("Connection Managers", False, error_msg)
                return False
                
        except Exception as e:
            self.record_test_result("Connection Managers", False, str(e))
            return False
        finally:
            if manager:
                await manager.disconnect_all()
    
    async def test_database_schema(self) -> bool:
        """Test 3: Database Schema Creation and Validation."""
        self.print_header("Test 3: Database Schema")
        
        try:
            start_time = time.time()
            
            self.print_status("Creating database schema...", "running")
            success = await initialize_database()
            
            if not success:
                self.record_test_result("Database Schema", False, "Schema initialization failed")
                return False
            
            # Verify schema
            schema = DatabaseSchema()
            verification = await schema.verify_schema()
            schema_time = time.time() - start_time
            
            if verification['tables_exist']:
                self.print_status(f"Created {verification['tables_count']} tables")
                self.print_status(f"Created {verification['indexes_count']} indexes")
                
                # Test basic operations
                await self._test_basic_database_operations(schema)
                
                self.record_test_result(
                    "Database Schema",
                    True,
                    metrics={
                        'schema_creation_time': schema_time,
                        'tables_created': verification['tables_count'],
                        'indexes_created': verification['indexes_count']
                    }
                )
                return True
            else:
                error_msg = f"Schema verification failed: {verification}"
                self.record_test_result("Database Schema", False, error_msg)
                return False
                
        except Exception as e:
            self.record_test_result("Database Schema", False, str(e))
            return False
    
    async def _test_basic_database_operations(self, schema: DatabaseSchema):
        """Test basic database operations."""
        try:
            # Test insert/select operations
            test_symbol = 'TESTBTCUSDT'
            
            # Insert test data
            await schema.connection_manager.postgres.execute(
                """INSERT INTO current_prices (symbol, price, timestamp) 
                   VALUES ($1, $2, CURRENT_TIMESTAMP)
                   ON CONFLICT (symbol) DO UPDATE SET price = EXCLUDED.price""",
                test_symbol, Decimal('50000.0')
            )
            
            # Verify data
            result = await schema.connection_manager.postgres.fetchrow(
                "SELECT * FROM current_prices WHERE symbol = $1", test_symbol
            )
            
            if result and result['symbol'] == test_symbol:
                self.print_status("Database operations: INSERT/SELECT working")
            else:
                raise Exception("Failed to insert/retrieve test data")
            
            # Cleanup
            await schema.connection_manager.postgres.execute(
                "DELETE FROM current_prices WHERE symbol = $1", test_symbol
            )
            
        except Exception as e:
            raise Exception(f"Database operations test failed: {e}")
    
    async def test_market_data_pipeline(self) -> bool:
        """Test 4: Market Data Pipeline."""
        self.print_header("Test 4: Market Data Pipeline")
        
        pipeline = None
        try:
            start_time = time.time()
            
            # Initialize pipeline
            self.print_status("Initializing market data pipeline...", "running")
            pipeline = MarketDataPipeline()
            pipeline.symbols = ['BTCUSDT']  # Test with single symbol
            await pipeline.initialize()
            
            # Test pipeline health
            health = await pipeline.get_pipeline_health()
            
            if health['status'] not in ['running', 'stopped']:
                raise Exception(f"Pipeline status invalid: {health['status']}")
            
            # Test data processing with mock data
            self.print_status("Testing data processing...", "running")
            await self._test_data_processing(pipeline)
            
            # Test data retrieval
            self.print_status("Testing data retrieval...", "running")
            await self._test_data_retrieval(pipeline)
            
            pipeline_time = time.time() - start_time
            
            self.record_test_result(
                "Market Data Pipeline",
                True,
                metrics={
                    'pipeline_initialization_time': pipeline_time,
                    'health_status': health['status'],
                    'symbols_tracked': len(pipeline.symbols)
                }
            )
            return True
            
        except Exception as e:
            self.record_test_result("Market Data Pipeline", False, str(e))
            return False
        finally:
            if pipeline:
                await pipeline.stop_pipeline()
    
    async def _test_data_processing(self, pipeline: MarketDataPipeline):
        """Test data processing functionality."""
        # Create mock ticker data
        test_ticker = TickerData(
            symbol='BTCUSDT',
            price=Decimal('50000.25'),
            bid_price=Decimal('50000.00'),
            ask_price=Decimal('50000.50'),
            volume_24h=Decimal('1234.56'),
            price_change_24h=Decimal('1500.00'),
            price_change_percent_24h=Decimal('3.09'),
            high_24h=Decimal('51000.00'),
            low_24h=Decimal('48500.00'),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Process through pipeline
        await pipeline._process_single_ticker('BTCUSDT', test_ticker)
        
        # Verify data was stored
        stored_price = await pipeline.connection_manager.postgres.fetchrow(
            "SELECT * FROM current_prices WHERE symbol = 'BTCUSDT'"
        )
        
        if not stored_price or Decimal(str(stored_price['price'])) != test_ticker.price:
            raise Exception("Data not properly stored in PostgreSQL")
        
        # Verify Redis caching
        cached_price = await pipeline.connection_manager.redis.get("price:BTCUSDT")
        if not cached_price or Decimal(cached_price) != test_ticker.price:
            raise Exception("Data not properly cached in Redis")
        
        self.print_status("Data processing: PostgreSQL ✓ Redis ✓")
    
    async def _test_data_retrieval(self, pipeline: MarketDataPipeline):
        """Test data retrieval functionality."""
        # Test current price retrieval
        price = await pipeline.get_current_price('BTCUSDT')
        
        if not price or price <= 0:
            raise Exception("Failed to retrieve current price")
        
        self.print_status(f"Data retrieval: Current price = ${price:,.2f}")
    
    async def test_data_quality_monitoring(self) -> bool:
        """Test 5: Data Quality Monitoring."""
        self.print_header("Test 5: Data Quality Monitoring")
        
        pipeline = None
        try:
            pipeline = MarketDataPipeline()
            await pipeline.initialize()
            
            # Test with high quality data
            good_ticker = TickerData(
                symbol='QUALITYTEST',
                price=Decimal('100.00'),
                bid_price=Decimal('99.95'),
                ask_price=Decimal('100.05'),
                volume_24h=Decimal('10000.0'),
                price_change_24h=Decimal('2.00'),
                price_change_percent_24h=Decimal('2.04'),
                high_24h=Decimal('102.00'),
                low_24h=Decimal('98.00'),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Test with poor quality data
            poor_ticker = TickerData(
                symbol='POORQUALITY',
                price=Decimal('100.00'),
                bid_price=None,  # Missing
                ask_price=None,  # Missing
                volume_24h=Decimal('0'),  # Zero volume
                price_change_24h=Decimal('0'),
                price_change_percent_24h=Decimal('0'),
                high_24h=Decimal('100.00'),
                low_24h=Decimal('100.00'),
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=10)  # Old
            )
            
            # Process both
            await pipeline._process_single_ticker('QUALITYTEST', good_ticker)
            await pipeline._process_single_ticker('POORQUALITY', poor_ticker)
            
            # Check quality metrics were recorded
            quality_metrics = await pipeline.connection_manager.postgres.fetch(
                """SELECT symbol, quality_score, alert_level 
                   FROM data_quality_metrics 
                   WHERE symbol IN ('QUALITYTEST', 'POORQUALITY')
                   ORDER BY timestamp DESC LIMIT 2"""
            )
            
            if len(quality_metrics) < 2:
                raise Exception("Quality metrics not properly recorded")
            
            # Verify quality scores
            quality_test_score = None
            poor_quality_score = None
            
            for metric in quality_metrics:
                if metric['symbol'] == 'QUALITYTEST':
                    quality_test_score = float(metric['quality_score'])
                elif metric['symbol'] == 'POORQUALITY':
                    poor_quality_score = float(metric['quality_score'])
            
            if quality_test_score is None or poor_quality_score is None:
                raise Exception("Quality scores not found for test symbols")
            
            if quality_test_score <= poor_quality_score:
                raise Exception(f"Quality scoring failed: good={quality_test_score}, poor={poor_quality_score}")
            
            self.print_status(f"Quality scoring: Good data = {quality_test_score:.2f}, Poor data = {poor_quality_score:.2f}")
            
            # Cleanup
            await pipeline.connection_manager.postgres.execute(
                "DELETE FROM current_prices WHERE symbol IN ('QUALITYTEST', 'POORQUALITY')"
            )
            await pipeline.connection_manager.postgres.execute(
                "DELETE FROM data_quality_metrics WHERE symbol IN ('QUALITYTEST', 'POORQUALITY')"
            )
            
            self.record_test_result("Data Quality Monitoring", True)
            return True
            
        except Exception as e:
            self.record_test_result("Data Quality Monitoring", False, str(e))
            return False
        finally:
            if pipeline:
                await pipeline.stop_pipeline()
    
    async def test_performance_benchmarks(self) -> bool:
        """Test 6: Performance Benchmarks."""
        self.print_header("Test 6: Performance Benchmarks")
        
        pipeline = None
        try:
            pipeline = MarketDataPipeline()
            await pipeline.initialize()
            
            # Benchmark data processing speed
            start_time = time.time()
            
            test_tickers = []
            for i in range(10):  # Process 10 tickers
                ticker = TickerData(
                    symbol=f'BENCH{i:02d}USDT',
                    price=Decimal(f'{1000 + i}.{i:02d}'),
                    bid_price=Decimal(f'{999 + i}.{i:02d}'),
                    ask_price=Decimal(f'{1001 + i}.{i:02d}'),
                    volume_24h=Decimal(f'{10000 + i * 100}.0'),
                    price_change_24h=Decimal(f'{i}.{i:02d}'),
                    price_change_percent_24h=Decimal(f'{i * 0.1:.2f}'),
                    high_24h=Decimal(f'{1010 + i}.{i:02d}'),
                    low_24h=Decimal(f'{990 + i}.{i:02d}'),
                    timestamp=datetime.now(timezone.utc)
                )
                test_tickers.append((f'BENCH{i:02d}USDT', ticker))
            
            # Process all tickers
            tasks = []
            for symbol, ticker in test_tickers:
                tasks.append(pipeline._process_single_ticker(symbol, ticker))
            
            await asyncio.gather(*tasks)
            
            processing_time = time.time() - start_time
            throughput = len(test_tickers) / processing_time
            
            self.print_status(f"Processed {len(test_tickers)} tickers in {processing_time:.2f}s")
            self.print_status(f"Throughput: {throughput:.1f} tickers/second")
            
            # Cleanup benchmark data
            cleanup_symbols = [f'BENCH{i:02d}USDT' for i in range(10)]
            for symbol in cleanup_symbols:
                await pipeline.connection_manager.postgres.execute(
                    "DELETE FROM current_prices WHERE symbol = $1", symbol
                )
                await pipeline.connection_manager.postgres.execute(
                    "DELETE FROM data_quality_metrics WHERE symbol = $1", symbol
                )
                await pipeline.connection_manager.redis.delete(f"price:{symbol}")
                await pipeline.connection_manager.redis.delete(f"ticker:{symbol}")
            
            # Performance benchmarks
            benchmarks = {
                'processing_time_seconds': processing_time,
                'throughput_tickers_per_second': throughput,
                'tickers_processed': len(test_tickers)
            }
            
            # Check performance requirements
            if throughput >= 5.0:  # Should process at least 5 tickers/second
                self.record_test_result("Performance Benchmarks", True, metrics=benchmarks)
                return True
            else:
                self.record_test_result("Performance Benchmarks", False, 
                                      f"Throughput too low: {throughput:.1f} < 5.0 tickers/second",
                                      benchmarks)
                return False
                
        except Exception as e:
            self.record_test_result("Performance Benchmarks", False, str(e))
            return False
        finally:
            if pipeline:
                await pipeline.stop_pipeline()
    
    def print_final_results(self):
        """Print final test results summary."""
        duration = datetime.now() - self.results['start_time']
        
        print(f"\n{'='*60}")
        print(f"🏁 PHASE 1.3 DATA PIPELINE TEST RESULTS")
        print(f"{'='*60}")
        
        print(f"📊 Test Summary:")
        print(f"   • Total Tests: {self.results['tests_run']}")
        print(f"   • Passed: {self.results['tests_passed']} ✅")
        print(f"   • Failed: {self.results['tests_failed']} ❌")
        print(f"   • Success Rate: {(self.results['tests_passed']/self.results['tests_run']*100):.1f}%")
        print(f"   • Duration: {duration.total_seconds():.1f} seconds")
        
        if self.results['performance_metrics']:
            print(f"\n⚡ Performance Metrics:")
            for test_name, metrics in self.results['performance_metrics'].items():
                print(f"   • {test_name}:")
                for metric, value in metrics.items():
                    if isinstance(value, float):
                        print(f"     - {metric}: {value:.2f}")
                    else:
                        print(f"     - {metric}: {value}")
        
        if self.results['errors']:
            print(f"\n🚨 Errors ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                print(f"   • {error['test']}: {error['error']}")
        
        # Overall status
        if self.results['tests_failed'] == 0:
            print(f"\n🎉 ALL TESTS PASSED! Phase 1.3 is ready for production.")
            print(f"   Your data pipeline is fully functional and performant.")
        else:
            print(f"\n⚠️  {self.results['tests_failed']} test(s) failed. Please review errors above.")
        
        print(f"\n💡 Next Steps:")
        if self.results['tests_failed'] == 0:
            print(f"   1. Review performance metrics above")
            print(f"   2. Monitor free tier usage limits")
            print(f"   3. Start Phase 1.4 - Real-time Data Collection")
        else:
            print(f"   1. Fix failed tests")
            print(f"   2. Re-run: python scripts/test_data_pipeline.py")
            print(f"   3. Check credentials and network connectivity")


async def main():
    """Run the complete data pipeline test suite."""
    print("🚀 Helios Trading Bot - Phase 1.3 Data Pipeline Testing")
    print("=" * 60)
    
    test_suite = PipelineTestSuite()
    
    try:
        # Run all tests in sequence
        tests = [
            test_suite.test_configuration(),
            test_suite.test_connection_managers(),
            test_suite.test_database_schema(),
            test_suite.test_market_data_pipeline(),
            test_suite.test_data_quality_monitoring(),
            test_suite.test_performance_benchmarks()
        ]
        
        for test in tests:
            success = await test
            if not success:
                break  # Stop on first failure for debugging
    
    except KeyboardInterrupt:
        test_suite.print_status("Testing interrupted by user", "warning")
    except Exception as e:
        test_suite.print_status(f"Testing failed with unexpected error: {e}", "error")
    
    finally:
        test_suite.print_final_results()


def run():
    """Entry point for console script."""
    asyncio.run(main())


if __name__ == "__main__":
    run() 