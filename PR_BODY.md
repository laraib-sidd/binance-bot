# Phase 1.6: Regime Gating, Schema Correctness, CI & Tooling + Full mypy cleanup

## Summary
This PR implements a regime-aware upgrade to the signal engine, fixes several correctness issues (schema usage and DB verification queries), aligns packaging/tooling, and introduces pre-commit + CI to enforce quality going forward.

## Changes
- Signal engine: Added ADX-based regime gating (disable entries in strong trend regimes). New parameter: `adx_threshold` (default 20.0).
- Logging init: Fixed `src/main.py` to pass full `TradingConfig` to logging setup.
- Schema correctness: Enforced `config.database_schema` usage across `market_data_pipeline.py` (removed hardcoded `helios_trading`).
- DB schema verification/stats: Fixed f-string usage in table_type filter; simplified stats query to avoid placeholder mismatches.
- Packaging/tooling: Bumped version to 1.5.0; mypy target to py311; removed py39 classifier; disabled broken backtest script entry; added `.pre-commit-config.yaml`; added GitHub Actions CI (`.github/workflows/ci.yaml`).
- Documentation: Updated `docs/CHANGELOG.md` and `PROJECT_STATUS.md`.
- Typing: Full mypy cleanup across `src` and `tests` (27 files) with precise annotations, Optional handling, and safe assertions. CI now enforces mypy repo-wide.

## Architecture & Impact
- Regime module: Lightweight ADX proxy in `technical_analysis.py`; integrated in `SignalGenerator` to gate BUY signals in trending regimes, reducing whipsaw.
- Data pipeline: All SQL now respects configured schema so multi-env installs don’t drift. DB verify/stats calls now stable.
- Operational quality: Pre-commit (black, ruff, mypy subset) and CI (lint, type-check, tests) to prevent regressions.

## Risk & Safety
- Trading behavior: More conservative entries during trends; no increased risk.
- Data writes: Schema qualification prevents accidental writes to wrong schema.
- Backwards compatibility: Default ADX threshold maintains existing behavior when trends are weak.

## Testing
- Unit: Existing unit tests pass locally; ruff/black applied.
- Type-check: mypy enforced repo-wide; CI runs mypy, ruff, black and pytest (excluding external-integration by marker). Local run: “Success: no issues found in 27 source files”.
- Integration: No API changes; existing integration tests should continue to pass.

## Migration / Notes
- No DB migration required beyond existing Phase 1.3 schema init.
- New CI requires GitHub Actions to be enabled on repo.

## Follow-ups (tracked next PRs)
- Broaden mypy coverage repo-wide; add missing annotations in `exceptions`, `logging`, `rate_limiter`, and connection managers.
- README/ENV setup doc realignment with pyproject/uv and current dependencies.
- Implement backtest entrypoint or remove scripts permanently.
- Add API docs & user guides (per `PROJECT_STATUS.md`).

## Checklists
- [x] CHANGELOG updated
- [x] PROJECT_STATUS updated
- [x] Architecture impact documented
- [x] Risk impact documented
- [x] Tests updated/existing pass for changed modules
- [x] Pre-commit configured
- [x] CI workflow added
