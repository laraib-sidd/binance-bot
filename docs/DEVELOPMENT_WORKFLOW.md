# Development Workflow Guide

## Mandatory Branch Protection Workflow

**CRITICAL**: This document demonstrates the correct development process that must be followed for ALL changes to the Helios Trading Bot project.

## Why This Matters

The recent project setup was done **incorrectly** by pushing directly to `main` branch, violating our own rules in `009-git-branch-protection.mdc`. This document ensures proper workflow going forward.

## Correct Development Process

### 1. Branch Naming Conventions
```bash
# Feature branches
git checkout -b feat/add-signal-engine
git checkout -b feat/implement-grid-logic

# Bug fixes
git checkout -b fix/order-execution-error
git checkout -b fix/risk-calculation-bug

# Documentation
git checkout -b docs/update-api-documentation

# Architecture changes
git checkout -b arch/add-multi-exchange-support
```

### 2. Development Workflow
```bash
# Step 1: ALWAYS review current project status (MANDATORY)
cat local/docs/CHANGELOG.md | head -20
cat PROJECT_STATUS.md

# Step 2: Create feature branch from main
git checkout main
git pull origin main
git checkout -b feat/your-feature-name

# Step 3: Make your changes
# (implement your feature following all rules)

# Step 4: Update documentation (MANDATORY)
# Update local/docs/CHANGELOG.md with your changes
# Update PROJECT_STATUS.md if needed

# Step 5: Test your changes
pytest tests/
black src/
flake8 src/

# Step 6: Commit with descriptive message
git add -A
git commit -m "feat: implement signal analysis engine with ATR-based volatility detection"

# Step 7: Push feature branch
git push origin feat/your-feature-name

# Step 8: Create PR with comprehensive documentation
# Create PR_BODY.md with full analysis
gh pr create --title "Implement Signal Analysis Engine" --body-file PR_BODY.md --base main --head feat/your-feature-name

# Step 9: After PR is merged, cleanup
git checkout main
git pull origin main
git branch -d feat/your-feature-name
rm PR_BODY.md  # Mandatory cleanup
```

### 3. Pull Request Requirements

Every PR must include:
- [ ] Architecture diagrams showing system impact
- [ ] Comprehensive change documentation
- [ ] Usage examples
- [ ] Testing strategy
- [ ] Risk assessment (for trading logic changes)
- [ ] Performance impact analysis

### 4. Never Push Directly to Main

**ABSOLUTE RULE**: The main branch is protected. ALL changes must go through PR process.

**Violations of this rule will require:**
- Immediate rollback of changes
- Proper re-implementation via feature branch
- Documentation of the mistake
- Process improvement to prevent recurrence

## Example PR Process

This document itself demonstrates the correct process:
1. Created feature branch: `feat/demonstrate-proper-branch-workflow`
2. Made changes on feature branch
3. Will create PR with proper documentation
4. Will merge via PR process
5. Will cleanup branch and PR_BODY.md

## Enforcement

The `.cursor/rules/009-git-branch-protection.mdc` rules are mandatory:
- All team members must follow branch workflow
- No exceptions for "small changes"
- Automated checks should be implemented
- Process violations must be documented and corrected

## Benefits of Proper Workflow

1. **Code Quality**: PR reviews catch issues before merge
2. **Documentation**: Complete change history and rationale
3. **Collaboration**: Multiple developers can work safely
4. **Risk Management**: Financial code requires careful review
5. **Compliance**: Audit trail for all changes

---

**Remember**: The goal is not bureaucracy, but **financial safety** and **professional development standards** for a trading bot that handles real money. 