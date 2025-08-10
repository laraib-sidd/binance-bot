# Helios Trading Bot Project

## Project Overview

This repository contains the design and implementation plan for **Helios**, an aggressive-growth cryptocurrency trading bot built from scratch in Python. The bot implements a unique **Signal-Driven Dynamic Grid Trading** strategy designed to generate steady weekly income through high-frequency automated trading.

## Conversation Summary

This project emerged from a comprehensive analysis of trading bot strategies and requirements. Key highlights:

- **Goal**: Build a profitable crypto trading bot for aggressive growth (30-40% monthly returns target)
- **Capital**: Starting with $700
- **Experience Level**: Intermediate trader with Python/Data Engineering background
- **Strategy**: Custom hybrid approach combining signal analysis with dynamic grid trading
- **Market Focus**: High-volume altcoins for maximum volatility and profit potential

## Project Components

### 📋 Documentation Files
- `requirements_analysis.md` - Detailed Q&A session defining project requirements
- `strategy_analysis.md` - In-depth comparison of different trading strategies
- `design_document.md` - Complete technical specification for the Helios bot
- `risk_management.md` - Comprehensive risk management framework
- `development_roadmap.md` - Step-by-step implementation timeline

### 🚀 Key Features
- **Signal-Driven Entry**: Only trades when market conditions are optimal
- **Dynamic Grid**: Automatically adjusts grid width based on volatility (ATR)
- **Risk Management**: Built-in stop-losses and position sizing controls
- **Multi-Exchange Support**: Designed for Binance and Coinbase
- **Real-time Monitoring**: Continuous market analysis and trade execution

### 💡 Unique Strategy: Signal-Driven Dynamic Grid

Unlike standard trading bots, Helios combines:
1. **Entry Signals** - Volatility and volume filters to identify optimal trading windows
2. **Dynamic Grids** - ATR-based grid sizing that adapts to market conditions
3. **Smart Exit** - Automatic session termination to prevent major losses

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (recommended for best performance)
- **Binance Testnet Account** for API keys
- **UV Package Manager** (optional, but 10-100x faster than pip)

### Installation

```bash
# Clone the repository
git clone https://github.com/laraib-sidd/binance-bot.git
cd binance-bot

# Option 1: Fast setup with UV (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install UV
python3 scripts/setup_dev_environment.py        # Auto-detects UV

# Option 2: Traditional setup with pip
python3 scripts/setup_dev_environment.py        # Auto-detects pip

# Test your environment
python3 scripts/test_environment.py
```

### Configuration

**Step 1: Get Binance API Keys**
1. Go to [Binance Testnet](https://testnet.binance.vision/)
2. Create account and generate API keys
3. Choose **"System generated"** (HMAC) when prompted

**Step 2: Configure Credentials**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your API credentials
# BINANCE_API_KEY=your_actual_api_key_here
# BINANCE_API_SECRET=your_actual_api_secret_here
```

**Step 3: Test Configuration**
```bash
# Test that configuration loads correctly
python3 -c "
import sys
sys.path.insert(0, 'src')
from src.core.config import load_configuration
config = load_configuration()
print(f'✅ Environment: {config.environment}')
print(f'✅ API Keys: {\"Configured\" if config.binance_api_key else \"Missing\"}')
print(f'✅ Trading Pairs: {len(config.default_trading_pairs)} configured')
"
```

### Development Commands

```bash
# Format code
uv run black src tests

# Lint code
uv run ruff check src tests

# Type checking
uv run mypy src

# Run tests
uv run pytest

# Or use traditional pip commands
python3 -m black src tests
python3 -m pytest
```

## Project Status

- [x] Requirements Analysis Complete
- [x] Strategy Design Finalized
- [x] Technical Architecture Defined
- [ ] Phase 1: Setup & Connection
- [ ] Phase 2: Data Engine & Signal Generation
- [ ] Phase 3: Core Grid & Order Logic
- [ ] Phase 4: Backtesting
- [ ] Phase 5: Paper Trading & Deployment

## Risk Warning

⚠️ **High-Risk Strategy**: This bot is designed for aggressive trading with high return expectations. The target of 30-40% monthly returns carries significant risk of loss. Always start with paper trading and small amounts.

## Target Performance
- **Realistic Expectation**: 5-15% monthly returns
- **Aggressive Goal**: 30-40% monthly returns (high risk)
- **Risk Management**: 1% risk per trade, 25% max drawdown circuit breaker

## Technology Stack
- **Language**: Python 3.9+
- **Exchanges**: Binance (primary), Coinbase (secondary)
- **Key Libraries**: python-binance, pandas, pandas-ta, apscheduler
- **Infrastructure**: Local development, cloud VPS for production

## Contributing

This is a personal trading project. Please review the risk management guidelines before making any modifications.

## License

This project is for educational and personal use only. Use at your own risk.
