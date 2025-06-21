"""
Helios Trading Bot - API Rate Limiter

Sophisticated rate limiting system for Binance API to prevent rate limit
violations and ensure optimal API usage.

Key Features:
- Multiple rate limit tracking (per endpoint, per minute, per second)
- Weight-based rate limiting (Binance uses request weights)
- Automatic backoff and retry logic
- Real-time rate limit monitoring
- Thread-safe implementation
"""

import asyncio
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict, deque
from threading import Lock
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """
    Configuration for a specific rate limit.
    """
    limit: int  # Maximum requests/weight allowed
    window_seconds: int  # Time window in seconds
    current_usage: int = 0  # Current usage count
    reset_time: float = field(default_factory=time.time)  # When usage resets
    
    def is_exceeded(self) -> bool:
        """Check if rate limit is currently exceeded."""
        now = time.time()
        
        # Reset if window has passed
        if now >= self.reset_time:
            self.current_usage = 0
            self.reset_time = now + self.window_seconds
            return False
        
        return self.current_usage >= self.limit
    
    def get_reset_delay(self) -> float:
        """Get seconds until rate limit resets."""
        now = time.time()
        return max(0, self.reset_time - now)
    
    def add_usage(self, weight: int = 1) -> None:
        """Add usage to the rate limit."""
        now = time.time()
        
        # Reset if window has passed
        if now >= self.reset_time:
            self.current_usage = 0
            self.reset_time = now + self.window_seconds
        
        self.current_usage += weight
    
    def get_available_capacity(self) -> int:
        """Get remaining capacity before hitting limit."""
        if self.is_exceeded():
            return 0
        return max(0, self.limit - self.current_usage)


class BinanceRateLimiter:
    """
    Advanced rate limiter for Binance API with support for multiple
    concurrent rate limits and automatic throttling.
    
    Binance has several rate limits:
    - Request rate limits (requests per minute)
    - Weight-based limits (weight units per minute)  
    - Order rate limits (orders per time period)
    - Individual endpoint limits
    """
    
    def __init__(self):
        """Initialize rate limiter with Binance-specific limits."""
        self._lock = Lock()
        
        # Binance testnet rate limits (more conservative than production)
        self._rate_limits = {
            # General API limits
            'requests_per_minute': RateLimit(limit=1200, window_seconds=60),
            'weight_per_minute': RateLimit(limit=6000, window_seconds=60),
            'requests_per_second': RateLimit(limit=20, window_seconds=1),
            
            # Order-specific limits  
            'orders_per_second': RateLimit(limit=10, window_seconds=1),
            'orders_per_day': RateLimit(limit=200000, window_seconds=86400),
        }
        
        # Endpoint-specific limits
        self._endpoint_limits: Dict[str, RateLimit] = defaultdict(
            lambda: RateLimit(limit=20, window_seconds=1)
        )
        
        # Track request history for monitoring
        self._request_history: deque = deque(maxlen=1000)
        
        # Endpoint weights (Binance assigns different weights to endpoints)
        self._endpoint_weights = {
            '/api/v3/ticker/24hr': 1,
            '/api/v3/ticker/price': 1,
            '/api/v3/klines': 1,
            '/api/v3/account': 10,
            '/api/v3/exchangeInfo': 10,
            '/api/v3/depth': 1,
            '/api/v3/trades': 1,
            '/api/v3/order': 1,
            '/api/v3/openOrders': 3,
            '/api/v3/allOrders': 10,
        }
    
    async def acquire(self, endpoint: str, weight: Optional[int] = None) -> None:
        """
        Acquire permission to make an API request.
        
        Will block until it's safe to proceed without violating rate limits.
        
        Args:
            endpoint: API endpoint being called
            weight: Request weight (auto-detected if not provided)
        """
        if weight is None:
            weight = self._endpoint_weights.get(endpoint, 1)
        
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            with self._lock:
                # Check all applicable rate limits
                delays = []
                
                # Check general limits
                for limit_name, rate_limit in self._rate_limits.items():
                    if 'weight' in limit_name:
                        # Weight-based limit
                        if rate_limit.current_usage + weight > rate_limit.limit:
                            delays.append(rate_limit.get_reset_delay())
                    else:
                        # Request count limit
                        if rate_limit.is_exceeded():
                            delays.append(rate_limit.get_reset_delay())
                
                # Check endpoint-specific limit
                endpoint_limit = self._endpoint_limits[endpoint]
                if endpoint_limit.is_exceeded():
                    delays.append(endpoint_limit.get_reset_delay())
                
                # If no delays needed, acquire the slots
                if not delays:
                    self._add_usage(endpoint, weight)
                    self._log_request(endpoint, weight)
                    return
                
                # Calculate required delay
                delay = max(delays)
            
            # Wait outside the lock
            if delay > 0:
                logger.warning(f"Rate limit approached for {endpoint}, waiting {delay:.2f}s")
                await asyncio.sleep(delay)
            
            attempt += 1
        
        raise Exception(f"Failed to acquire rate limit after {max_attempts} attempts")
    
    def _add_usage(self, endpoint: str, weight: int) -> None:
        """Add usage to all applicable rate limits."""
        # Update general limits
        self._rate_limits['requests_per_minute'].add_usage(1)
        self._rate_limits['requests_per_second'].add_usage(1)
        self._rate_limits['weight_per_minute'].add_usage(weight)
        
        # Update endpoint-specific limit
        self._endpoint_limits[endpoint].add_usage(1)
        
        # Update order-specific limits if applicable
        if 'order' in endpoint.lower():
            self._rate_limits['orders_per_second'].add_usage(1)
            self._rate_limits['orders_per_day'].add_usage(1)
    
    def _log_request(self, endpoint: str, weight: int) -> None:
        """Log request for monitoring and debugging."""
        request_info = {
            'timestamp': time.time(),
            'endpoint': endpoint,
            'weight': weight
        }
        self._request_history.append(request_info)
        
        logger.debug(f"API request: {endpoint} (weight: {weight})")
    
    def get_status(self) -> Dict[str, any]:
        """
        Get current rate limiter status for monitoring.
        
        Returns:
            Dictionary with current usage and limits
        """
        with self._lock:
            status = {}
            
            for name, rate_limit in self._rate_limits.items():
                status[name] = {
                    'current_usage': rate_limit.current_usage,
                    'limit': rate_limit.limit,
                    'reset_in_seconds': rate_limit.get_reset_delay(),
                    'capacity_remaining': rate_limit.get_available_capacity()
                }
            
            # Recent request rate
            now = time.time()
            recent_requests = sum(
                1 for req in self._request_history 
                if now - req['timestamp'] < 60
            )
            
            status['recent_requests_per_minute'] = recent_requests
            status['total_requests_tracked'] = len(self._request_history)
            
            return status
    
    def update_limits_from_headers(self, headers: Dict[str, str]) -> None:
        """
        Update rate limits based on response headers from Binance.
        
        Binance includes rate limit information in response headers.
        """
        with self._lock:
            # Extract rate limit info from headers
            weight_used = headers.get('X-MBX-USED-WEIGHT-1M')
            if weight_used:
                try:
                    used = int(weight_used)
                    weight_limit = self._rate_limits['weight_per_minute']
                    weight_limit.current_usage = used
                    logger.debug(f"Updated weight usage from headers: {used}/{weight_limit.limit}")
                except ValueError:
                    logger.warning(f"Invalid weight header value: {weight_used}")
            
            # Update request count if available
            request_count = headers.get('X-MBX-REQUEST-COUNT-1M')
            if request_count:
                try:
                    used = int(request_count)
                    request_limit = self._rate_limits['requests_per_minute']
                    request_limit.current_usage = used
                    logger.debug(f"Updated request count from headers: {used}/{request_limit.limit}")
                except ValueError:
                    logger.warning(f"Invalid request count header value: {request_count}")
    
    def is_healthy(self) -> bool:
        """
        Check if rate limiter is in a healthy state.
        
        Returns:
            True if well within limits, False if approaching limits
        """
        with self._lock:
            for rate_limit in self._rate_limits.values():
                usage_percent = (rate_limit.current_usage / rate_limit.limit) * 100
                if usage_percent > 80:  # More than 80% usage
                    return False
            return True
    
    def get_recommended_delay(self) -> float:
        """
        Get recommended delay before next request to maintain healthy rates.
        
        Returns:
            Recommended delay in seconds
        """
        with self._lock:
            max_usage_percent = 0
            
            for rate_limit in self._rate_limits.values():
                usage_percent = (rate_limit.current_usage / rate_limit.limit) * 100
                max_usage_percent = max(max_usage_percent, usage_percent)
            
            # Progressive delay based on usage
            if max_usage_percent > 90:
                return 2.0  # High usage, slow down significantly
            elif max_usage_percent > 80:
                return 1.0  # Moderate usage, slow down moderately
            elif max_usage_percent > 60:
                return 0.5  # Light usage, slight delay
            else:
                return 0.1  # Low usage, minimal delay
    
    def reset_limits(self) -> None:
        """Reset all rate limits (for testing or manual intervention)."""
        with self._lock:
            now = time.time()
            for rate_limit in self._rate_limits.values():
                rate_limit.current_usage = 0
                rate_limit.reset_time = now + rate_limit.window_seconds
            
            for endpoint_limit in self._endpoint_limits.values():
                endpoint_limit.current_usage = 0
                endpoint_limit.reset_time = now + endpoint_limit.window_seconds
            
            logger.info("All rate limits reset")


# Global rate limiter instance
_rate_limiter = BinanceRateLimiter()


async def acquire_rate_limit(endpoint: str, weight: Optional[int] = None) -> None:
    """
    Convenience function to acquire rate limit for an endpoint.
    
    Args:
        endpoint: API endpoint being called
        weight: Request weight (auto-detected if not provided)
    """
    await _rate_limiter.acquire(endpoint, weight)


def update_rate_limits(headers: Dict[str, str]) -> None:
    """
    Convenience function to update rate limits from response headers.
    
    Args:
        headers: Response headers from Binance API
    """
    _rate_limiter.update_limits_from_headers(headers)


def get_rate_limiter_status() -> Dict[str, any]:
    """
    Get current rate limiter status.
    
    Returns:
        Dictionary with current usage and limits
    """
    return _rate_limiter.get_status()


def is_rate_limiter_healthy() -> bool:
    """
    Check if rate limiter is in a healthy state.
    
    Returns:
        True if well within limits
    """
    return _rate_limiter.is_healthy() 