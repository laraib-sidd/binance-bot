# Cloud Services Usage Limits & Monitoring

## 🎯 **Service Overview & Free Tier Limits**

This document tracks all cloud service usage limits for the Helios Trading Bot to ensure we stay within free tier allocations and optimize resource usage.

**Last Updated**: December 22, 2024
**Current Status**: All services within free tier limits ✅

---

## 📊 **Active Services & Limits**

### **1. Neon PostgreSQL**
- **Plan**: Free Tier
- **Database**: `helios_trading` 
- **Region**: Asia-Pacific Southeast (Singapore)
- **Limits**:
  ```
  Storage: 10 GB maximum
  Compute Hours: 100 hours/month
  Connections: 1000 concurrent max
  Databases: 10 per project
  Branches: 10 per project
  ```
- **Estimated Usage**:
  ```
  Storage: ~100MB/month (market data)
  Compute: ~20 hours/month (trading operations)
  Connections: 5-10 concurrent (bot operations)
  ```
- **Usage %**: ~1% storage, ~20% compute
- **Monitor**: Storage growth, compute hours remaining

### **2. Upstash Redis**
- **Plan**: Free Tier ✅ **JUST SELECTED**
- **Database**: `helios-cache-prod`
- **Region**: Singapore (ap-southeast-1)
- **Limits**:
  ```
  Max Data Size: 256 MB
  Max Monthly Bandwidth: 10 GB
  Commands: Unlimited (free tier)
  Connections: 100 concurrent
  Eviction: Enabled (optimistic-volatile)
  ```
- **Eviction Policy Notes**:
  ```
  optimistic-volatile = volatile-random + allkeys-random
  - Prioritizes removing keys with TTL/expiration first
  - Falls back to random removal when memory full
  - Strategy: Set appropriate TTLs on all trading data
  ```
- **Estimated Usage**:
  ```
  Data Size: ~50MB (current prices + indicators)
  Bandwidth: ~2GB/month (real-time updates)
  Commands: ~500K/month (price updates + queries)
  ```
- **Usage %**: ~20% storage, ~20% bandwidth
- **Monitor**: Memory usage, bandwidth consumption

### **3. Cloudflare R2** (Setup in Progress)
- **Plan**: Free Tier
- **Bucket**: `helios-trading-datalake` (to be created)
- **Region**: Global (Auto-optimized)
- **Limits**:
  ```
  Storage: 10 GB/month
  Class A Operations: 1M/month (PutObject, ListObjects, etc.)
  Class B Operations: 10M/month (GetObject, HeadObject, etc.)
  Data Transfer: FREE (unlimited egress)
  ```
- **Operation Types**:
  ```
  Class A (expensive): PutObject, CopyObject, ListObjects
  Class B (cheaper): GetObject, HeadObject, UsageSummary
  Free Operations: DeleteObject, DeleteBucket
  ```
- **Estimated Usage**:
  ```
  Storage: ~2GB/month (historical parquet files)
  Class A: ~100/month (daily data uploads)
  Class B: ~5K/month (backtesting queries)
  Transfer: ~1GB/month (FREE egress)
  ```
- **Usage %**: ~20% storage, ~0.01% Class A, ~0.05% Class B
- **Monitor**: Storage accumulation, operation counts (very low usage)

---

## 📈 **Usage Monitoring Strategy**

### **Daily Monitoring Checklist**
```python
DAILY_CHECKS = {
    "neon_compute_hours": "Check dashboard for remaining hours",
    "upstash_memory": "Monitor Redis memory usage",
    "upstash_bandwidth": "Track monthly bandwidth consumption",
    "r2_storage": "Monitor bucket size growth",
    "overall_costs": "Verify all services remain $0/month"
}
```

### **Weekly Optimization Review**
```python
WEEKLY_REVIEW = {
    "data_cleanup": "Remove old Redis cache entries",
    "storage_optimization": "Compress old parquet files",
    "query_efficiency": "Optimize database queries",
    "bandwidth_usage": "Review API call patterns"
}
```

### **Monthly Limit Assessment**
```python
MONTHLY_ASSESSMENT = {
    "storage_projection": "Project storage needs for next month",
    "compute_optimization": "Review Neon compute usage patterns",
    "bandwidth_trending": "Analyze bandwidth growth trends",
    "upgrade_planning": "Assess if paid plans needed"
}
```

---

## 🚨 **Usage Alerts & Thresholds**

### **Warning Thresholds (Take Action)**
```python
WARNING_THRESHOLDS = {
    "neon_storage": "8GB (80% of 10GB limit)",
    "neon_compute": "80 hours (80% of 100 hours/month)",
    "upstash_memory": "200MB (78% of 256MB limit)",
    "upstash_bandwidth": "8GB (80% of 10GB/month)",
    "r2_storage": "8GB (80% of 10GB/month)",
    "r2_class_a_ops": "800K writes (80% of 1M/month)",
    "r2_class_b_ops": "8M reads (80% of 10M/month)"
}
```

### **Critical Thresholds (Emergency Action)**
```python
CRITICAL_THRESHOLDS = {
    "neon_storage": "9.5GB (95% of limit)",
    "neon_compute": "95 hours (95% of limit)",
    "upstash_memory": "240MB (94% of limit)", 
    "upstash_bandwidth": "9.5GB (95% of limit)",
    "r2_storage": "9.5GB (95% of limit)"
}
```

### **Mitigation Strategies**
```python
MITIGATION_ACTIONS = {
    "neon_storage_high": [
        "Archive old market data to R2",
        "Compress OHLCV data",
        "Remove duplicate records"
    ],
    "neon_compute_high": [
        "Optimize query efficiency", 
        "Reduce connection pool size",
        "Cache frequent queries in Redis"
    ],
    "upstash_memory_high": [
        "Set appropriate TTLs on all keys (optimistic-volatile priority)",
        "Reduce TTL values for less critical data",
        "Remove old cache entries manually",
        "Optimize data structures and payload sizes"
    ],
    "upstash_bandwidth_high": [
        "Reduce API polling frequency",
        "Batch operations",
        "Optimize data payload sizes"
    ]
}
```

---

## 💰 **Cost Optimization Tracking**

### **Current Monthly Cost**: $0.00 ✅
```python
COST_BREAKDOWN = {
    "neon_postgresql": "$0.00 (Free tier)",
    "upstash_redis": "$0.00 (Free tier)", 
    "cloudflare_r2": "$0.00 (Free tier)",
    "total_monthly": "$0.00"
}
```

### **Upgrade Cost Analysis** (If Needed)
```python
UPGRADE_COSTS = {
    "neon_pro": "$19/month (50GB storage, 1000 compute hours)",
    "upstash_pro": "$10/month (1GB memory, 100GB bandwidth)",
    "r2_storage": "$0.015/GB/month (beyond 10GB)",
    "estimated_pro_total": "$30-40/month at scale"
}
```

---

## 📊 **Usage Tracking Implementation**

### **Monitoring Scripts** (To Be Implemented)
```python
# File: scripts/monitor_usage.py
class UsageMonitor:
    def check_neon_usage(self):
        """Query Neon API for storage/compute usage"""
        
    def check_upstash_usage(self):
        """Query Upstash API for memory/bandwidth usage"""
        
    def check_r2_usage(self):
        """Query Cloudflare API for storage/operations usage"""
        
    def generate_usage_report(self):
        """Generate daily usage report"""
        
    def check_thresholds(self):
        """Alert if approaching limits"""
```

### **Usage Dashboard** (Future Enhancement)
```python
# Simple dashboard showing:
DASHBOARD_METRICS = {
    "current_usage_percentages": "All services",
    "monthly_trends": "Growth patterns",
    "cost_projections": "If usage continues",
    "optimization_suggestions": "Automated recommendations"
}
```

---

## 🎯 **Scaling Strategy**

### **Growth Milestones**
```python
SCALING_MILESTONES = {
    "milestone_1": {
        "trigger": "80% of any free tier limit",
        "action": "Implement usage optimizations"
    },
    "milestone_2": {
        "trigger": "Consistent 90%+ usage",
        "action": "Plan paid tier upgrades"
    },
    "milestone_3": {
        "trigger": "$700+ monthly revenue from bot",
        "action": "Upgrade to paid plans for reliability"
    }
}
```

### **Service Priority for Upgrades**
```python
UPGRADE_PRIORITY = [
    "1. Upstash Redis (most critical for trading performance)",
    "2. Neon PostgreSQL (storage and compute reliability)",
    "3. Cloudflare R2 (least critical, ample free tier)"
]
```

---

## 📝 **Usage Log**

### **December 22, 2024 - Initial Setup**
- ✅ **Neon PostgreSQL**: Project created, Singapore region
- ✅ **Upstash Redis**: Free plan selected, 256MB/10GB limits
- ⏳ **Cloudflare R2**: Setup pending
- **Status**: All services within free tier
- **Next Review**: December 29, 2024

### **Usage Notes**
```
Week 1: Initial setup and basic data pipeline
Week 2: Add real-time market data ingestion  
Week 3: Implement trading strategies
Week 4: Full production deployment
```

---

**🔄 This document will be updated weekly with actual usage metrics and optimization actions.** 