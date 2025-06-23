# Environment Configuration Template

Copy the content below to create your `.env` file in the project root directory.

**IMPORTANT**: Never commit `.env` to version control! It's already in `.gitignore`.

## Basic .env File Structure

```bash
# Helios Trading Bot - Environment Configuration
# IMPORTANT: Never commit .env to version control!

# =============================================================================
# BINANCE API CONFIGURATION (REQUIRED)
# =============================================================================
# Get these from your Binance account (use testnet for development)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
BINANCE_TESTNET=true

# =============================================================================
# DATABASE CONFIGURATION (REQUIRED - Choose one option)
# =============================================================================

# OPTION 1: Full Connection URL (if you have a single connection string)
# NEON_DATABASE_URL=postgresql://username:password@hostname:5432/database_name

# OPTION 2: Individual Components (if you have separate host, db, user, password)
DB_HOST=your_database_host
DB_DATABASE=your_database_name  
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_PORT=5432

# =============================================================================
# OPTIONAL CLOUD SERVICES (Phase 1.3 - can be added later)
# =============================================================================

# Redis Cache (Optional - for caching market data)
# UPSTASH_REDIS_URL=redis://username:password@hostname:port

# Cloudflare R2 Storage (Optional - for data archiving)
# R2_ACCOUNT_ID=your_r2_account_id
# R2_API_TOKEN=your_r2_api_token  
# R2_BUCKET_NAME=your_r2_bucket_name
# R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com

# =============================================================================
# TRADING ENVIRONMENT SETTINGS
# =============================================================================
TRADING_ENVIRONMENT=development
LOG_LEVEL=INFO
DATA_DIRECTORY=local/data

# =============================================================================
# NOTIFICATION SETTINGS (Optional)
# =============================================================================
# Telegram notifications (Optional)
# TELEGRAM_BOT_TOKEN=your_telegram_bot_token
# TELEGRAM_CHAT_ID=your_telegram_chat_id

# Discord notifications (Optional)  
# DISCORD_WEBHOOK_URL=your_discord_webhook_url

# =============================================================================
# TRADING PARAMETERS (Optional - uses defaults if not set)
# =============================================================================
# MAX_POSITION_SIZE_USD=100.00
# MAX_DAILY_LOSS_USD=50.00
# MAX_ACCOUNT_DRAWDOWN_PERCENT=25.00
# GRID_LEVELS=10
# GRID_SPACING_PERCENT=1.0
# SIGNAL_CHECK_INTERVAL_SECONDS=30
# PRICE_UPDATE_INTERVAL_SECONDS=5
```

## Configuration Options Explained

### Database Configuration

You can configure the database connection in two ways:

#### Option 1: Full Connection URL
If you have a complete PostgreSQL connection string:
```bash
NEON_DATABASE_URL=postgresql://username:password@hostname:5432/database_name
```

#### Option 2: Individual Components  
If you have separate database parameters:
```bash
DB_HOST=your_database_host
DB_DATABASE=your_database_name  
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_PORT=5432
```

The setup script will automatically build the connection URL from individual components.

### Required vs Optional Variables

**Required for Phase 1.3:**
- Binance API credentials (`BINANCE_API_KEY`, `BINANCE_API_SECRET`)  
- Database connection (either full URL or individual components)

**Optional (can be added later):**
- Redis cache for performance optimization
- Cloudflare R2 for data archiving
- Notification services (Telegram, Discord)
- Custom trading parameters (uses sensible defaults)

## Setup Instructions

1. **Create your .env file:**
   ```bash
   cp docs/ENVIRONMENT_TEMPLATE.md .env
   # Edit .env and replace all placeholder values
   ```

2. **Fill in your actual values:**
   - Replace `your_binance_api_key_here` with your actual Binance API key
   - Replace database placeholders with your actual database credentials
   - Add optional services as needed

3. **Verify configuration:**
   ```bash
   uv run python -m scripts.setup_phase_1_3
   ```

The setup script will now work with either database configuration method and only require the essential components for Phase 1.3 to function. 