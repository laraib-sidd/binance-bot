#!/usr/bin/env python3
"""
Helios Trading Bot - Development Environment Setup Script

This script automates the setup of the development environment for the Helios
trading bot, including dependency installation, directory creation, and
basic configuration setup.

Usage:
    python setup_dev_environment.py
    python setup_dev_environment.py --force
    python setup_dev_environment.py --requirements-only
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
import shutil
import subprocess
import sys

# Project root - go up one level since we're in scripts/
project_root = Path(__file__).parent.parent
logs_dir = project_root / "local" / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            logs_dir / f"setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)

logger = logging.getLogger(__name__)


class EnvironmentSetup:
    """Handles automated environment setup for the Helios trading bot."""

    def __init__(self, force: bool = False):
        self.force = force
        self.project_root = project_root
        self.setup_steps = []
        self.errors = []
        self.package_manager = "uv"  # Default to uv, will be updated during tool check

    def print_header(self):
        """Print setup header."""
        print("=" * 70)
        print("🚀 HELIOS TRADING BOT - DEVELOPMENT ENVIRONMENT SETUP")
        print("=" * 70)
        print(f"Setup Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project Root: {self.project_root}")
        print(f"Python Version: {sys.version.split()[0]}")
        print("=" * 70)
        print()

    def check_python_version(self) -> bool:
        """Check if Python version meets requirements."""
        print("🐍 Checking Python Version...")

        min_version = (3, 9, 0)
        current_version = sys.version_info[:3]

        if current_version < min_version:
            error_msg = (
                f"Python {min_version[0]}.{min_version[1]}+ required, "
                f"but {current_version[0]}.{current_version[1]}.{current_version[2]} found"
            )
            print(f"  ❌ {error_msg}")
            self.errors.append(error_msg)
            return False

        print(
            f"  ✅ Python {current_version[0]}.{current_version[1]}.{current_version[2]} is compatible"
        )
        return True

    def check_system_tools(self) -> bool:
        """Check for required system tools."""
        print("\n🛠️  Checking System Tools...")

        required_tools = ["git"]
        missing_tools = []

        for tool in required_tools:
            if not shutil.which(tool):
                missing_tools.append(tool)

        if missing_tools:
            error_msg = f"Missing required tools: {', '.join(missing_tools)}"
            print(f"  ❌ {error_msg}")
            self.errors.append(error_msg)
            return False

        return True

    def create_directory_structure(self) -> bool:
        """Create required directory structure."""
        print("\n📁 Creating Directory Structure...")

        required_directories = [
            "src",
            "src/core",
            "src/api",
            "src/data",
            "src/strategies",
            "src/risk",
            "src/backtest",
            "src/utils",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/backtest",
            "local",
            "local/data",
            "local/logs",
            "local/configs",
            "docs",
            "docs/api",
            "docs/architecture",
            "docs/guides",
        ]

        created_dirs = []
        failed_dirs = []

        for dir_path in required_directories:
            full_path = self.project_root / dir_path
            try:
                if not full_path.exists():
                    full_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(dir_path)
                    print(f"  ✅ Created: {dir_path}")
                else:
                    print(f"  ✓  Exists: {dir_path}")
            except Exception as e:
                print(f"  ❌ Failed to create {dir_path}: {e}")
                failed_dirs.append(dir_path)

        if failed_dirs:
            error_msg = f"Failed to create directories: {', '.join(failed_dirs)}"
            self.errors.append(error_msg)
            return False

        if created_dirs:
            print(f"  🎉 Created {len(created_dirs)} directories")
        else:
            print("  ✅ All directories already exist")

        return True

    def create_init_files(self) -> bool:
        """Create __init__.py files for Python packages."""
        print("\n📝 Creating Python Package Files...")

        package_dirs = [
            "src",
            "src/core",
            "src/api",
            "src/data",
            "src/strategies",
            "src/risk",
            "src/backtest",
            "src/utils",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/backtest",
        ]

        created_files = []

        for dir_path in package_dirs:
            init_file = self.project_root / dir_path / "__init__.py"
            try:
                if not init_file.exists():
                    with open(init_file, "w") as f:
                        f.write(
                            f'"""Helios Trading Bot - {dir_path.replace("/", ".")} package"""\n'
                        )
                    created_files.append(str(init_file.relative_to(self.project_root)))
                    print(f"  ✅ Created: {init_file.relative_to(self.project_root)}")
                else:
                    print(f"  ✓  Exists: {init_file.relative_to(self.project_root)}")
            except Exception as e:
                print(f"  ❌ Failed to create {init_file}: {e}")

        if created_files:
            print(f"  🎉 Created {len(created_files)} __init__.py files")
        else:
            print("  ✅ All __init__.py files already exist")

        return True

    def install_requirements(self) -> bool:
        """Install required Python packages using uv or pip."""
        print("\n📦 Installing Python Dependencies...")

        # Check if pyproject.toml exists
        pyproject_file = self.project_root / "pyproject.toml"
        if not pyproject_file.exists():
            print(
                "  ⚠️  pyproject.toml not found, this should not happen in modern setup"
            )
            return False

        try:
            if self.package_manager == "uv":
                print("  🚀 Using uv for fast dependency installation...")

                # Install dependencies with uv
                print("  Installing core dependencies...")
                result = subprocess.run(
                    ["uv", "pip", "install", "-e", "."], capture_output=True, text=True
                )

                if result.returncode == 0:
                    print("  ✅ Core dependencies installed successfully")

                    # Install dev dependencies
                    print("  Installing development dependencies...")
                    dev_result = subprocess.run(
                        ["uv", "pip", "install", "-e", ".[dev]"],
                        capture_output=True,
                        text=True,
                    )

                    if dev_result.returncode == 0:
                        print("  ✅ Development dependencies installed successfully")
                        return True
                    else:
                        print(
                            f"  ⚠️  Dev dependencies failed, but core succeeded: {dev_result.stderr}"
                        )
                        return True  # Core succeeded, dev is optional
                else:
                    print(
                        f"  ❌ Failed to install dependencies with uv: {result.stderr}"
                    )
                    self.errors.append(f"uv install failed: {result.stderr}")
                    return False

            else:  # Fallback to pip
                print("  📦 Using pip for dependency installation...")

                # Upgrade pip first
                print("  Upgrading pip...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                print("  ✅ pip upgraded successfully")

                # Install dependencies
                print("  Installing dependencies from pyproject.toml...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-e", "."],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    print("  ✅ Core dependencies installed successfully")

                    # Try to install dev dependencies
                    dev_result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
                        capture_output=True,
                        text=True,
                    )

                    if dev_result.returncode == 0:
                        print("  ✅ Development dependencies installed successfully")
                    else:
                        print("  ⚠️  Development dependencies failed (optional)")

                    return True
                else:
                    print(f"  ❌ Failed to install dependencies: {result.stderr}")
                    self.errors.append(f"pip install failed: {result.stderr}")
                    return False

        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to install dependencies: {e}")
            self.errors.append(f"Package installation failed: {e}")
            return False

    def create_sample_config_files(self) -> bool:
        """Create sample configuration files."""
        print("\n⚙️  Creating Sample Configuration Files...")

        # Create .env.template
        env_example_content = """# Helios Trading Bot Environment Configuration
# Copy this file to .env and fill in your actual values

# Binance API Configuration (REQUIRED)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BINANCE_TESTNET=true

# Environment Settings
TRADING_ENVIRONMENT=development
LOG_LEVEL=INFO
DATA_DIRECTORY=local/data

# Trading Parameters (Optional Overrides)
MAX_POSITION_SIZE_USD=100.00
MAX_DAILY_LOSS_USD=50.00
MAX_ACCOUNT_DRAWDOWN_PERCENT=25.00
GRID_LEVELS=10
GRID_SPACING_PERCENT=1.0

# Signal Settings
SIGNAL_CHECK_INTERVAL_SECONDS=30
PRICE_UPDATE_INTERVAL_SECONDS=5

# Default Trading Pairs (comma-separated)
DEFAULT_TRADING_PAIRS=SOLUSDT,AVAXUSDT,LINKUSDT,DOTUSDT,ADAUSDT
"""

        # Create config.py sample
        config_example_content = """# Helios Trading Bot - Configuration Example
# This file shows how to create a configuration without environment variables

from src.core.config import TradingConfig
from decimal import Decimal

# Example configuration (DO NOT commit with real API keys)
EXAMPLE_CONFIG = TradingConfig(
    # API Configuration (REPLACE WITH YOUR VALUES)
    binance_api_key="your_binance_api_key_here",
    binance_api_secret="your_binance_api_secret_here",
    binance_testnet=True,

    # Environment
    environment="development",
    log_level="INFO",

    # Trading Parameters
    default_trading_pairs=["SOLUSDT", "AVAXUSDT", "LINKUSDT"],
    max_position_size_usd=Decimal("100.00"),
    max_daily_loss_usd=Decimal("50.00"),

    # Grid Settings
    grid_levels=10,
    grid_spacing_percent=Decimal("1.0")
)
"""

        created_files = []

        # Create .env.template
        env_example_file = self.project_root / ".env.template"
        if not env_example_file.exists() or self.force:
            try:
                with open(env_example_file, "w") as f:
                    f.write(env_example_content)
                created_files.append(".env.template")
                print("  ✅ Created .env.template")
            except Exception as e:
                print(f"  ❌ Failed to create .env.template: {e}")
        else:
            print("  ✓  .env.template already exists")

        # Create config.example.py
        config_example_file = self.project_root / "config.example.py"
        if not config_example_file.exists() or self.force:
            try:
                with open(config_example_file, "w") as f:
                    f.write(config_example_content)
                created_files.append("config.example.py")
                print("  ✅ Created config.example.py")
            except Exception as e:
                print(f"  ❌ Failed to create config.example.py: {e}")
        else:
            print("  ✓  config.example.py already exists")

        if created_files:
            print(f"  🎉 Created {len(created_files)} configuration files")

        return True

    def setup_git_ignore(self) -> bool:
        """Setup or update .gitignore file."""
        print("\n📄 Setting up .gitignore...")

        gitignore_content = """# Helios Trading Bot - Git Ignore

# Environment and Configuration
.env
.env.local
.env.*.local
config.py

# API Keys and Secrets
**/api_keys/
**/secrets/
**/*secret*
**/*key*

# Local Data and Logs
local/
*.log
logs/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Virtual Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Trading Bot Specific
backtest_results/
live_trading_logs/
market_data_cache/
*.db
*.sqlite
*.sqlite3

# Jupyter Notebooks
.ipynb_checkpoints

# Documentation builds
docs/_build/
"""

        gitignore_file = self.project_root / ".gitignore"
        try:
            if not gitignore_file.exists() or self.force:
                with open(gitignore_file, "w") as f:
                    f.write(gitignore_content)
                print("  ✅ Created .gitignore")
            else:
                print("  ✓  .gitignore already exists")
            return True
        except Exception as e:
            print(f"  ❌ Failed to create .gitignore: {e}")
            return False

    def run_setup(self, requirements_only: bool = False) -> bool:
        """Run the complete setup process."""
        self.print_header()

        setup_steps = [
            ("Python Version Check", self.check_python_version),
            ("System Tools Check", self.check_system_tools),
        ]

        if not requirements_only:
            setup_steps.extend(
                [
                    ("Directory Structure", self.create_directory_structure),
                    ("Python Packages", self.create_init_files),
                    ("Configuration Files", self.create_sample_config_files),
                    ("Git Ignore Setup", self.setup_git_ignore),
                ]
            )

        setup_steps.append(("Python Dependencies", self.install_requirements))

        # Run setup steps
        successful_steps = 0
        total_steps = len(setup_steps)

        for step_name, step_function in setup_steps:
            try:
                if step_function():
                    successful_steps += 1
                    self.setup_steps.append((step_name, True))
                else:
                    self.setup_steps.append((step_name, False))
            except Exception as e:
                print(f"  ❌ {step_name} failed with exception: {e}")
                self.setup_steps.append((step_name, False))
                self.errors.append(f"{step_name}: {e}")

        # Print results
        self.print_results(successful_steps, total_steps, requirements_only)

        return successful_steps == total_steps

    def print_results(
        self, successful_steps: int, total_steps: int, requirements_only: bool
    ):
        """Print setup results summary."""
        print("\n" + "=" * 70)
        print("📊 SETUP RESULTS")
        print("=" * 70)

        for step_name, success in self.setup_steps:
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"  {step_name:<25} {status}")

        print(
            f"\nOverall: {successful_steps}/{total_steps} steps completed successfully"
        )

        if successful_steps == total_steps:
            print("\n🎉 SETUP COMPLETE!")
            if requirements_only:
                print("All Python dependencies have been installed.")
            else:
                print("Your development environment is ready!")
                print("\nNext steps:")
                print("1. Copy .env.template to .env and add your API credentials")
                print("2. Run: python test_environment.py")
                print("3. Start Phase 1 development!")
        else:
            print(
                f"\n⚠️  SETUP INCOMPLETE: {total_steps - successful_steps} step(s) failed"
            )
            if self.errors:
                print("\nErrors encountered:")
                for error in self.errors:
                    print(f"  - {error}")

        print("\n" + "=" * 70)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Setup Helios Trading Bot development environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_dev_environment.py                    # Full setup
  python setup_dev_environment.py --force            # Force overwrite existing files
  python setup_dev_environment.py --requirements-only # Install dependencies only
        """,
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force overwrite existing configuration files",
    )

    parser.add_argument(
        "--requirements-only",
        "-r",
        action="store_true",
        help="Only install Python requirements, skip other setup steps",
    )

    args = parser.parse_args()

    try:
        setup = EnvironmentSetup(force=args.force)
        success = setup.run_setup(requirements_only=args.requirements_only)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
