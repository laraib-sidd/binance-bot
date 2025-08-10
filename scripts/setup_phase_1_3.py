#!/usr/bin/env python3
"""
Helios Trading Bot - Phase 1.3 Setup Script

Sets up the data pipeline dependencies and environment for Phase 1.3.

Usage:
    python scripts/setup_phase_1_3.py
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys


def print_status(message, status="info"):
    """Print a formatted status message."""
    color_map = {
        "info": "\033[94m",  # Blue
        "success": "\033[92m",  # Green
        "warning": "\033[93m",  # Yellow
        "error": "\033[91m",  # Red
        "running": "\033[96m",  # Cyan
        "reset": "\033[0m",
    }
    print(f"{color_map.get(status, '')}▶ {message}{color_map['reset']}")


def print_guidance(message):
    """Print a formatted guidance message."""
    print(f"  💡 \033[93m{message}\033[0m")


def print_separator():
    """Print a visual separator."""
    print("-" * 60)


def initial_setup_message():
    """Print the initial setup message."""
    print_separator()
    print_status("Helios Trading Bot - Phase 1.3 Setup", "info")
    print_status("This script will verify your environment configuration.", "info")
    print_separator()


def check_python_version():
    """Check if the Python version is 3.10 or higher."""
    print_status("Checking Python version", "running")
    if sys.version_info < (3, 10):
        print_status(f"Python version {sys.version} is too old.", "error")
        print_guidance("Please use Python 3.10 or newer.")
        return False
    print_status(f"Python version {sys.version} is sufficient.", "success")
    return True


def check_uv_installed():
    """Check if 'uv' is installed."""
    print_status("Checking for 'uv' package manager", "running")
    if not shutil.which("uv"):
        print_status("'uv' is not installed or not in PATH.", "error")
        print_guidance("Please install it from https://github.com/astral-sh/uv")
        return False
    print_status("'uv' is installed.", "success")
    return True


def check_dependencies_installed():
    """Check if Python dependencies are installed using uv."""
    print_status("Checking Python dependencies", "running")
    try:
        # We check for a core dependency to see if `uv pip install` was run
        subprocess.check_call(
            ["uv", "pip", "check"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print_status("Python dependencies are installed.", "success")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_status("Dependencies are not installed.", "error")
        print_guidance("Run 'uv pip install -e .[dev]' to install them.")
        return False


def _check_variable(var: str, check_fn: callable) -> bool:
    """Helper to check a single environment variable."""
    value = os.getenv(var)
    if not value:
        print_status(f"Missing required environment variable: {var}", "error")
        return False
    try:
        if not check_fn(value):
            print_status(f"Invalid format or value for {var}", "error")
            return False
    except ValueError as e:
        print_status(f"Validation failed for {var}: {e}", "error")
        return False
    return True


def check_environment_variables() -> bool:
    """Check if required environment variables are set."""
    print_status("Checking environment variables", "running")
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        print_status(".env file not found.", "warning")
        print_guidance(f"Please create it at {env_file}")
        return False

    checks = {
        "POSTGRES_USER": lambda v: True,
        "POSTGRES_PASSWORD": lambda v: True,
        "POSTGRES_DB": lambda v: True,
        "POSTGRES_HOST": lambda v: True,
        "POSTGRES_PORT": lambda v: v.isdigit(),
        "REDIS_HOST": lambda v: True,
        "REDIS_PORT": lambda v: v.isdigit(),
        "R2_ACCOUNT_ID": lambda v: True,
        "R2_ACCESS_KEY_ID": lambda v: True,
        "R2_SECRET_ACCESS_KEY": lambda v: True,
        "R2_BUCKET_NAME": lambda v: True,
        "BINANCE_API_KEY": lambda v: True,
        "BINANCE_API_SECRET": lambda v: True,
    }

    all_ok = all(_check_variable(var, check) for var, check in checks.items())

    if all_ok:
        print_status("All environment variables are set correctly.", "success")
    else:
        print_status(
            "One or more environment variables are missing or invalid.", "error"
        )
        print_guidance("Please check your .env file against .env.example.")
    return all_ok


def test_imports():
    """Test if required packages can be imported."""
    print_status("Testing critical imports", "running")
    try:
        import asyncpg  # noqa: F401
        import boto3  # noqa: F401
        import polars  # noqa: F401
        import redis  # noqa: F401

        print_status("Critical library imports successful.", "success")
        return True
    except ImportError as e:
        print_status(f"Missing required Python package: {e.name}", "error")
        print_guidance("Please run 'uv pip install -e .[dev]' again.")
        return False


def main():
    """Main function to run the setup and validation checks."""
    initial_setup_message()
    checks = [
        check_python_version,
        check_uv_installed,
        check_dependencies_installed,
        check_environment_variables,
        test_imports,
    ]
    success_count = sum(check() for check in checks)

    print_separator()
    if success_count == len(checks):
        print_status(
            "✅ All checks passed! Environment is ready for Phase 1.3.", "success"
        )
    else:
        failures = len(checks) - success_count
        print_status(f"❌ {failures} check(s) failed.", "error")
        print_guidance("Please address the errors above and run the script again.")
    print_separator()


if __name__ == "__main__":
    main()
