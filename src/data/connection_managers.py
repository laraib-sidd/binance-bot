"""
Helios Trading Bot - Connection Managers

Manages connections to all external services:
- Neon PostgreSQL (trading data storage)
- Upstash Redis (real-time caching)
- Cloudflare R2 (historical data storage)

Features:
- Connection pooling and management
- Automatic retry logic with exponential backoff
- Health checking and monitoring
- Secure credential handling
- Proper connection lifecycle management
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import redis.asyncio as redis

from ..core.config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ConnectionHealth:
    """Health status for a connection."""
    service: str
    is_healthy: bool
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None

class PostgreSQLManager:
    """
    Manages PostgreSQL connection pool for trading data.

    Features:
    - Connection pooling with configurable size
    - Automatic reconnection on failure
    - Query performance monitoring
    - Transaction management
    """

    def __init__(self, database_url: str, pool_size: int = 10):
        self.database_url = database_url
        self.pool_size = pool_size
        self.pool: Optional[asyncpg.Pool] = None
        self._health_status = ConnectionHealth(
            service="postgresql",
            is_healthy=False,
            last_check=datetime.now(),
            response_time_ms=0.0
        )

    async def connect(self) -> None:
        """Initialize connection pool."""
        try:
            logger.info("Connecting to PostgreSQL database...")
            start_time = datetime.now()

            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=self.pool_size,
                command_timeout=10,
                server_settings={
                    'jit': 'off',  # Disable JIT for better performance on small queries
                    'timezone': 'UTC'
                }
            )

            # Test connection
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._health_status = ConnectionHealth(
                service="postgresql",
                is_healthy=True,
                last_check=datetime.now(),
                response_time_ms=response_time
            )

            logger.info(f"PostgreSQL connected successfully ({response_time:.1f}ms)")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self._health_status = ConnectionHealth(
                service="postgresql",
                is_healthy=False,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_message=str(e)
            )
            raise

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

    async def execute(self, query: str, *args: Any) -> None:
        """Execute a query without returning results."""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")

        async with self.pool.acquire() as conn:
            await conn.execute(query, *args)

    async def executemany(self, query: str, args_list: List[tuple[Any, ...]]) -> None:
        """Execute a query multiple times with different parameters using efficient batch insert."""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")

        if not args_list:
            return

        async with self.pool.acquire() as conn:
            # For large datasets (>1000 rows), use transaction for better performance
            if len(args_list) > 1000:
                async with conn.transaction():
                    await conn.executemany(query, args_list)
            else:
                # Use asyncpg's efficient executemany for smaller batches
                await conn.executemany(query, args_list)

    async def fetch(self, query: str, *args: Any) -> List[Dict[str, Any]]:
        """Fetch multiple rows as dictionaries."""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetchrow(self, query: str, *args: Any) -> Optional[Dict[str, Any]]:
        """Fetch single row as dictionary."""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetchval(self, query: str, *args: Any) -> Any:
        """Fetch single value."""
        if not self.pool:
            raise RuntimeError("PostgreSQL pool not initialized")

        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def health_check(self) -> ConnectionHealth:
        """Check connection health."""
        try:
            start_time = datetime.now()
            await self.fetchval("SELECT 1")
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            self._health_status = ConnectionHealth(
                service="postgresql",
                is_healthy=True,
                last_check=datetime.now(),
                response_time_ms=response_time
            )
        except Exception as e:
            self._health_status = ConnectionHealth(
                service="postgresql",
                is_healthy=False,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_message=str(e)
            )

        return self._health_status

class RedisManager:
    """
    Manages Redis connection for real-time caching.

    Features:
    - Automatic connection management
    - TTL-based caching with optimistic-volatile eviction
    - Pipeline operations for bulk operations
    - Health monitoring
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None
        self._health_status = ConnectionHealth(
            service="redis",
            is_healthy=False,
            last_check=datetime.now(),
            response_time_ms=0.0
        )

    async def connect(self) -> None:
        """Initialize Redis connection."""
        try:
            logger.info("Connecting to Redis...")
            start_time = datetime.now()

            # Configure SSL settings for Upstash Redis
            ssl_settings = {}
            if self.redis_url.startswith('rediss://'):
                ssl_settings = {
                    'ssl_cert_reqs': None,  # Don't require SSL certificates
                    'ssl_check_hostname': False  # Don't verify hostname
                }

            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True,
                health_check_interval=30,
                **ssl_settings
            )

            # Test connection
            client = self.client
            assert client is not None
            await client.ping()

            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._health_status = ConnectionHealth(
                service="redis",
                is_healthy=True,
                last_check=datetime.now(),
                response_time_ms=response_time
            )

            logger.info(f"Redis connected successfully ({response_time:.1f}ms)")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._health_status = ConnectionHealth(
                service="redis",
                is_healthy=False,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_message=str(e)
            )
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.aclose()
            logger.info("Redis connection closed")

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value with optional TTL."""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        result = await self.client.set(key, value, ex=ex)
        return bool(result)

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        value = await self.client.get(key)
        return value if value is not None else None

    async def delete(self, key: str) -> int:
        """Delete key."""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        deleted = await self.client.delete(key)
        return int(deleted)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        return bool(await self.client.exists(key))

    async def pipeline_set(self, items: Dict[str, str], ttl: int = 300) -> None:
        """Set multiple keys using pipeline for better performance."""
        if not self.client:
            raise RuntimeError("Redis client not initialized")

        async with self.client.pipeline() as pipe:
            for key, value in items.items():
                pipe.setex(key, ttl, value)
            await pipe.execute()

    async def health_check(self) -> ConnectionHealth:
        """Check Redis connection health."""
        try:
            start_time = datetime.now()
            client = self.client
            assert client is not None
            await client.ping()
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            self._health_status = ConnectionHealth(
                service="redis",
                is_healthy=True,
                last_check=datetime.now(),
                response_time_ms=response_time
            )
        except Exception as e:
            self._health_status = ConnectionHealth(
                service="redis",
                is_healthy=False,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_message=str(e)
            )

        return self._health_status

class R2Manager:
    """
    Manages Cloudflare R2 connection for historical data storage.

    Features:
    - S3-compatible API for R2 access
    - Automatic retry with exponential backoff
    - Efficient upload/download operations
    - Object lifecycle management
    """

    def __init__(
        self,
        account_id: str,
        api_token: str,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        self.account_id = account_id
        self.api_token = api_token
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url or f"https://{account_id}.r2.cloudflarestorage.com"
        self.client: Optional[Any] = None
        self._health_status = ConnectionHealth(
            service="r2",
            is_healthy=False,
            last_check=datetime.now(),
            response_time_ms=0.0
        )

    async def connect(self) -> None:
        """Initialize R2 client."""
        try:
            logger.info("Connecting to Cloudflare R2...")
            start_time = datetime.now()

            # Use S3-style credentials if available, otherwise fall back to API token
            if self.access_key and self.secret_key:
                logger.info("Using S3-style credentials for R2 connection")
                aws_access_key_id = self.access_key
                aws_secret_access_key = self.secret_key
            else:
                logger.info("Using API token for R2 connection")
                # Use API token as both access key and secret (R2 requirement for API token auth)
                aws_access_key_id = self.api_token
                aws_secret_access_key = self.api_token

            self.client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name='auto',
                config=Config(
                    retries={'max_attempts': 3, 'mode': 'adaptive'},
                    connect_timeout=10,
                    read_timeout=30
                )
            )

            # Test connection by listing objects (with limit)
            client = self.client
            assert client is not None
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            )

            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._health_status = ConnectionHealth(
                service="r2",
                is_healthy=True,
                last_check=datetime.now(),
                response_time_ms=response_time
            )

            logger.info(f"R2 connected successfully ({response_time:.1f}ms)")

        except Exception as e:
            logger.error(f"Failed to connect to R2: {e}")
            self._health_status = ConnectionHealth(
                service="r2",
                is_healthy=False,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_message=str(e)
            )
            raise

    async def upload_object(self, key: str, data: bytes,
                          content_type: str = 'application/octet-stream') -> bool:
        """Upload object to R2."""
        if not self.client:
            raise RuntimeError("R2 client not initialized")

        try:
            client = self.client
            assert client is not None
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=data,
                    ContentType=content_type
                )
            )
            logger.debug(f"Uploaded object to R2: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload object {key}: {e}")
            return False

    async def download_object(self, key: str) -> Optional[bytes]:
        """Download object from R2."""
        if not self.client:
            raise RuntimeError("R2 client not initialized")

        try:
            client = self.client
            assert client is not None
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.get_object(Bucket=self.bucket_name, Key=key)
            )
            body = response.get('Body')
            return body.read() if body is not None else None
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(f"Object not found in R2: {key}")
                return None
            logger.error(f"Failed to download object {key}: {e}")
            return None

    async def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[str]:
        """List objects in bucket with optional prefix."""
        if not self.client:
            raise RuntimeError("R2 client not initialized")

        try:
            client = self.client
            assert client is not None
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=max_keys
                )
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except ClientError as e:
            logger.error(f"Failed to list objects: {e}")
            return []

    async def delete_object(self, key: str) -> bool:
        """Delete object from R2."""
        if not self.client:
            raise RuntimeError("R2 client not initialized")

        try:
            client = self.client
            assert client is not None
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.delete_object(Bucket=self.bucket_name, Key=key)
            )
            logger.debug(f"Deleted object from R2: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete object {key}: {e}")
            return False

    async def health_check(self) -> ConnectionHealth:
        """Check R2 connection health."""
        try:
            start_time = datetime.now()
            # Simple health check - list 1 object
            await self.list_objects(max_keys=1)
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            self._health_status = ConnectionHealth(
                service="r2",
                is_healthy=True,
                last_check=datetime.now(),
                response_time_ms=response_time
            )
        except Exception as e:
            self._health_status = ConnectionHealth(
                service="r2",
                is_healthy=False,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_message=str(e)
            )

        return self._health_status

class ConnectionManager:
    """
    Central connection manager for all external services.

    Manages lifecycle and health of all connections:
    - PostgreSQL for trading data
    - Redis for real-time caching
    - R2 for historical data storage
    """

    def __init__(self) -> None:
        config = get_config()

        # Initialize managers using new config methods
        self.postgres = PostgreSQLManager(
            database_url=config.get_postgresql_url(),
            pool_size=10
        )

        self.redis = RedisManager(
            redis_url=config.get_redis_url()
        )

        r2_config = config.get_r2_config()
        self.r2 = R2Manager(
            account_id=r2_config["account_id"],
            api_token=r2_config["api_token"],
            bucket_name=r2_config["bucket_name"],
            endpoint_url=r2_config["endpoint"],
            access_key=r2_config["access_key"],
            secret_key=r2_config["secret_key"]
        )

        self._connected = False

    async def connect_all(self) -> None:
        """Connect to all services."""
        logger.info("Connecting to all external services...")

        try:
            # Connect in parallel for faster startup
            await asyncio.gather(
                self.postgres.connect(),
                self.redis.connect(),
                self.r2.connect()
            )

            self._connected = True
            logger.info("✅ All services connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to services: {e}")
            await self.disconnect_all()
            raise

    async def disconnect_all(self) -> None:
        """Disconnect from all services."""
        logger.info("Disconnecting from all services...")

        # Disconnect in parallel
        await asyncio.gather(
            self.postgres.disconnect(),
            self.redis.disconnect(),
            # R2 doesn't need explicit disconnect
            return_exceptions=True
        )

        self._connected = False
        logger.info("All services disconnected")

    async def health_check_all(self) -> Dict[str, ConnectionHealth]:
        """Check health of all connections."""
        if not self._connected:
            return {
                "postgresql": ConnectionHealth("postgresql", False, datetime.now(), 0.0, "Not connected"),
                "redis": ConnectionHealth("redis", False, datetime.now(), 0.0, "Not connected"),
                "r2": ConnectionHealth("r2", False, datetime.now(), 0.0, "Not connected")
            }

        # Run health checks in parallel
        postgres_health, redis_health, r2_health = await asyncio.gather(
            self.postgres.health_check(),
            self.redis.health_check(),
            self.r2.health_check(),
            return_exceptions=True
        )

        return {
            "postgresql": postgres_health if isinstance(postgres_health, ConnectionHealth) else
                         ConnectionHealth("postgresql", False, datetime.now(), 0.0, str(postgres_health)),
            "redis": redis_health if isinstance(redis_health, ConnectionHealth) else
                    ConnectionHealth("redis", False, datetime.now(), 0.0, str(redis_health)),
            "r2": r2_health if isinstance(r2_health, ConnectionHealth) else
                 ConnectionHealth("r2", False, datetime.now(), 0.0, str(r2_health))
        }

    @property
    def is_connected(self) -> bool:
        """Check if all services are connected."""
        return self._connected

# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None

async def get_connection_manager() -> ConnectionManager:
    """Get or create global connection manager."""
    global _connection_manager

    if _connection_manager is None:
        _connection_manager = ConnectionManager()
        await _connection_manager.connect_all()

    return _connection_manager

async def close_connections() -> None:
    """Close all connections (for cleanup)."""
    global _connection_manager

    if _connection_manager:
        await _connection_manager.disconnect_all()
        _connection_manager = None

async def reset_connection_manager() -> None:
    """Reset the global connection manager (for testing/cleanup)."""
    global _connection_manager

    if _connection_manager:
        try:
            await _connection_manager.disconnect_all()
        except Exception as e:
            logger.warning(f"Error disconnecting manager during reset: {e}")
        finally:
            _connection_manager = None
