#!/usr/bin/env python3
"""
Helios Trading Bot - Configuration Update Test

Tests the new individual database parameter configuration approach.
This validates that the configuration system properly loads individual
parameters and builds connection strings correctly.

Usage:
    python scripts/test_config_update.py
"""

import os
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def print_status(message: str, status: str = "info"):
    """Print formatted status message."""
    icons = {
        'info': 'ℹ️',
        'success': '✅', 
        'warning': '⚠️',
        'error': '❌',
        'test': '🧪'
    }
    
    icon = icons.get(status, 'ℹ️')
    print(f"{icon} {message}")


def test_configuration_loading():
    """Test that configuration loads with individual parameters."""
    print_status("Testing configuration loading with individual parameters", "test")
    
    # Set up test environment variables
    test_env = {
        'BINANCE_API_KEY': 'test_api_key_12345678901234567890123456789012',
        'BINANCE_API_SECRET': 'test_secret_12345678901234567890123456789012',
        'NEON_HOST': 'test-host.neon.tech',
        'NEON_DATABASE': 'test_database',
        'NEON_USERNAME': 'test_user',
        'NEON_PASSWORD': 'test_password_12345',
        'NEON_PORT': '5432',
        'NEON_SSL_MODE': 'require',
        'UPSTASH_REDIS_USERNAME': 'default',
        'UPSTASH_REDIS_HOST': 'test-redis.upstash.io',
        'UPSTASH_REDIS_PORT': '6379',
        'UPSTASH_REDIS_PASSWORD': 'testpass123',
        'R2_ACCOUNT_ID': 'test_account_id_12345678901234567890123456789012',
        'R2_API_TOKEN': 'test_api_token_12345678901234567890123456789012',
        'R2_BUCKET_NAME': 'test-bucket',
        'R2_ENDPOINT': 'https://test-account.r2.cloudflarestorage.com',
        'R2_REGION': 'auto'
    }
    
    # Store original environment
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.getenv(key)
        os.environ[key] = value
    
    try:
        # Import and test configuration
        from core.config import ConfigurationManager
        
        print_status("Loading configuration...", "info")
        config_manager = ConfigurationManager()
        config = config_manager.load_from_environment()  # Don't load .env file
        
        print_status("Configuration loaded successfully", "success")
        
        # Test PostgreSQL URL building
        postgres_url = config.get_postgresql_url()
        expected_postgres = "postgresql://test_user:test_password_12345@test-host.neon.tech:5432/test_database?sslmode=require"
        
        if postgres_url == expected_postgres:
            print_status("PostgreSQL URL building: PASS", "success")
        else:
            print_status(f"PostgreSQL URL building: FAIL", "error")
            print_status(f"Expected: {expected_postgres}", "info")
            print_status(f"Got: {postgres_url}", "info")
            return False
        
        # Test Redis URL building
        redis_url = config.get_redis_url()
        expected_redis = "redis://default:testpass123@test-redis.upstash.io:6379"
        
        if redis_url == expected_redis:
            print_status("Redis URL building: PASS", "success")
        else:
            print_status(f"Redis URL building: FAIL", "error")
            print_status(f"Expected: {expected_redis}", "info")
            print_status(f"Got: {redis_url}", "info")
            return False
        
        # Test R2 config building
        r2_config = config.get_r2_config()
        expected_r2 = {
            "account_id": "test_account_id_12345678901234567890123456789012",
            "api_token": "test_api_token_12345678901234567890123456789012",
            "bucket_name": "test-bucket",
            "endpoint": "https://test-account.r2.cloudflarestorage.com",
            "region": "auto"
        }
        
        if r2_config == expected_r2:
            print_status("R2 config building: PASS", "success")
        else:
            print_status(f"R2 config building: FAIL", "error")
            print_status(f"Expected: {expected_r2}", "info")
            print_status(f"Got: {r2_config}", "info")
            return False
        
        # Test configuration status reporting
        config_dict = config.to_dict()
        required_status_keys = [
            'database_configured', 'redis_configured', 'r2_configured'
        ]
        
        for key in required_status_keys:
            if key not in config_dict:
                print_status(f"Missing status key: {key}", "error")
                return False
            if not config_dict[key]:
                print_status(f"Status key {key} should be True", "error")
                return False
        
        print_status("Configuration status reporting: PASS", "success")
        print_status("All configuration tests passed!", "success")
        return True
        
    except Exception as e:
        print_status(f"Configuration test failed: {e}", "error")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Restore original environment
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


def test_connection_managers():
    """Test that connection managers work with new config."""
    print_status("Testing connection managers with new config", "test")
    
    # Import without relative imports by adding the path
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "data"))
        
        import connection_managers
        print_status("Connection manager import: PASS", "success")
        
        # Verify the class structure exists
        if hasattr(connection_managers, 'ConnectionManager'):
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