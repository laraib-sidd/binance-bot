# 🚀 Helios Trading Bot - UV Setup Guide

## Quick Start with UV (Recommended)

**UV** is the fastest Python package manager and is now the recommended way to manage dependencies for the Helios trading bot.

### **1. Install UV**

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip if you prefer
pip install uv
```

### **2. Clone and Setup**

```bash
# Clone the repository
git clone https://github.com/laraib-sidd/binance-bot.git
cd binance-bot

# Quick setup with uv
uv pip install -e .
uv pip install -e .[dev]
```

### **3. Run Tests**

```bash
# Test environment
python test_environment.py

# Run setup validation
python setup_dev_environment.py
```

## Why UV?

- **⚡ 10-100x faster** than pip
- **🔒 Reliable dependency resolution**
- **🎯 Modern Python tooling**
- **🔄 Backward compatible** with pip

## Project Structure

The project uses `pyproject.toml` for modern Python packaging:

- **Core dependencies**: Trading APIs, data processing
- **Dev dependencies**: Testing, linting, formatting
- **Optional groups**: Visualization, notifications, backtesting

## Available Commands

```bash
# Install core dependencies only
uv pip install -e .

# Install with development tools
uv pip install -e .[dev]

# Install with all optional dependencies
uv pip install -e .[all]

# Specific groups
uv pip install -e .[viz]          # Visualization tools
uv pip install -e .[notifications] # Telegram/Discord bots
uv pip install -e .[backtest]     # Backtesting tools
```

## Environment Setup

```bash
# Set your API credentials
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"

# Or create .env file
cp .env.example .env
# Edit .env with your credentials
```

## Development Workflow

```bash
# Format code
uv run black src tests

# Lint code
uv run ruff check src tests

# Type checking
uv run mypy src

# Run tests
uv run pytest
```

## Fallback to Pip

If you prefer pip, the project still works:

```bash
pip install -e .
pip install -e .[dev]
```

The setup scripts automatically detect which package manager you have available and use the fastest one. 