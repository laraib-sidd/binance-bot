"""
Helios Trading Bot - Configuration System Unit Tests

This module contains comprehensive unit tests for the configuration management
system, testing various scenarios including validation, loading, and error handling.
"""

from decimal import Decimal
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import (
    ConfigurationManager,
    TradingConfig,
    config_manager,
    get_config,
    load_configuration,
    validate_configuration,
)


class TestTradingConfig:
    """Test cases for TradingConfig dataclass."""

    def test_default_configuration(self):
        """Test default configuration values."""
        # This should fail validation due to missing API keys
        with pytest.raises(ValueError, match="Configuration validation failed"):
            TradingConfig()

    def test_valid_configuration(self):
        """Test valid configuration creation."""
        config = TradingConfig(
            binance_api_key="a" * 64,  # Valid length API key
            binance_api_secret="b" * 64,  # Valid length API secret
            binance_testnet=True,
            environment="development",
        )

        assert config.binance_api_key == "a" * 64
        assert config.binance_api_secret == "b" * 64
        assert config.binance_testnet is True
        assert config.environment == "development"
        assert config.max_position_size_usd == Decimal("100.00")
        assert len(config.default_trading_pairs) == 5

    def test_api_key_validation(self):
        """Test API key validation."""
        # Test missing API key
        with pytest.raises(ValueError, match="BINANCE_API_KEY is required"):
            TradingConfig(binance_api_secret="b" * 64)

        # Test short API key
        with pytest.raises(ValueError, match="BINANCE_API_KEY appears invalid"):
            TradingConfig(binance_api_key="short", binance_api_secret="b" * 64)

        # Test missing API secret
        with pytest.raises(ValueError, match="BINANCE_API_SECRET is required"):
            TradingConfig(binance_api_key="a" * 64)

        # Test short API secret
        with pytest.raises(ValueError, match="BINANCE_API_SECRET appears invalid"):
            TradingConfig(binance_api_key="a" * 64, binance_api_secret="short")

    def test_environment_validation(self):
        """Test environment validation."""
        with pytest.raises(ValueError, match="Environment must be one of"):
            TradingConfig(
                binance_api_key="a" * 64,
                binance_api_secret="b" * 64,
                environment="invalid",
            )

    def test_risk_parameter_validation(self):
        """Test risk parameter validation."""
        # Test negative position size
        with pytest.raises(ValueError, match="max_position_size_usd must be positive"):
            TradingConfig(
                binance_api_key="a" * 64,
                binance_api_secret="b" * 64,
                max_position_size_usd=Decimal("-100.00"),
            )

        # Test invalid drawdown percentage
        with pytest.raises(
            ValueError, match="max_account_drawdown_percent must be between 0 and 100"
        ):
            TradingConfig(
                binance_api_key="a" * 64,
                binance_api_secret="b" * 64,
                max_account_drawdown_percent=Decimal("150.00"),
            )

    def test_trading_pairs_validation(self):
        """Test trading pairs validation."""
        # Test empty trading pairs
        with pytest.raises(
            ValueError, match="At least one trading pair must be specified"
        ):
            TradingConfig(
                binance_api_key="a" * 64,
                binance_api_secret="b" * 64,
                default_trading_pairs=[],
            )

        # Test invalid trading pair format
        with pytest.raises(ValueError, match="Invalid trading pair format"):
            TradingConfig(
                binance_api_key="a" * 64,
                binance_api_secret="b" * 64,
                default_trading_pairs=["BTC"],
            )

    def test_grid_trading_validation(self):
        """Test grid trading parameter validation."""
        # Test insufficient grid levels
        with pytest.raises(ValueError, match="grid_levels must be at least 2"):
            TradingConfig(
                binance_api_key="a" * 64, binance_api_secret="b" * 64, grid_levels=1
            )

        # Test invalid grid spacing
        with pytest.raises(ValueError, match="grid_spacing_percent must be positive"):
            TradingConfig(
                binance_api_key="a" * 64,
                binance_api_secret="b" * 64,
                grid_spacing_percent=Decimal("-1.0"),
            )

    def test_to_dict(self):
        """Test configuration serialization to dictionary."""
        config = TradingConfig(
            binance_api_key="a" * 64, binance_api_secret="b" * 64, environment="testnet"
        )

        config_dict = config.to_dict()

        # Check that sensitive data is excluded
        assert "binance_api_key" not in config_dict
        assert "binance_api_secret" not in config_dict

        # Check that non-sensitive data is included
        assert config_dict["environment"] == "testnet"
        assert config_dict["binance_testnet"] is True
        assert config_dict["api_keys_configured"] is True
        assert "config_loaded_at" in config_dict

    def test_save_config_summary(self):
        """Test saving configuration summary to file."""
        config = TradingConfig(binance_api_key="a" * 64, binance_api_secret="b" * 64)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            config.save_config_summary(temp_file)

            # Verify file was created and contains expected data
            assert Path(temp_file).exists()

            with open(temp_file, "r") as f:
                import json

                saved_config = json.load(f)

            assert saved_config["environment"] == "development"
            assert saved_config["api_keys_configured"] is True
            assert "binance_api_key" not in saved_config

        finally:
            # Cleanup
            if Path(temp_file).exists():
                Path(temp_file).unlink()


class TestConfigurationManager:
    """Test cases for ConfigurationManager class."""

    @pytest.fixture
    def manager(self):
        """Fixture to provide a clean ConfigurationManager instance."""
        # Reset the global manager's state before each test
        config_manager.config = None
        config_manager._env_file_path = None
        return ConfigurationManager()

    def test_load_from_environment(self, manager):
        """Test loading configuration from environment variables."""
        test_env = {
            "BINANCE_API_KEY": "a" * 64,
            "BINANCE_API_SECRET": "b" * 64,
            "BINANCE_TESTNET": "true",
            "LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, test_env, clear=False):
            config = manager.load_from_environment()
            assert config.binance_testnet is True
            assert config.log_level == "DEBUG"

    def test_load_from_env_file(self, manager):
        """Test loading configuration from a .env file."""
        env_content = "LOG_LEVEL=WARNING\n"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
            f.write(env_content)
            temp_env_file = f.name

        try:
            config = manager.load_from_env_file(temp_env_file)
            assert config.log_level == "WARNING"
        finally:
            os.unlink(temp_env_file)

    def test_api_credentials_validation(self, manager):
        """Test API credential validation logic."""
        test_env = {
            "BINANCE_API_KEY": "a" * 64,
            "BINANCE_API_SECRET": "b" * 64,
        }
        with patch.dict(os.environ, test_env, clear=False):
            manager.load_from_environment()
            assert manager.validate_api_credentials() is True

    def test_get_safe_config_summary(self, manager):
        """Test the safe config summary obfuscates sensitive data."""
        test_env = {
            "BINANCE_API_KEY": "MyApiKey123",
            "BINANCE_API_SECRET": "MyApiSecret456",
        }
        with patch.dict(os.environ, test_env, clear=False):
            manager.load_from_environment()
            summary = manager.get_safe_config_summary()
            assert "MyApiKey123" not in str(summary.values())
            assert "MyA...123" in str(summary.values())


class TestConfigurationFunctions:
    """Test cases for module-level configuration functions."""

    def setup_method(self):
        """Setup for each test method."""
        # Reset the global config manager state
        config_manager.config = None
        config_manager._env_file_path = None

    def test_load_configuration_from_env_file(self):
        """Test load_configuration function with .env file."""
        env_content = """
BINANCE_API_KEY=test_api_key_64_characters_long_abcdefghijklmnopqrstuvwxyz
BINANCE_API_SECRET=test_api_secret_64_characters_long_abcdefghijklmnopqrstuvw
        """.strip()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
            f.write(env_content)
            temp_env_file = f.name

        try:
            config = load_configuration(temp_env_file)
            assert len(config.binance_api_key) == 64
            assert len(config.binance_api_secret) == 64

        finally:
            if Path(temp_env_file).exists():
                Path(temp_env_file).unlink()

    def test_load_configuration_from_environment(self):
        """Test load_configuration function from environment variables."""
        test_env = {"BINANCE_API_KEY": "a" * 64, "BINANCE_API_SECRET": "b" * 64}

        with patch.dict(os.environ, test_env, clear=False):
            config = load_configuration("nonexistent.env")
            assert config.binance_api_key == "a" * 64

    def test_get_config_without_loading(self):
        """Test get_config function without prior loading."""
        with pytest.raises(RuntimeError, match="Configuration not loaded"):
            get_config()

    def test_get_config_after_loading(self):
        """Test get_config function after loading configuration."""
        test_env = {"BINANCE_API_KEY": "a" * 64, "BINANCE_API_SECRET": "b" * 64}

        with patch.dict(os.environ, test_env, clear=False):
            # Load configuration
            load_configuration("nonexistent.env")

            # Get configuration
            config = get_config()
            assert config.binance_api_key == "a" * 64

    def test_validate_configuration_function(self):
        """Test validate_configuration function."""
        # Test without loaded config
        assert validate_configuration() is False

        # Test with loaded config
        test_env = {"BINANCE_API_KEY": "a" * 64, "BINANCE_API_SECRET": "b" * 64}

        with patch.dict(os.environ, test_env, clear=False):
            load_configuration("nonexistent.env")
            assert validate_configuration() is True


class TestConfigurationIntegration:
    """Integration tests for configuration system."""

    def setup_method(self):
        """Setup for each test method."""
        config_manager.config = None
        config_manager._env_file_path = None

    def test_full_configuration_workflow(self):
        """Test complete configuration workflow."""
        # Create temporary .env file
        env_content = """
BINANCE_API_KEY=integration_test_api_key_64_chars_abcdefghijklmnopqrstuvwxyz
BINANCE_API_SECRET=integration_test_secret_64_chars_abcdefghijklmnopqrstuvwx
BINANCE_TESTNET=true
TRADING_ENVIRONMENT=development
LOG_LEVEL=INFO
DATA_DIRECTORY=test_data
        """.strip()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
            f.write(env_content)
            temp_env_file = f.name

        try:
            # Load configuration
            config = load_configuration(temp_env_file)

            # Validate configuration
            assert validate_configuration() is True

            # Get configuration
            retrieved_config = get_config()
            assert retrieved_config.binance_api_key.startswith("integration_test")
            assert retrieved_config.environment == "development"
            assert retrieved_config.binance_testnet is True
            assert retrieved_config.data_directory == "test_data"

            # Test configuration serialization
            config_dict = config.to_dict()
            assert config_dict["environment"] == "development"
            assert "binance_api_key" not in config_dict

            # Test saving configuration summary
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".json"
            ) as f:
                temp_json_file = f.name

            config.save_config_summary(temp_json_file)
            assert Path(temp_json_file).exists()

            # Cleanup JSON file
            Path(temp_json_file).unlink()

        finally:
            # Cleanup env file
            if Path(temp_env_file).exists():
                Path(temp_env_file).unlink()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
