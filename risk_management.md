# Risk Management Framework - Helios Trading Bot

## Overview

Risk management is the cornerstone of profitable trading bot operations. With aggressive return targets of 30-40% monthly and a limited $700 capital base, implementing robust risk controls is essential to prevent catastrophic losses while maximizing profit opportunities.

## Core Risk Principles

### 1. Capital Preservation First
- Never risk more than 1% of total capital per grid session
- Maintain 25% of capital as cash reserve for opportunities  
- Implement circuit breakers at 25% account drawdown
- Scale position sizes based on recent performance

### 2. Position-Level Controls
- Maximum position size: 5% of account balance
- Dynamic stop-loss based on ATR (Average True Range)
- Time-based exits: Maximum 4 hours per grid session
- Correlation limits: Max 3 positions in related assets

### 3. Account-Level Safeguards
- Daily loss limit: 5% of account balance
- Maximum drawdown: 25% (emergency shutdown)
- Trade frequency limit: 20 trades per day
- Mandatory cooling-off periods after losses

## Risk Calculation Framework

### Position Sizing Formula
```
Optimal Position Size = Base Risk × Volatility Factor × Confidence Factor × Performance Factor

Where:
- Base Risk = 1% of account balance
- Volatility Factor = Adjustment for market volatility (0.5-1.5x)
- Confidence Factor = Signal strength adjustment (0.5-1.5x)  
- Performance Factor = Recent performance multiplier (0.5-1.5x)
```

### Stop-Loss Calculation
```
Dynamic Stop-Loss = Entry Price - (ATR × Volatility Multiplier)

Volatility Multipliers:
- Low volatility: 1.5x ATR
- Normal volatility: 2.0x ATR
- High volatility: 2.5x ATR

Maximum stop-loss: 3% of entry price
```

## Emergency Procedures

### Automatic Shutdown Triggers
1. **25% Account Drawdown**: Immediate halt of all trading
2. **5 Consecutive Losses**: 4-hour cooling-off period
3. **API Failures**: Switch to backup systems or manual mode
4. **High Correlation Risk**: Reduce position sizes across correlated assets

### Recovery Protocol
1. Assess losses and identify failure causes
2. Update risk parameters based on lessons learned
3. Validate system integrity through testing
4. Gradual capital redeployment with reduced risk
5. Monitor performance for stability before scaling up

## Risk Monitoring Dashboard

### Real-Time Metrics
- Current account drawdown percentage
- Daily P&L and trade count
- Active position exposure and correlation
- Market volatility and liquidity status
- API health and system status

### Alert Thresholds
- **INFO**: 5% daily loss, 10% account drawdown
- **WARNING**: 10% daily loss, 15% account drawdown
- **CRITICAL**: 15% daily loss, 20% account drawdown
- **EMERGENCY**: 25% account drawdown

## Implementation Guidelines

### Pre-Trade Validation
- Verify sufficient account balance
- Check daily loss limits not exceeded
- Assess market liquidity and volatility
- Validate correlation with existing positions
- Confirm trading hours and restrictions

### In-Trade Monitoring  
- Real-time position P&L tracking
- Stop-loss and take-profit order management
- Correlation risk assessment
- Time-based exit monitoring
- Emergency exit trigger evaluation

### Post-Trade Analysis
- Trade performance evaluation
- Risk parameter effectiveness review
- Correlation impact assessment
- Daily/weekly risk report generation
- Parameter optimization recommendations

This risk management framework ensures that aggressive trading goals can be pursued while maintaining strict capital protection measures. 