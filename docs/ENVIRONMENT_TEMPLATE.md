# Environment Variables Template

## 📝 **Create .env File**

Copy the following template to create your `.env` file in the project root:

```env
# Helios Trading Bot - Environment Variables
# Copy this to .env and fill in your actual credentials

# =====================================
# Binance API Credentials (Testnet)
# =====================================
BINANCE_API_KEY=your_binance_testnet_api_key
BINANCE_SECRET_KEY=your_binance_testnet_secret_key
BINANCE_TESTNET=True

# =====================================
# Neon PostgreSQL (Singapore)
# =====================================
NEON_DATABASE_URL=postgresql://helios_trading_owner:your_password@ep-your-endpoint.ap-southeast-1.aws.neon.tech/helios_trading?sslmode=require

# =====================================
# Upstash Redis (Singapore)  
# =====================================
UPSTASH_REDIS_URL=redis://default:your_password@your-redis-host.upstash.io:6379
UPSTASH_REDIS_HOST=your-redis-host.upstash.io
UPSTASH_REDIS_PORT=6379
UPSTASH_REDIS_PASSWORD=your_upstash_password

# =====================================
# Cloudflare R2 (Global)
# =====================================
R2_ACCOUNT_ID=your_account_id_from_r2_dashboard
R2_API_TOKEN=your_cloudflare_r2_api_token
R2_BUCKET_NAME=helios-trading-datalake
R2_ENDPOINT=https://your_account_id.r2.cloudflarestorage.com
R2_REGION=auto

# =====================================
# Trading Bot Configuration
# =====================================
ENVIRONMENT=development
LOG_LEVEL=INFO
TRADING_MODE=paper
MAX_POSITION_SIZE=100.00
RISK_PERCENTAGE=1.0

# =====================================
# Data Pipeline Settings
# =====================================
DATA_DIRECTORY=local/data
CACHE_TTL_SECONDS=300
BATCH_SIZE=1000
POLLING_INTERVAL_SECONDS=60
```

## 🔒 **Security Notes**

1. **Never commit .env to git** - it's already in .gitignore
2. **Use strong passwords** for all services
3. **Testnet only** for development (BINANCE_TESTNET=True)
4. **Secure credential sharing** when providing to development team

## 📋 **Credential Checklist**

- [ ] **Neon PostgreSQL**: Connection URL from dashboard
- [ ] **Upstash Redis**: Redis URL and REST URL from dashboard  
- [ ] **Cloudflare R2**: Account ID, Access Key, Secret Key from API tokens
- [ ] **Binance API**: Testnet API key and secret (if not already configured)

## 🎯 **Next Steps**

1. **Create .env file** in project root using this template
2. **Fill in actual credentials** from each service dashboard
3. **Test connections** with provided scripts
4. **Start Phase 1.3 development** once all credentials verified 