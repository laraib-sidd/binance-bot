# Environment Setup Guide

## Overview
This guide walks through setting up the complete development environment for the Helios Trading Bot project.

## Prerequisites

### System Requirements
- **Python**: 3.9 or higher
- **Git**: Latest version
- **Operating System**: macOS, Linux, or Windows with WSL
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **Storage**: At least 5GB free space

### Required Accounts
- **Binance Account**: For API access (both testnet and live)
- **GitHub Account**: For repository access and collaboration
- **Optional**: Coinbase account for future multi-exchange support

## Step-by-Step Setup

### 1. Clone and Navigate to Project
```bash
# Clone the repository
git clone https://github.com/laraib-sidd/binance-bot.git
cd binance-bot

# Verify project structure
ls -la
```

### 2. Python Environment Setup
```bash
# Create virtual environment
python3.9 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Verify Python version
python --version  # Should show 3.9+
```

### 3. Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install all project dependencies
pip install -r requirements.txt

# Verify critical packages
python -c "import pandas, numpy, pandas_ta, aiohttp; print('Core packages installed successfully')"
```

### 4. API Keys and Configuration

#### 4.1 Binance API Setup
1. **Create Binance Testnet Account**:
   - Go to https://testnet.binance.vision/
   - Create account and verify email
   - Generate API key and secret

2. **Create Environment File**:
```bash
# Copy example configuration
cp config.example.py config.py

# Create environment file
touch .env
```

3. **Configure Environment Variables**:
```bash
# Edit .env file with your API credentials
cat > .env << EOF
# Binance API Configuration
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
USE_TESTNET=True

# Trading Environment
TRADING_ENVIRONMENT=TESTNET

# Optional: Telegram Notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
EOF
```

#### 4.2 Security Verification
```bash
# Verify .env is in .gitignore
grep -q "^\.env$" .gitignore && echo "✅ .env properly ignored" || echo "❌ Add .env to .gitignore"

# Verify config.py is in .gitignore  
grep -q "^config\.py$" .gitignore && echo "✅ config.py properly ignored" || echo "❌ Add config.py to .gitignore"
```

### 5. Development Tools Setup

#### 5.1 Code Quality Tools
```bash
# Install development tools globally (optional)
pip install black flake8 mypy pytest

# Verify code formatting
black --check src/
flake8 src/
```

#### 5.2 Git Configuration
```bash
# Set up git hooks (optional but recommended)
# Pre-commit hook to run tests
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "Running pre-commit checks..."
python -m pytest tests/ -x
python -m black --check src/
python -m flake8 src/
EOF

chmod +x .git/hooks/pre-commit
```

### 6. Directory Structure Verification
```bash
# Verify all required directories exist
for dir in src tests local docs; do
  if [ -d "$dir" ]; then
    echo "✅ $dir directory exists"
  else
    echo "❌ $dir directory missing"
  fi
done

# Create any missing local subdirectories
mkdir -p local/{docs,logs,data,configs,temp}
```

### 7. Initial Testing

#### 7.1 Basic Environment Test
```python
# Create and run test_environment.py
cat > test_environment.py << 'EOF'
#!/usr/bin/env python3
"""
Environment setup verification script
"""
import sys
import os
from pathlib import Path

def test_python_version():
    """Test Python version compatibility"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requires 3.9+")
        return False

def test_required_packages():
    """Test that required packages are installed"""
    required_packages = [
        'pandas', 'numpy', 'pandas_ta', 'aiohttp', 
        'python-binance', 'sqlalchemy', 'pytest'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} - Installed")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def test_environment_file():
    """Test environment configuration"""
    env_file = Path('.env')
    if env_file.exists():
        print("✅ .env file exists")
        return True
    else:
        print("❌ .env file missing - create with API credentials")
        return False

def test_project_structure():
    """Test project directory structure"""
    required_dirs = ['src', 'tests', 'local', 'docs']
    all_exist = True
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"❌ {dir_name}/ directory missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all environment tests"""
    print("🔍 Helios Trading Bot - Environment Setup Verification\n")
    
    tests = [
        ("Python Version", test_python_version),
        ("Required Packages", test_required_packages),
        ("Environment File", test_environment_file),
        ("Project Structure", test_project_structure)
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}:")
        if not test_func():
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 Environment setup complete! Ready for development.")
    else:
        print("⚠️ Environment setup incomplete. Please fix the issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

# Run the environment test
python test_environment.py
```

#### 7.2 API Connectivity Test (After API keys configured)
```python
# Create api_test.py for later use
cat > api_test.py << 'EOF'
#!/usr/bin/env python3
"""
Basic API connectivity test for Binance testnet
Run this after configuring API keys
"""
import os
from dotenv import load_dotenv

def test_api_connection():
    """Test basic API connection"""
    load_dotenv()
    
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ API credentials not found in environment")
        return False
    
    try:
        from binance.client import Client
        
        # Create testnet client
        client = Client(api_key, api_secret, testnet=True)
        
        # Test connection
        account_info = client.get_account()
        print(f"✅ API connection successful")
        print(f"📊 Account status: {account_info.get('accountType', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

if __name__ == "__main__":
    test_api_connection()
EOF
```

### 8. IDE Setup (Optional)

#### 8.1 VS Code Configuration
```json
// Create .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "files.exclude": {
        "**/__pycache__": true,
        "**/.*": false,
        "local/": true
    }
}
```

#### 8.2 Recommended VS Code Extensions
- Python
- Python Docstring Generator
- GitLens
- Black Formatter
- Pylance

## Environment Verification Checklist

Before starting development, verify:

- [ ] Python 3.9+ installed and activated in virtual environment
- [ ] All requirements.txt packages installed successfully
- [ ] .env file created with Binance testnet API credentials
- [ ] config.py file configured (copy from config.example.py)
- [ ] Project directory structure complete
- [ ] Git hooks configured (optional)
- [ ] Code quality tools working (black, flake8, pytest)
- [ ] Environment test script passes
- [ ] API connectivity test passes (after API keys configured)

## Troubleshooting

### Common Issues

#### 1. Python Version Issues
```bash
# Install specific Python version using pyenv
pyenv install 3.9.18
pyenv local 3.9.18
```

#### 2. Package Installation Failures
```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Install packages one by one to identify issues
pip install pandas numpy python-binance
```

#### 3. API Connection Issues
- Verify API keys are correct
- Ensure testnet is enabled
- Check network connectivity
- Verify Binance testnet is accessible

#### 4. Permission Issues (macOS/Linux)
```bash
# Fix permission issues
chmod +x test_environment.py api_test.py
```

## Security Reminders

⚠️ **CRITICAL SECURITY NOTES**:
- **Never commit .env or config.py** to version control
- **Use testnet credentials only** for development
- **Rotate API keys** if accidentally exposed
- **Keep local/ directory private** (already in .gitignore)

## Next Steps

After completing environment setup:
1. Run `python test_environment.py` to verify setup
2. Configure API credentials in .env file
3. Run `python api_test.py` to test API connectivity
4. You're ready for Phase 1 development!

## Support

If you encounter issues:
1. Check this guide's troubleshooting section
2. Verify all prerequisites are met
3. Review error messages carefully
4. Create an issue with detailed error information

---

**Environment setup is the foundation of successful development. Take time to get it right!** 