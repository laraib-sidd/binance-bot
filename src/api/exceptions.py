"""
Helios Trading Bot - API Exceptions

Custom exception classes for handling various types of API errors with
appropriate security measures for financial applications.

Key Features:
- Hierarchical exception structure for specific error handling
- Security-conscious error messages (no sensitive data exposure)
- Retry-friendly error classification
- Comprehensive error context preservation
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BinanceAPIError(Exception):
    """
    Base exception for all Binance API related errors.
    
    Provides common functionality for error logging, context preservation,
    and security-conscious error handling.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        http_status: Optional[int] = None,
        retry_after: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize API exception with comprehensive error context.
        
        Args:
            message: Human-readable error description
            error_code: Binance-specific error code 
            http_status: HTTP status code from response
            retry_after: Seconds to wait before retry (if applicable)
            context: Additional context (sanitized, no sensitive data)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.http_status = http_status
        self.retry_after = retry_after
        self.context = context or {}
        
        # Log error (without sensitive information)
        self._log_error()
    
    def _log_error(self) -> None:
        """Log error details safely (no sensitive data)."""
        safe_context = self._sanitize_context(self.context)
        logger.error(
            f"Binance API Error: {self.message} "
            f"[Code: {self.error_code}, Status: {self.http_status}] "
            f"Context: {safe_context}"
        )
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from context before logging."""
        sensitive_keys = {
            'api_key', 'secret', 'signature', 'password', 'token',
            'key', 'auth', 'credential', 'private'
        }
        
        safe_context = {}
        for key, value in context.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                safe_context[key] = '[REDACTED]'
            elif isinstance(value, str) and len(value) > 50:
                # Truncate long strings that might contain sensitive data
                safe_context[key] = value[:50] + '...'
            else:
                safe_context[key] = value
        
        return safe_context
    
    def is_retryable(self) -> bool:
        """
        Determine if this error condition is retryable.
        
        Returns:
            True if the operation can be safely retried
        """
        return False  # Default: don't retry unless specifically overridden
    
    def get_retry_delay(self) -> int:
        """
        Get recommended retry delay in seconds.
        
        Returns:
            Seconds to wait before retry, or 0 if not retryable
        """
        if self.retry_after:
            return self.retry_after
        return 0


class AuthenticationError(BinanceAPIError):
    """
    API authentication failed.
    
    Raised when API keys are invalid, expired, or lack required permissions.
    This is typically not retryable without fixing credentials.
    """
    
    def __init__(self, message: str = "API authentication failed", **kwargs):
        super().__init__(message, **kwargs)
    
    def is_retryable(self) -> bool:
        """Authentication errors are not retryable."""
        return False


class RateLimitError(BinanceAPIError):
    """
    API rate limit exceeded.
    
    Raised when hitting Binance API rate limits. This is retryable
    after waiting for the specified period.
    """
    
    def __init__(
        self,
        message: str = "API rate limit exceeded",
        retry_after: int = 60,
        **kwargs
    ):
        super().__init__(message, retry_after=retry_after, **kwargs)
    
    def is_retryable(self) -> bool:
        """Rate limit errors are retryable after waiting."""
        return True
    
    def get_retry_delay(self) -> int:
        """Return the rate limit reset time."""
        return self.retry_after or 60


class NetworkError(BinanceAPIError):
    """
    Network connectivity or communication error.
    
    Raised for timeouts, connection failures, or other network issues.
    Usually retryable with exponential backoff.
    """
    
    def __init__(self, message: str = "Network communication error", **kwargs):
        super().__init__(message, **kwargs)
    
    def is_retryable(self) -> bool:
        """Network errors are generally retryable."""
        return True
    
    def get_retry_delay(self) -> int:
        """Progressive retry delay for network issues."""
        return 5  # Start with 5 seconds, caller should implement exponential backoff


class InvalidResponseError(BinanceAPIError):
    """
    API returned invalid or malformed response.
    
    Raised when the API response doesn't match expected format or
    contains invalid data that can't be processed.
    """
    
    def __init__(self, message: str = "Invalid API response format", **kwargs):
        super().__init__(message, **kwargs)
    
    def is_retryable(self) -> bool:
        """Invalid responses might be temporary."""
        return True
    
    def get_retry_delay(self) -> int:
        """Short retry delay for response format issues."""
        return 2


class InsufficientPermissionsError(BinanceAPIError):
    """
    API key lacks required permissions.
    
    Raised when the API key doesn't have the necessary permissions
    for the requested operation (e.g., trading permissions required).
    """
    
    def __init__(self, message: str = "Insufficient API permissions", **kwargs):
        super().__init__(message, **kwargs)
    
    def is_retryable(self) -> bool:
        """Permission errors are not retryable."""
        return False


class ServerError(BinanceAPIError):
    """
    Binance server-side error.
    
    Raised for HTTP 5xx errors indicating issues on Binance's side.
    Usually retryable as these are temporary server issues.
    """
    
    def __init__(self, message: str = "Binance server error", **kwargs):
        super().__init__(message, **kwargs)
    
    def is_retryable(self) -> bool:
        """Server errors are typically retryable."""
        return True
    
    def get_retry_delay(self) -> int:
        """Longer delay for server errors."""
        return 10


class DataValidationError(BinanceAPIError):
    """
    Market data failed validation checks.
    
    Raised when received market data doesn't pass validation rules
    (e.g., negative prices, future timestamps, etc.).
    """
    
    def __init__(self, message: str = "Market data validation failed", **kwargs):
        super().__init__(message, **kwargs)
    
    def is_retryable(self) -> bool:
        """Data validation errors are retryable."""
        return True
    
    def get_retry_delay(self) -> int:
        """Short delay for data validation issues."""
        return 1


def classify_binance_error(
    error_code: str,
    http_status: int,
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> BinanceAPIError:
    """
    Classify a Binance API error and return appropriate exception.
    
    Args:
        error_code: Binance error code from response
        http_status: HTTP status code
        message: Error message from API
        context: Additional error context
    
    Returns:
        Appropriate BinanceAPIError subclass instance
    """
    # Authentication and permission errors
    if error_code in ['-2014', '-2015'] or http_status == 401:
        return AuthenticationError(message, error_code=error_code, 
                                 http_status=http_status, context=context)
    
    if error_code in ['-2010', '-2011']:
        return InsufficientPermissionsError(message, error_code=error_code,
                                          http_status=http_status, context=context)
    
    # Rate limiting
    if error_code == '-1003' or http_status == 429:
        # Extract retry-after from headers if available
        retry_after = context.get('retry_after', 60) if context else 60
        return RateLimitError(message, error_code=error_code,
                            http_status=http_status, retry_after=retry_after,
                            context=context)
    
    # Server errors (5xx)
    if http_status and 500 <= http_status < 600:
        return ServerError(message, error_code=error_code,
                         http_status=http_status, context=context)
    
    # Network/connectivity issues
    if http_status in [0, 408, 502, 503, 504]:
        return NetworkError(message, error_code=error_code,
                          http_status=http_status, context=context)
    
    # Default: generic API error
    return BinanceAPIError(message, error_code=error_code,
                          http_status=http_status, context=context) 