"""
Helios Trading Bot - API Data Models

Data models for Binance API responses with proper typing, validation,
and decimal precision for financial calculations.

Key Features:
- Type-safe data models with comprehensive validation
- Decimal precision for all financial values 
- Immutable data structures for consistency
- Automatic data conversion and normalization
- Security-conscious handling of sensitive data
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TickerData:
    """
    Real-time ticker data for a trading pair.
    
    Contains current price, volume, and price change information.
    All financial values use Decimal for precision.
    """
    symbol: str
    price: Decimal
    bid_price: Decimal
    ask_price: Decimal
    volume_24h: Decimal
    price_change_24h: Decimal
    price_change_percent_24h: Decimal
    high_24h: Decimal
    low_24h: Decimal
    timestamp: datetime
    
    @classmethod
    def from_binance_response(cls, data: Dict[str, Any]) -> 'TickerData':
        """
        Create TickerData from Binance API response.
        
        Args:
            data: Raw response from Binance 24hr ticker endpoint
            
        Returns:
            Validated TickerData instance
            
        Raises:
            ValueError: If data is invalid or missing required fields
        """
        try:
            return cls(
                symbol=str(data['symbol']),
                price=Decimal(str(data['lastPrice'])),
                bid_price=Decimal(str(data['bidPrice'])),
                ask_price=Decimal(str(data['askPrice'])),
                volume_24h=Decimal(str(data['volume'])),
                price_change_24h=Decimal(str(data['priceChange'])),
                price_change_percent_24h=Decimal(str(data['priceChangePercent'])),
                high_24h=Decimal(str(data['highPrice'])),
                low_24h=Decimal(str(data['lowPrice'])),
                timestamp=datetime.fromtimestamp(int(data['closeTime']) / 1000)
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse ticker data: {e}")
            raise ValueError(f"Invalid ticker data format: {e}")
    
    def validate(self) -> bool:
        """
        Validate ticker data for financial reasonableness.
        
        Returns:
            True if data passes validation
            
        Raises:
            ValueError: If data fails validation
        """
        # Price validation
        if self.price <= 0:
            raise ValueError(f"Invalid price: {self.price}")
        
        if self.bid_price <= 0 or self.ask_price <= 0:
            raise ValueError(f"Invalid bid/ask: {self.bid_price}/{self.ask_price}")
        
        if self.bid_price > self.ask_price:
            raise ValueError(f"Bid price {self.bid_price} > ask price {self.ask_price}")
        
        # Volume validation
        if self.volume_24h < 0:
            raise ValueError(f"Invalid volume: {self.volume_24h}")
        
        # Range validation
        if self.low_24h > self.high_24h:
            raise ValueError(f"Low {self.low_24h} > high {self.high_24h}")
        
        if not (self.low_24h <= self.price <= self.high_24h):
            raise ValueError(f"Price {self.price} outside 24h range [{self.low_24h}, {self.high_24h}]")
        
        # Timestamp validation (not too far in past/future)
        now = datetime.now()
        age_seconds = (now - self.timestamp).total_seconds()
        if abs(age_seconds) > 3600:  # 1 hour tolerance
            raise ValueError(f"Timestamp too old/future: {self.timestamp}")
        
        return True


@dataclass(frozen=True)
class KlineData:
    """
    OHLCV (candlestick) data for technical analysis.
    
    Contains open, high, low, close, volume data for a specific time period.
    Essential for technical analysis and strategy backtesting.
    """
    symbol: str
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    number_of_trades: int
    interval: str  # e.g., "1m", "5m", "1h", "1d"
    
    @classmethod
    def from_binance_response(cls, symbol: str, interval: str, data: List[Any]) -> 'KlineData':
        """
        Create KlineData from Binance API kline response.
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval (1m, 5m, 1h, etc.)
            data: Raw kline data array from Binance
            
        Returns:
            Validated KlineData instance
        """
        try:
            return cls(
                symbol=symbol,
                open_time=datetime.fromtimestamp(int(data[0]) / 1000),
                close_time=datetime.fromtimestamp(int(data[6]) / 1000),
                open_price=Decimal(str(data[1])),
                high_price=Decimal(str(data[2])),
                low_price=Decimal(str(data[3])),
                close_price=Decimal(str(data[4])),
                volume=Decimal(str(data[5])),
                number_of_trades=int(data[8]),
                interval=interval
            )
        except (IndexError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse kline data: {e}")
            raise ValueError(f"Invalid kline data format: {e}")
    
    def validate(self) -> bool:
        """Validate OHLCV data for consistency."""
        # Price validation
        if any(price <= 0 for price in [self.open_price, self.high_price, 
                                       self.low_price, self.close_price]):
            raise ValueError("Prices must be positive")
        
        # OHLC relationship validation
        if self.high_price < max(self.open_price, self.close_price):
            raise ValueError("High price below open/close")
        
        if self.low_price > min(self.open_price, self.close_price):
            raise ValueError("Low price above open/close")
        
        if self.low_price > self.high_price:
            raise ValueError("Low price above high price")
        
        # Volume validation
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
        
        if self.number_of_trades < 0:
            raise ValueError("Trade count cannot be negative")
        
        # Time validation
        if self.close_time <= self.open_time:
            raise ValueError("Close time must be after open time")
        
        return True


@dataclass(frozen=True)
class AccountInfo:
    """
    Binance account information including balances and permissions.
    
    Contains account status, balances, and trading permissions.
    Sensitive financial data handled securely.
    """
    account_type: str
    can_trade: bool
    can_withdraw: bool
    can_deposit: bool
    update_time: datetime
    total_wallet_balance: Decimal
    total_unrealized_pnl: Decimal
    balances: Dict[str, Decimal] = field(default_factory=dict)
    
    @classmethod
    def from_binance_response(cls, data: Dict[str, Any]) -> 'AccountInfo':
        """
        Create AccountInfo from Binance account endpoint response.
        
        Args:
            data: Raw response from Binance account endpoint
            
        Returns:
            Validated AccountInfo instance
        """
        try:
            # Parse balances
            balances = {}
            for balance in data.get('balances', []):
                asset = balance['asset']
                free = Decimal(str(balance['free']))
                locked = Decimal(str(balance['locked']))
                total = free + locked
                if total > 0:  # Only include non-zero balances
                    balances[asset] = total
            
            return cls(
                account_type=str(data.get('accountType', 'SPOT')),
                can_trade=bool(data.get('canTrade', False)),
                can_withdraw=bool(data.get('canWithdraw', False)),
                can_deposit=bool(data.get('canDeposit', False)),
                update_time=datetime.fromtimestamp(int(data['updateTime']) / 1000),
                total_wallet_balance=Decimal(str(data.get('totalWalletBalance', '0'))),
                total_unrealized_pnl=Decimal(str(data.get('totalUnrealizedProfit', '0'))),
                balances=balances
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse account info: {e}")
            raise ValueError(f"Invalid account info format: {e}")
    
    def get_balance(self, asset: str) -> Decimal:
        """
        Get balance for a specific asset.
        
        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')
            
        Returns:
            Balance amount, or Decimal('0') if not found
        """
        return self.balances.get(asset.upper(), Decimal('0'))
    
    def validate(self) -> bool:
        """Validate account information."""
        # Balance validation
        for asset, balance in self.balances.items():
            if balance < 0:
                raise ValueError(f"Negative balance for {asset}: {balance}")
        
        # Wallet balance validation
        if self.total_wallet_balance < 0:
            raise ValueError(f"Negative total wallet balance: {self.total_wallet_balance}")
        
        return True
    
    def __str__(self) -> str:
        """String representation without sensitive balance details."""
        return (f"AccountInfo(type={self.account_type}, "
                f"can_trade={self.can_trade}, "
                f"assets={len(self.balances)})")


@dataclass(frozen=True)
class ExchangeInfo:
    """
    Binance exchange information including symbol details and limits.
    
    Contains trading rules, filters, and limits for trading pairs.
    Critical for order validation and trading compliance.
    """
    server_time: datetime
    symbols: Dict[str, 'SymbolInfo'] = field(default_factory=dict)
    
    @classmethod
    def from_binance_response(cls, data: Dict[str, Any]) -> 'ExchangeInfo':
        """Create ExchangeInfo from Binance exchange info response."""
        try:
            symbols = {}
            for symbol_data in data.get('symbols', []):
                symbol_info = SymbolInfo.from_binance_response(symbol_data)
                symbols[symbol_info.symbol] = symbol_info
            
            return cls(
                server_time=datetime.fromtimestamp(int(data['serverTime']) / 1000),
                symbols=symbols
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse exchange info: {e}")
            raise ValueError(f"Invalid exchange info format: {e}")
    
    def get_symbol_info(self, symbol: str) -> Optional['SymbolInfo']:
        """Get trading info for a specific symbol."""
        return self.symbols.get(symbol.upper())


@dataclass(frozen=True)
class SymbolInfo:
    """
    Trading information for a specific symbol/trading pair.
    
    Contains precision, filters, and trading rules for the symbol.
    """
    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    base_precision: int
    quote_precision: int
    min_qty: Decimal
    max_qty: Decimal
    step_size: Decimal
    min_price: Decimal
    max_price: Decimal
    tick_size: Decimal
    min_notional: Decimal
    
    @classmethod
    def from_binance_response(cls, data: Dict[str, Any]) -> 'SymbolInfo':
        """Create SymbolInfo from Binance symbol data."""
        try:
            # Extract filters
            filters = {f['filterType']: f for f in data.get('filters', [])}
            
            lot_size = filters.get('LOT_SIZE', {})
            price_filter = filters.get('PRICE_FILTER', {})
            min_notional = filters.get('MIN_NOTIONAL', {})
            
            return cls(
                symbol=str(data['symbol']),
                status=str(data['status']),
                base_asset=str(data['baseAsset']),
                quote_asset=str(data['quoteAsset']),
                base_precision=int(data['baseAssetPrecision']),
                quote_precision=int(data['quotePrecision']),
                min_qty=Decimal(str(lot_size.get('minQty', '0'))),
                max_qty=Decimal(str(lot_size.get('maxQty', '0'))),
                step_size=Decimal(str(lot_size.get('stepSize', '0'))),
                min_price=Decimal(str(price_filter.get('minPrice', '0'))),
                max_price=Decimal(str(price_filter.get('maxPrice', '0'))),
                tick_size=Decimal(str(price_filter.get('tickSize', '0'))),
                min_notional=Decimal(str(min_notional.get('minNotional', '0')))
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse symbol info: {e}")
            raise ValueError(f"Invalid symbol info format: {e}")
    
    def is_trading_enabled(self) -> bool:
        """Check if trading is enabled for this symbol."""
        return self.status == 'TRADING' 