# Helios Trading Bot - Technical Design Document

## Executive Summary

**Helios** is a Signal-Driven Dynamic Grid Trading bot designed for aggressive cryptocurrency trading. It combines intelligent market analysis with adaptive grid trading to maximize profit opportunities while maintaining strict risk controls.

**Key Innovation**: Unlike static grid bots, Helios only deploys grids when market conditions are optimal and dynamically adjusts grid parameters based on real-time volatility.

## System Architecture

### High-Level Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Engine   │    │  Signal Engine  │    │  Grid Manager   │
│                 │    │                 │    │                 │
│ • Price feeds   │────│ • ATR analysis  │────│ • Order mgmt    │
│ • Volume data   │    │ • Volume filter │    │ • Position      │
│ • Indicators    │    │ • Entry signals │    │   tracking      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Risk Controller │
                    │                 │
                    │ • Stop losses   │
                    │ • Position size │
                    │ • Drawdown mgmt │
                    └─────────────────┘
```

### Technology Stack

**Core Framework**
- **Language**: Python 3.9+
- **Architecture**: Event-driven, modular design
- **Concurrency**: AsyncIO for non-blocking operations
- **Data Storage**: SQLite for trade logs and performance tracking

**Key Dependencies**
```python
# requirements.txt
python-binance==1.0.19      # Exchange API
pandas==2.1.0               # Data manipulation
pandas-ta==0.3.14b          # Technical indicators
numpy==1.24.3               # Numerical operations
apscheduler==3.10.4         # Task scheduling
aiohttp==3.8.5              # Async HTTP client
sqlalchemy==2.0.20          # Database ORM
python-dotenv==1.0.0        # Environment variables
pytest==7.4.2              # Testing framework
```

## Core Strategy Logic

### 1. Market Scanning & Entry Signals

The bot continuously monitors market conditions and only activates when all criteria are met:

```python
def check_entry_signal(symbol_data):
    """
    Multi-factor analysis for optimal entry timing
    Returns: (bool, confidence_score)
    """
    
    # Factor 1: Volatility Filter
    atr_14 = calculate_atr(symbol_data, period=14)
    atr_threshold = atr_14.rolling(50).mean() * 1.2
    volatility_ok = atr_14 > atr_threshold
    
    # Factor 2: Volume Confirmation
    volume_ma_20 = symbol_data['volume'].rolling(20).mean()
    volume_ok = symbol_data['volume'][-1] > volume_ma_20[-1] * 1.1
    
    # Factor 3: Price Action Filter
    price_range = symbol_data['high'][-5:].max() - symbol_data['low'][-5:].min()
    price_ok = price_range > (atr_14 * 0.8)
    
    # Factor 4: Time-based Filter (avoid weekends, major events)
    time_ok = check_trading_hours()
    
    entry_signal = all([volatility_ok, volume_ok, price_ok, time_ok])
    confidence = calculate_confidence_score(volatility_ok, volume_ok, price_ok)
    
    return entry_signal, confidence
```

### 2. Dynamic Grid Configuration

When entry signal triggers, the bot calculates optimal grid parameters:

```python
def calculate_grid_parameters(current_price, atr_14, account_balance):
    """
    Calculate dynamic grid based on market volatility
    """
    
    # Grid range based on ATR (volatility-adaptive)
    grid_range_multiplier = 2.0  # Conservative setting
    grid_upper = current_price + (atr_14 * grid_range_multiplier)
    grid_lower = current_price - (atr_14 * grid_range_multiplier)
    
    # Fixed number of grid levels for consistent risk management
    grid_levels = 8
    grid_spacing = (grid_upper - grid_lower) / grid_levels
    
    # Position sizing (1% risk per grid session)
    max_risk_per_session = account_balance * 0.01
    total_buy_orders = grid_levels // 2
    order_size = max_risk_per_session / total_buy_orders
    
    return {
        'upper_bound': grid_upper,
        'lower_bound': grid_lower,
        'levels': grid_levels,
        'spacing': grid_spacing,
        'order_size': order_size,
        'session_id': generate_session_id()
    }
```

## Risk Management Framework

### 1. Position Sizing Rules

```python
class RiskManager:
    def __init__(self, initial_balance):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.max_drawdown_percent = 0.25  # 25% circuit breaker
        self.risk_per_trade_percent = 0.01  # 1% per grid session
    
    def validate_new_position(self, proposed_risk):
        """Validate if new position meets risk criteria"""
        
        # Check account-level drawdown
        current_drawdown = (self.initial_balance - self.current_balance) / self.initial_balance
        if current_drawdown >= self.max_drawdown_percent:
            raise RiskLimitExceeded("Maximum drawdown reached")
        
        # Check position size
        max_position_size = self.current_balance * self.risk_per_trade_percent
        if proposed_risk > max_position_size:
            raise RiskLimitExceeded("Position size too large")
        
        return True
```

## Configuration Management

### 1. Environment Configuration

```python
# config.py
import os
from dataclasses import dataclass
from typing import List

@dataclass
class TradingConfig:
    # Exchange settings
    exchange_name: str = "binance"
    api_key: str = os.getenv("BINANCE_API_KEY")
    api_secret: str = os.getenv("BINANCE_API_SECRET")
    testnet: bool = True  # Start with paper trading
    
    # Strategy parameters
    risk_per_trade: float = 0.01  # 1% per grid session
    max_drawdown: float = 0.25    # 25% circuit breaker
    grid_levels: int = 8
    grid_range_multiplier: float = 2.0
    
    # Signal thresholds
    atr_threshold_multiplier: float = 1.2
    volume_threshold_multiplier: float = 1.1
    
    # Trading pairs
    trading_pairs: List[str] = None
    
    def __post_init__(self):
        if self.trading_pairs is None:
            self.trading_pairs = [
                'SOLUSDT',   # High volatility altcoin
                'AVAXUSDT',  # Layer 1 blockchain
                'LINKUSDT',  # Oracle network
                'MATICUSDT', # Polygon scaling
                'ADAUSDT'    # Cardano
            ]
```

## Expected Performance Targets

**Conservative Scenario (Realistic)**
- Monthly Return: 5-15%
- Win Rate: 65-75%
- Maximum Drawdown: 10-15%
- Sharpe Ratio: >1.2

**Aggressive Scenario (Target)**
- Monthly Return: 20-35%
- Win Rate: 60-70%
- Maximum Drawdown: 15-25%
- Sharpe Ratio: >1.0

The system is designed to automatically scale down risk when performance degrades and scale up when conditions improve, ensuring long-term capital preservation while maximizing profit opportunities. 