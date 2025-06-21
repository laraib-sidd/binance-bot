#!/usr/bin/env python3
"""
Helios Trading Bot - Environment Testing Script

This script performs comprehensive validation of the Helios trading bot
environment, checking all dependencies, configurations, and system requirements.

Run this script to verify your environment is properly set up before starting
development or trading operations.

Usage:
    python test_environment.py
    python test_environment.py --verbose
    python test_environment.py --save-report
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path for imports - go up one level since we're in scripts/
project_root = Path(__file__).parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

try:
    from src.core.config import load_configuration, TradingConfig
    from src.core.environment import validate_environment, setup_development_environment, environment_validator
except ImportError as e:
    print(f"❌ Critical Error: Cannot import core modules: {e}")
    print("This suggests the project structure is not properly set up.")
    print("Please ensure you're running this script from the project root directory.")
    sys.exit(1)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory if it doesn't exist
    logs_dir = project_root / "local" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                logs_dir / f"environment_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
        ]
    )


def print_header():
    """Print test header."""
    print("=" * 70)
    print("🚀 HELIOS TRADING BOT - ENVIRONMENT VALIDATION")
    print("=" * 70)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project Root: {project_root}")
    print("=" * 70)
    print()


def test_basic_imports():
    """Test basic Python imports."""
    print("🔍 Testing Basic Python Imports...")
    
    required_modules = [
        "os", "sys", "json", "logging", "datetime", "pathlib",
        "decimal", "typing", "dataclasses"
    ]
    
    failed_imports = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"  ⚠️  Failed imports: {', '.join(failed_imports)}")
        return False
    
    print("  🎉 All basic imports successful!")
    return True


def test_project_structure():
    """Test project directory structure."""
    print("\n🏗️  Testing Project Structure...")
    
    required_files = [
        "src/__init__.py",
        "src/core/__init__.py",
        "src/core/config.py",
        "src/core/environment.py",
        "pyproject.toml",
        "README.md"
    ]
    
    required_dirs = [
        "src", "src/core", "src/api", "src/data", "src/strategies",
        "src/risk", "src/backtest", "src/utils", "tests", "docs", "local"
    ]
    
    missing_files = []
    missing_dirs = []
    
    # Check files
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            missing_files.append(file_path)
    
    # Check directories
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/")
            missing_dirs.append(dir_path)
    
    if missing_files or missing_dirs:
        print(f"  ⚠️  Missing files: {missing_files}")
        print(f"  ⚠️  Missing directories: {missing_dirs}")
        
        # Offer to create missing directories
        if missing_dirs:
            print("\n🛠️  Creating missing directories...")
            success, created_dirs = setup_development_environment()
            if success:
                print(f"  ✅ Created: {', '.join(created_dirs)}")
            else:
                print("  ❌ Failed to create directories")
        
        return len(missing_files) == 0  # Only fail if files are missing
    
    print("  🎉 Project structure is complete!")
    return True


def test_configuration_loading():
    """Test configuration loading."""
    print("\n⚙️  Testing Configuration Loading...")
    
    try:
        # Test loading from .env file or environment variables
        print("  Testing configuration loading (.env file or environment variables)...")
        config = load_configuration()
        print(f"  ✅ Configuration loaded for environment: {config.environment}")
        print(f"  ✅ Testnet mode: {config.binance_testnet}")
        print(f"  ✅ Trading pairs: {len(config.default_trading_pairs)} configured")
        
        # Test configuration validation
        if config.binance_api_key and config.binance_api_secret:
            print("  ✅ API credentials configured")
        else:
            print("  ⚠️  API credentials not configured")
            print("     💡 Create .env file with BINANCE_API_KEY and BINANCE_API_SECRET")
            print("     💡 Or copy .env.example to .env and edit it")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration loading failed: {e}")
        print("  💡 Solution: Create .env file with your API credentials")
        print("     cp .env.example .env")
        print("     # Then edit .env with your actual API keys")
        return False


def test_environment_validation():
    """Test comprehensive environment validation."""
    print("\n🔍 Testing Environment Validation...")
    
    try:
        # Run full environment validation
        system_info = validate_environment()
        
        # Display key results
        print(f"  Python Version: {system_info.python_version}")
        print(f"  Platform: {system_info.platform_system} {system_info.platform_release}")
        print(f"  Project Root: {system_info.project_root}")
        
        # Package validation
        installed_count = len(system_info.required_packages_installed)
        missing_count = len(system_info.missing_packages)
        print(f"  Packages: {installed_count} installed, {missing_count} missing")
        
        if system_info.missing_packages:
            print(f"  ⚠️  Missing packages: {', '.join(system_info.missing_packages[:5])}")
            if len(system_info.missing_packages) > 5:
                print(f"      ... and {len(system_info.missing_packages) - 5} more")
        
        # Environment status
        if system_info.environment_valid:
            print("  ✅ Environment configuration valid")
        else:
            print("  ❌ Environment configuration invalid")
        
        if system_info.api_credentials_valid:
            print("  ✅ API credentials valid")
        else:
            print("  ⚠️  API credentials not configured or invalid")
        
        # Overall status
        if system_info.is_valid():
            print("  🎉 Environment validation passed!")
            return True
        else:
            print("  ⚠️  Environment validation completed with issues")
            if system_info.validation_errors:
                print("  Errors:")
                for error in system_info.validation_errors[:3]:
                    print(f"    - {error}")
            return False
    
    except Exception as e:
        print(f"  ❌ Environment validation failed: {e}")
        return False


def test_api_connectivity():
    """Test basic API connectivity (if credentials are available)."""
    print("\n🌐 Testing API Connectivity...")
    
    try:
        config = load_configuration()
        
        if not config.binance_api_key or not config.binance_api_secret:
            print("  ⚠️  Skipping API test - credentials not configured in .env file")
            print("     💡 Add your API keys to .env file to test connectivity")
            return True
        
        # Basic credential format validation
        if len(config.binance_api_key) < 32 or len(config.binance_api_secret) < 32:
            print("  ❌ API credentials appear to be invalid (too short)")
            print("     💡 Check your .env file for correct API key format")
            return False
        
        print("  ✅ API credentials format appears valid")
        print("  💡 Full API connectivity will be tested in Phase 1.2")
        return True
        
    except Exception as e:
        print(f"  ❌ API connectivity test failed: {e}")
        print("  💡 Check your .env file configuration")
        return False


def create_sample_env_file():
    """Create a sample .env file if it doesn't exist."""
    env_file = project_root / ".env.example"
    
    if env_file.exists():
        return
    
    print("\n📄 Creating sample .env file...")
    
    sample_env_content = '''# Helios Trading Bot Environment Configuration
# Copy this file to .env and fill in your actual values

# Binance API Configuration
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BINANCE_TESTNET=true

# Environment Settings
TRADING_ENVIRONMENT=development
LOG_LEVEL=INFO
DATA_DIRECTORY=local/data

# Optional: Override default trading parameters
# MAX_POSITION_SIZE_USD=100.00
# MAX_DAILY_LOSS_USD=50.00
# GRID_LEVELS=10
'''
    
    try:
        with open(env_file, 'w') as f:
            f.write(sample_env_content)
        print(f"  ✅ Created {env_file}")
        print("  💡 Copy this file to .env and add your API credentials")
    except Exception as e:
        print(f"  ❌ Failed to create sample .env file: {e}")


def run_all_tests(verbose: bool = False, save_report: bool = False) -> bool:
    """Run all environment tests."""
    setup_logging(verbose)
    print_header()
    
    test_results = []
    
    # Run all tests
    test_results.append(("Basic Imports", test_basic_imports()))
    test_results.append(("Project Structure", test_project_structure()))
    test_results.append(("Configuration Loading", test_configuration_loading()))
    test_results.append(("Environment Validation", test_environment_validation()))
    test_results.append(("API Connectivity", test_api_connectivity()))
    
    # Create sample files
    create_sample_env_file()
    
    # Display results summary
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed_tests = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:<25} {status}")
        if result:
            passed_tests += 1
    
    total_tests = len(test_results)
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    # Overall status
    all_passed = passed_tests == total_tests
    if all_passed:
        print("\n🎉 ENVIRONMENT READY! All tests passed.")
        print("You can now proceed with Phase 1 development.")
    else:
        print(f"\n⚠️  ENVIRONMENT NEEDS ATTENTION: {total_tests - passed_tests} test(s) failed.")
        print("Please address the issues above before proceeding.")
    
    # Generate detailed report if requested
    if save_report:
        try:
            report = environment_validator.generate_validation_report()
            report_file = project_root / "local" / "logs" / f"environment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            report_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_file, 'w') as f:
                f.write("HELIOS TRADING BOT - COMPREHENSIVE TEST REPORT\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Project Root: {project_root}\n\n")
                
                f.write("TEST RESULTS:\n")
                for test_name, result in test_results:
                    f.write(f"  {test_name}: {'PASS' if result else 'FAIL'}\n")
                f.write(f"\nOverall: {passed_tests}/{total_tests} tests passed\n\n")
                
                f.write("DETAILED ENVIRONMENT VALIDATION:\n")
                f.write("=" * 60 + "\n")
                f.write(report)
            
            print(f"\n📄 Detailed report saved to: {report_file}")
            
        except Exception as e:
            print(f"\n⚠️  Could not save detailed report: {e}")
    
    print("\n" + "=" * 70)
    
    return all_passed


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test Helios Trading Bot environment setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_environment.py              # Run basic tests
  python test_environment.py --verbose    # Run with detailed output
  python test_environment.py --save-report # Save detailed report to file
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with detailed logging"
    )
    
    parser.add_argument(
        "--save-report", "-r",
        action="store_true",
        help="Save detailed validation report to file"
    )
    
    args = parser.parse_args()
    
    try:
        success = run_all_tests(verbose=args.verbose, save_report=args.save_report)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 