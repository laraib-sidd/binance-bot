# Phase 1.3 Data Pipeline Testing Guide

## Overview
This guide provides step-by-step instructions for testing the Phase 1.3 Data Pipeline Foundation.

## Prerequisites
- ✅ **Phase 1.1**: Environment Setup Complete
- ✅ **Phase 1.2**: Binance API Integration Complete  
- ✅ **Credentials**: All cloud service credentials in `.env` file

## Required Environment Variables

Create or update your `.env` file with:

```env
# Binance API (from Phase 1.2)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BINANCE_TESTNET=true

# Phase 1.3 Data Pipeline
NEON_DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
UPSTASH_REDIS_URL=redis://default:pass@host:port
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_API_TOKEN=your_r2_api_token
R2_BUCKET_NAME=helios-trading-datalake
R2_ENDPOINT=https://your_account_id.r2.cloudflarestorage.com
```

## Step-by-Step Testing

### Step 1: Install Dependencies
```bash
# Install new Phase 1.3 dependencies
helios-setup-phase13
```

### Step 2: Run Complete Test Suite
```bash
# Run comprehensive data pipeline tests
helios-test-pipeline
```

## Expected Test Results

The test suite runs **6 comprehensive tests**:

### ✅ Test 1: Configuration Validation
- Loads `.env` file automatically
- Validates all required environment variables
- Masks sensitive data in output

### ✅ Test 2: Connection Managers  
- Tests PostgreSQL connection (Neon)
- Tests Redis connection (Upstash)
- Tests R2 connection (Cloudflare)
- Measures connection response times

### ✅ Test 3: Database Schema
- Creates 8 production tables
- Creates 15+ optimized indexes  
- Tests basic CRUD operations
- Validates constraints and triggers

## Performance Expectations

### Connection Times
- **PostgreSQL**: <500ms (Asia-Pacific)
- **Redis**: <200ms (Singapore)
- **R2**: <1000ms (Global)

### Processing Speed
- **Throughput**: >5 tickers/second
- **Individual processing**: <200ms/ticker
- **Database operations**: <100ms

### Success Criteria
- ✅ **All tests pass**
- ✅ **0 errors, minimal warnings**
- ✅ **Performance within targets**
- ✅ **All services healthy**

## Next Steps After Successful Testing

1. **Commit Changes**: All tests pass
2. **Update Documentation**: Phase 1.3 complete
3. **Plan Phase 1.4**: Real-time data collection
4. **Monitor Usage**: Track free tier limits
5. **Performance Tuning**: Optimize based on metrics 