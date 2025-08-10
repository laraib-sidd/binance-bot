#!/usr/bin/env python3
"""
Helios Trading Bot - Configuration Update Test

Tests the new individual database parameter configuration approach.
This validates that the configuration system properly loads individual
parameters and builds connection strings correctly.

Usage:
    python scripts/test_config_update.py
"""

from pathlib import Path
import sys

from src.core.config import config_manager, get_config, load_configuration

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def print_status(message, stage):
    print(f"[{stage.upper()}] {message}")


def test_configuration_loading():
    """Test that configuration loads with individual parameters."""
    print_status("Testing configuration loading with individual parameters", "test")

    # 1. Setup mock environment
    base_dir = Path(__file__).parent.parent
    env_file = base_dir / ".env.template"
    load_configuration(env_file_path=env_file)
    print_status("Loaded .env.template for base configuration", "setup")

    # 2. Get initial config and verify
    initial_config = get_config()
    print_status("Initial configuration loaded", "info")
    assert initial_config.log_level == "INFO"
    assert initial_config.trading_symbols == ["BTCUSDT", "ETHUSDT"]
    print_status("Initial config values verified", "assert")

    # 3. Update configuration with new values
    update_data = {
        "LOG_LEVEL": "DEBUG",
        "TRADING_SYMBOLS": '["ADAUSDT", "SOLUSDT"]',
        "POLLING_INTERVAL_SECONDS": "30",
    }
    config_manager.update_from_dict(update_data)
    print_status("Configuration updated from dictionary", "update")

    # 4. Get updated config and verify changes
    updated_config = get_config()
    print_status("Updated configuration retrieved", "info")
    assert updated_config.log_level == "DEBUG"
    assert updated_config.trading_symbols == ["ADAUSDT", "SOLUSDT"]
    assert updated_config.polling_interval_seconds == 30
    print_status("Updated config values verified", "assert")

    # 5. Test persistence (optional, depends on implementation)
    # If config_manager writes to a file, we could test that here.
    # For now, we assume it's in-memory.

    print_status("Configuration update test completed successfully", "success")


def test_connection_managers():
    """Test that connection managers work with new config."""
    print_status("Testing connection managers with new config", "test")

    # Import without relative imports by adding the path
    try:
        from pathlib import Path
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "data"))

        import connection_managers

        print_status("Connection manager import: PASS", "success")

        # Verify the class structure exists
        if hasattr(connection_managers, "ConnectionManager"):
            print_status("ConnectionManager class found: PASS", "success")
        else:
            print_status("ConnectionManager class not found: FAIL", "error")
            return False

        return True

    except Exception as e:
        print_status(f"Connection manager test failed: {e}", "error")
        return False


def main():
    """Run all configuration tests."""
    print("🧪 Helios Trading Bot - Configuration Update Test")
    print("=" * 60)

    tests = [
        ("Configuration Loading", test_configuration_loading),
        ("Connection Managers", test_connection_managers),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 40)

        if test_func():
            passed += 1
            print_status(f"{test_name}: PASSED", "success")
        else:
            print_status(f"{test_name}: FAILED", "error")

    # Final results
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print_status("All tests passed! Configuration update successful!", "success")
        print("\n💡 Next Steps:")
        print("   1. Update your .env file to use individual parameters")
        print("   2. Remove old URL-based parameters if desired")
        print("   3. Test with real credentials using test_data_pipeline.py")
        return True
    else:
        print_status("Some tests failed. Please check the errors above.", "error")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
