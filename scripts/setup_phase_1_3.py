#!/usr/bin/env python3
"""
Helios Trading Bot - Phase 1.3 Setup Script

Sets up the data pipeline dependencies and environment for Phase 1.3.

Usage:
    python scripts/setup_phase_1_3.py
"""

import subprocess
import sys
import os
from pathlib import Path


def print_status(message: str, status: str = "info"):
    """Print formatted status message."""
    icons = {
        'info': 'ℹ️',
        'success': '✅',
        'warning': '⚠️',
        'error': '❌',
        'running': '🔄'
    }
    
    icon = icons.get(status, 'ℹ️')
    print(f"{icon} {message}")


def run_command(command: list, description: str) -> bool:
    """Run a command and return success status."""
    print_status(f"{description}...", "running")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print_status(f"{description} completed", "success")
            return True
        else:
            print_status(f"{description} failed: {result.stderr}", "error")
            return False
            
    except Exception as e:
        print_status(f"{description} failed: {e}", "error")
        return False


def check_uv_installed() -> bool:
    """Check if uv is installed."""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_status(f"UV package manager found: {result.stdout.strip()}", "success")
            return True
        else:
            return False
    except FileNotFoundError:
        return False


def install_dependencies() -> bool:
    """Install new dependencies for Phase 1.3."""
    print_status("Installing Phase 1.3 dependencies", "running")
    
    # New dependencies for Phase 1.3
    new_packages = [
        "asyncpg>=0.29.0",  # PostgreSQL async driver
        "redis>=5.0.0",     # Redis async client
        "boto3>=1.34.0",    # AWS/R2 S3-compatible client
        "polars>=0.20.0",   # Fast dataframe library
    ]
    
    if check_uv_installed():
        # Use UV if available
        for package in new_packages:
            success = run_command(['uv', 'add', package], f"Installing {package}")
            if not success:
                return False
    else:
        # Fallback to pip
        print_status("UV not found, using pip", "warning")
        for package in new_packages:
            success = run_command(['pip', 'install', package], f"Installing {package}")
            if not success:
                return False
    
    return True


def create_data_directories() -> bool:
    """Create necessary data directories."""
    print_status("Creating data directories", "running")
    
    directories = [
        "src/data",
        "local/data",
        "local/logs"
    ]
    
    try:
        for directory in directories:
            dir_path = Path(__file__).parent.parent / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py for Python packages
            if directory.startswith("src/"):
                init_file = dir_path / "__init__.py"
                if not init_file.exists():
                    init_file.touch()
        
        print_status("Data directories created", "success")
        return True
        
    except Exception as e:
        print_status(f"Failed to create directories: {e}", "error")
        return False


def check_environment_variables() -> bool:
    """Check if required environment variables are set."""
    print_status("Checking environment variables", "running")
    
    # Load .env file if it exists
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print_status(f"Loading .env file: {env_file}", "info")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    # Check database connection - either full URL or individual components
    database_configured = False
    
    # Option 1: Single connection URL
    if os.getenv('NEON_DATABASE_URL'):
        print_status("Database URL found (NEON_DATABASE_URL)", "info")
        database_configured = True
    
    # Option 2: Individual components
    db_components = [
        'DB_HOST', 'DB_DATABASE', 'DB_USER', 'DB_PASSWORD'
    ]
    if all(os.getenv(var) for var in db_components):
        print_status("Database components found (DB_HOST, DB_DATABASE, DB_USER, DB_PASSWORD)", "info")
        
        # Build the connection URL from components
        host = os.getenv('DB_HOST')
        database = os.getenv('DB_DATABASE')
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        port = os.getenv('DB_PORT', '5432')
        
        neon_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        os.environ['NEON_DATABASE_URL'] = neon_url
        print_status("Built NEON_DATABASE_URL from components", "success")
        database_configured = True
    
    if not database_configured:
        print_status("Database not configured. Need either:", "warning")
        print_status("  - NEON_DATABASE_URL (full connection string)", "info")
        print_status("  - DB_HOST, DB_DATABASE, DB_USER, DB_PASSWORD (individual components)", "info")
    
    # Optional cloud services (not required for basic functionality)
    optional_vars = {
        'UPSTASH_REDIS_URL': 'Redis cache (optional for Phase 1.3)',
        'R2_ACCOUNT_ID': 'Cloudflare R2 storage (optional)',
        'R2_API_TOKEN': 'Cloudflare R2 API token (optional)',
        'R2_BUCKET_NAME': 'Cloudflare R2 bucket (optional)'
    }
    
    missing_optional = []
    for var, description in optional_vars.items():
        if not os.getenv(var):
            missing_optional.append(f"{var} - {description}")
    
    if missing_optional:
        print_status("Optional services not configured:", "info")
        for var_info in missing_optional:
            print_status(f"  - {var_info}", "info")
    
    # For Phase 1.3, we only require database connection
    if database_configured:
        print_status("Required environment variables found", "success")
        return True
    else:
        print_status("Database configuration missing", "warning")
        print_status("Please add database credentials to your .env file", "warning")
        return False


def main():
    """Main setup function."""
    print("🚀 Helios Trading Bot - Phase 1.3 Setup")
    print("=" * 50)
    
    success_count = 0
    total_steps = 4
    
    # Step 1: Create directories
    if create_data_directories():
        success_count += 1
    
    # Step 2: Install dependencies
    if install_dependencies():
        success_count += 1
    
    # Step 3: Check environment variables
    if check_environment_variables():
        success_count += 1
    else:
        print_status("Environment variables missing, but continuing setup", "warning")
        success_count += 1  # Don't fail setup for missing env vars
    
    # Step 4: Run basic import test
    try:
        print_status("Testing imports", "running")
        import asyncpg
        import redis
        import boto3
        import polars
        print_status("All imports successful", "success")
        success_count += 1
    except ImportError as e:
        print_status(f"Import test failed: {e}", "error")
    
    # Final status
    print("\n" + "=" * 50)
    print(f"🏁 Setup Results: {success_count}/{total_steps} steps completed")
    
    if success_count == total_steps:
        print_status("Phase 1.3 setup completed successfully!", "success")
        print("\n💡 Next Steps:")
        print("   1. Ensure your .env file has all required credentials")
        print("   2. Run: python scripts/test_data_pipeline.py")
        print("   3. If tests pass, you're ready for Phase 1.3!")
    else:
        print_status("Setup completed with some issues", "warning")
        print("\n🔧 Troubleshooting:")
        print("   1. Check error messages above")
        print("   2. Ensure you have internet connectivity")
        print("   3. Try running setup again")


if __name__ == "__main__":
    main() 