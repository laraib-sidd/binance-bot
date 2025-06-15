# Helios Trading Bot - Configuration Example
# Copy this file to config.py and fill in your actual values

import os
from dataclasses import dataclass
from typing import List

@dataclass
class TradingConfig:
    """
    Trading bot configuration settings
    Copy this file to config.py and update with your actual values
    """
    
    # Exchange API Settings
    exchange_name: str = "binance"
    api_key: str = "your_binance_api_key_here"
    api_secret: str = "your_binance_api_secret_here"
    testnet: bool = True  # ALWAYS start with testnet!
    
    # Risk Management Settings
    risk_per_trade: float = 0.01        # 1% risk per grid session
    max_drawdown: float = 0.25          # 25% maximum account drawdown
    daily_loss_limit: float = 0.05      # 5% daily loss limit
    
    # Strategy Parameters
    grid_levels: int = 8                # Number of grid levels
    grid_range_multiplier: float = 2.0  # ATR multiplier for grid range
    
    # Signal Thresholds
    atr_threshold_multiplier: float = 1.2     # Volatility filter
    volume_threshold_multiplier: float = 1.1  # Volume filter
    
    # Trading Pairs (High volatility altcoins recommended)
    trading_pairs: List[str] = None
    
    # Notification Settings
    telegram_bot_token: str = "your_telegram_bot_token"
    telegram_chat_id: str = "your_telegram_chat_id"
    
    # Performance Targets
    target_monthly_return: float = 0.15    # 15% monthly target (realistic)
    target_win_rate: float = 0.65          # 65% win rate target
    
    def __post_init__(self):
        if self.trading_pairs is None:
            self.trading_pairs = [
                'SOLUSDT',   # Solana - High volatility
                'AVAXUSDT',  # Avalanche - Layer 1
                'LINKUSDT',  # Chainlink - Oracle
                'MATICUSDT', # Polygon - Scaling
                'ADAUSDT'    # Cardano - Smart contracts
            ]
    
    def validate(self):
        """Validate configuration parameters"""
        if not self.api_key or self.api_key == "your_binance_api_key_here":
            raise ValueError("Please set your actual Binance API key")
        
        if not self.api_secret or self.api_secret == "your_binance_api_secret_here":
            raise ValueError("Please set your actual Binance API secret")
        
        if self.risk_per_trade > 0.05:  # 5% max
            raise ValueError("Risk per trade too high - maximum 5%")
        
        if self.max_drawdown > 0.5:  # 50% max
            raise ValueError("Max drawdown too high - maximum 50%")
        
        if not self.testnet:
            print("WARNING: Testnet is disabled. Are you sure you want to trade with real money?")

# Environment-based configuration (alternative approach)
def load_config_from_env():
    """Load configuration from environment variables"""
    return TradingConfig(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        testnet=os.getenv("USE_TESTNET", "True").lower() == "true",
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "")
    )

# Usage:
# config = TradingConfig()
# config.validate()
# 
# Or load from environment:
# config = load_config_from_env()
# config.validate() 