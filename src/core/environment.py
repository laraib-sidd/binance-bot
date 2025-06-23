"""
Helios Trading Bot - Environment Validation and Management

This module provides comprehensive environment validation, detection, and
management for the Helios trading bot. It ensures the system is properly
configured for development, testnet, or production use.

Features:
- Environment detection and validation
- System requirement checks
- API connectivity validation
- Security environment verification
- Development tool validation
"""

from dataclasses import dataclass, field
from datetime import datetime
import logging
import os
from pathlib import Path
import platform
import sys
from typing import Dict, List, Optional, Tuple

import pkg_resources

from .config import TradingConfig, config_manager, get_config

# Configure logging for this module
logger = logging.getLogger(__name__)


@dataclass
class SystemInfo:
    """System information and validation results."""

    # System Details
    python_version: str = field(default="")
    platform_system: str = field(default="")
    platform_release: str = field(default="")
    platform_machine: str = field(default="")

    # Directory Validation
    project_root: str = field(default="")
    data_directory_exists: bool = field(default=False)
    logs_directory_exists: bool = field(default=False)

    # Package Validation
    required_packages_installed: Dict[str, str] = field(default_factory=dict)
    missing_packages: List[str] = field(default_factory=list)

    # Environment Validation
    environment_valid: bool = field(default=False)
    api_credentials_valid: bool = field(default=False)

    # Validation Results
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)

    # Performance Info
    memory_available_gb: float = field(default=0.0)
    disk_space_available_gb: float = field(default=0.0)

    def is_valid(self) -> bool:
        """Check if environment is completely valid."""
        return (
            self.environment_valid
            and self.api_credentials_valid
            and not self.validation_errors
            and len(self.missing_packages) == 0
        )


class EnvironmentValidator:
    """
    Validates and manages the trading bot environment.

    This class performs comprehensive validation of the system environment,
    including Python version, required packages, API credentials, and
    system resources.
    """

    # Required Python version
    MIN_PYTHON_VERSION = (3, 9, 0)

    # Required packages and minimum versions
    REQUIRED_PACKAGES = {
        "python-binance": "1.0.0",
        "pandas": "1.5.0",
        "numpy": "1.21.0",
        "requests": "2.25.0",
        "aiohttp": "3.8.0",
        "python-dotenv": "0.19.0",
        "ta": "0.10.0",  # Technical analysis library
        "matplotlib": "3.5.0",  # For plotting
        "python-telegram-bot": "13.0.0",  # For notifications
    }

    # Required directories
    REQUIRED_DIRECTORIES = [
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
    ]

    def __init__(self):
        self.system_info = SystemInfo()
        self._validation_completed = False

    def validate_environment(
        self, config: Optional[TradingConfig] = None
    ) -> SystemInfo:
        """
        Perform comprehensive environment validation.

        Args:
            config: Trading configuration (optional)

        Returns:
            SystemInfo: Validation results
        """
        logger.info("Starting comprehensive environment validation")

        # Get configuration if not provided
        if config is None:
            try:
                config = get_config()
            except RuntimeError:
                logger.warning(
                    "No configuration loaded, proceeding with basic validation"
                )

        # Reset validation state
        self.system_info = SystemInfo()

        # Perform validation steps
        self._validate_python_version()
        self._validate_system_info()
        self._validate_directory_structure()
        self._validate_required_packages()
        self._validate_system_resources()

        if config:
            self._validate_configuration(config)
            self._validate_api_credentials(config)

        # Final validation
        self._perform_final_validation()

        self._validation_completed = True
        logger.info(
            f"Environment validation completed. Valid: {self.system_info.is_valid()}"
        )
        return self.system_info

    def _validate_python_version(self) -> None:
        """Validate Python version meets requirements."""
        current_version = sys.version_info[:3]
        self.system_info.python_version = (
            f"{current_version[0]}.{current_version[1]}.{current_version[2]}"
        )

        if current_version < self.MIN_PYTHON_VERSION:
            error_msg = (
                f"Python {self.MIN_PYTHON_VERSION[0]}.{self.MIN_PYTHON_VERSION[1]}+ required, "
                f"but {self.system_info.python_version} found"
            )
            self.system_info.validation_errors.append(error_msg)
            logger.error(error_msg)
        else:
            logger.info(
                f"✅ Python version {self.system_info.python_version} is compatible"
            )

    def _validate_system_info(self) -> None:
        """Gather and validate system information."""
        self.system_info.platform_system = platform.system()
        self.system_info.platform_release = platform.release()
        self.system_info.platform_machine = platform.machine()

        # Get project root
        current_dir = Path.cwd()
        if (current_dir / "src" / "core").exists():
            self.system_info.project_root = str(current_dir)
        elif (current_dir.parent / "src" / "core").exists():
            self.system_info.project_root = str(current_dir.parent)
        else:
            self.system_info.validation_errors.append(
                "Cannot determine project root directory (src/core not found)"
            )

        logger.info(
            f"✅ System: {self.system_info.platform_system} {self.system_info.platform_release}"
        )
        logger.info(f"✅ Project root: {self.system_info.project_root}")

    def _validate_directory_structure(self) -> None:
        """Validate required directory structure exists."""
        project_root = (
            Path(self.system_info.project_root)
            if self.system_info.project_root
            else Path.cwd()
        )

        missing_dirs = []
        for dir_path in self.REQUIRED_DIRECTORIES:
            full_path = project_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
            else:
                logger.debug(f"✅ Directory exists: {dir_path}")

        if missing_dirs:
            self.system_info.validation_warnings.extend(
                [f"Directory missing: {dir_path}" for dir_path in missing_dirs]
            )
            logger.warning(f"Missing directories: {missing_dirs}")

        # Check specific important directories
        data_dir = project_root / "local" / "data"
        self.system_info.data_directory_exists = data_dir.exists()

        logs_dir = project_root / "local" / "logs"
        self.system_info.logs_directory_exists = logs_dir.exists()

        if not self.system_info.data_directory_exists:
            logger.warning("Data directory will be created automatically")

        if not self.system_info.logs_directory_exists:
            logger.warning("Logs directory will be created automatically")

    def _validate_required_packages(self) -> None:
        """Validate required Python packages are installed."""
        logger.info("Validating required Python packages")

        for package_name, _min_version in self.REQUIRED_PACKAGES.items():
            try:
                installed_version = pkg_resources.get_distribution(package_name).version
                self.system_info.required_packages_installed[package_name] = (
                    installed_version
                )
                logger.debug(f"✅ {package_name} {installed_version} installed")
            except pkg_resources.DistributionNotFound:
                self.system_info.missing_packages.append(package_name)
                logger.warning(f"❌ Missing package: {package_name}")

        if self.system_info.missing_packages:
            self.system_info.validation_errors.append(
                f"Missing required packages: {', '.join(self.system_info.missing_packages)}"
            )

    def _validate_system_resources(self) -> None:
        """Validate system resources (memory, disk space)."""
        try:
            # Memory validation (basic)
            if (
                hasattr(os, "sysconf")
                and os.sysconf("SC_PAGE_SIZE")
                and os.sysconf("SC_PHYS_PAGES")
            ):
                memory_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
                self.system_info.memory_available_gb = memory_bytes / (1024**3)

            # Disk space validation
            if self.system_info.project_root:
                stat = os.statvfs(self.system_info.project_root)
                self.system_info.disk_space_available_gb = (
                    stat.f_bavail * stat.f_frsize
                ) / (1024**3)

            # Validate minimum requirements
            if (
                self.system_info.memory_available_gb > 0
                and self.system_info.memory_available_gb < 2.0
            ):
                self.system_info.validation_warnings.append(
                    f"Low memory: {self.system_info.memory_available_gb:.1f}GB (recommend 4GB+)"
                )

            if (
                self.system_info.disk_space_available_gb > 0
                and self.system_info.disk_space_available_gb < 1.0
            ):
                self.system_info.validation_warnings.append(
                    f"Low disk space: {self.system_info.disk_space_available_gb:.1f}GB (recommend 5GB+)"
                )

        except Exception as e:
            logger.debug(f"Could not validate system resources: {e}")

    def _validate_configuration(self, config: TradingConfig) -> None:
        """Validate trading configuration."""
        try:
            # Configuration is already validated in its __post_init__
            self.system_info.environment_valid = True
            logger.info(f"✅ Configuration valid for environment: {config.environment}")
        except Exception as e:
            self.system_info.validation_errors.append(
                f"Configuration validation failed: {e}"
            )
            logger.error(f"❌ Configuration validation failed: {e}")

    def _validate_api_credentials(self, config: TradingConfig) -> None:
        """Validate API credentials format."""
        self.system_info.api_credentials_valid = (
            config_manager.validate_api_credentials()
        )

        if self.system_info.api_credentials_valid:
            logger.info("✅ API credentials format appears valid")
        else:
            self.system_info.validation_errors.append(
                "API credentials are missing or invalid"
            )
            logger.error("❌ API credentials validation failed")

    def _perform_final_validation(self) -> None:
        """Perform final validation checks."""
        # Check critical errors
        critical_errors = [
            error
            for error in self.system_info.validation_errors
            if any(
                keyword in error.lower()
                for keyword in ["python", "api", "configuration"]
            )
        ]

        if critical_errors:
            logger.error(f"Critical validation errors found: {len(critical_errors)}")

        # Summary
        total_errors = len(self.system_info.validation_errors)
        total_warnings = len(self.system_info.validation_warnings)

        if total_errors == 0 and total_warnings == 0:
            logger.info("🎉 Environment validation passed with no issues!")
        elif total_errors == 0:
            logger.info(
                f"✅ Environment validation passed with {total_warnings} warnings"
            )
        else:
            logger.error(
                f"❌ Environment validation failed with {total_errors} errors and {total_warnings} warnings"
            )

    def create_missing_directories(self) -> List[str]:
        """
        Create missing required directories.

        Returns:
            List[str]: List of directories that were created
        """
        if not self.system_info.project_root:
            return []

        project_root = Path(self.system_info.project_root)
        created_dirs = []

        for dir_path in self.REQUIRED_DIRECTORIES:
            full_path = project_root / dir_path
            if not full_path.exists():
                try:
                    full_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(dir_path)
                    logger.info(f"✅ Created directory: {dir_path}")
                except Exception as e:
                    logger.error(f"❌ Failed to create directory {dir_path}: {e}")

        return created_dirs

    def generate_validation_report(self) -> str:
        """
        Generate a comprehensive validation report.

        Returns:
            str: Formatted validation report
        """
        if not self._validation_completed:
            return "Environment validation not completed. Run validate_environment() first."

        report = []
        report.append("=" * 60)
        report.append("HELIOS TRADING BOT - ENVIRONMENT VALIDATION REPORT")
        report.append("=" * 60)
        report.append(
            f"Validation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report.append(
            f"Overall Status: {'✅ VALID' if self.system_info.is_valid() else '❌ INVALID'}"
        )
        report.append("")

        # System Information
        report.append("SYSTEM INFORMATION:")
        report.append(f"  Python Version: {self.system_info.python_version}")
        report.append(
            f"  Platform: {self.system_info.platform_system} {self.system_info.platform_release}"
        )
        report.append(f"  Architecture: {self.system_info.platform_machine}")
        report.append(f"  Project Root: {self.system_info.project_root}")
        if self.system_info.memory_available_gb > 0:
            report.append(f"  Memory: {self.system_info.memory_available_gb:.1f} GB")
        if self.system_info.disk_space_available_gb > 0:
            report.append(
                f"  Disk Space: {self.system_info.disk_space_available_gb:.1f} GB"
            )
        report.append("")

        # Package Information
        report.append("PYTHON PACKAGES:")
        for package, version in self.system_info.required_packages_installed.items():
            report.append(f"  ✅ {package}: {version}")
        for package in self.system_info.missing_packages:
            report.append(f"  ❌ {package}: NOT INSTALLED")
        report.append("")

        # Configuration Status
        report.append("CONFIGURATION:")
        report.append(
            f"  Environment Valid: {'✅' if self.system_info.environment_valid else '❌'}"
        )
        report.append(
            f"  API Credentials: {'✅' if self.system_info.api_credentials_valid else '❌'}"
        )
        report.append(
            f"  Data Directory: {'✅' if self.system_info.data_directory_exists else '⚠️'}"
        )
        report.append(
            f"  Logs Directory: {'✅' if self.system_info.logs_directory_exists else '⚠️'}"
        )
        report.append("")

        # Errors and Warnings
        if self.system_info.validation_errors:
            report.append("ERRORS:")
            for error in self.system_info.validation_errors:
                report.append(f"  ❌ {error}")
            report.append("")

        if self.system_info.validation_warnings:
            report.append("WARNINGS:")
            for warning in self.system_info.validation_warnings:
                report.append(f"  ⚠️ {warning}")
            report.append("")

        report.append("=" * 60)

        return "\n".join(report)

    def save_validation_report(self, filepath: str) -> None:
        """Save validation report to file."""
        report = self.generate_validation_report()

        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            f.write(report)

        logger.info(f"Validation report saved to {filepath}")


# Global environment validator instance
environment_validator = EnvironmentValidator()


def validate_environment(config: Optional[TradingConfig] = None) -> SystemInfo:
    """
    Validate the current environment.

    Args:
        config: Trading configuration (optional)

    Returns:
        SystemInfo: Validation results
    """
    return environment_validator.validate_environment(config)


def is_environment_valid(config: Optional[TradingConfig] = None) -> bool:
    """
    Quick check if environment is valid.

    Args:
        config: Trading configuration (optional)

    Returns:
        bool: True if environment is valid
    """
    try:
        system_info = validate_environment(config)
        return system_info.is_valid()
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        return False


def setup_development_environment() -> Tuple[bool, List[str]]:
    """
    Setup development environment by creating missing directories.

    Returns:
        Tuple[bool, List[str]]: (success, list of created directories)
    """
    try:
        created_dirs = environment_validator.create_missing_directories()
        return True, created_dirs
    except Exception as e:
        logger.error(f"Failed to setup development environment: {e}")
        return False, []


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)

    print("🔍 Validating Helios Trading Bot Environment...")
    print()

    try:
        system_info = validate_environment()
        print(environment_validator.generate_validation_report())

        if not system_info.is_valid():
            print("\n🛠️  Setting up development environment...")
            success, created_dirs = setup_development_environment()
            if success and created_dirs:
                print(f"✅ Created directories: {', '.join(created_dirs)}")

    except Exception as e:
        print(f"❌ Environment validation failed: {e}")
