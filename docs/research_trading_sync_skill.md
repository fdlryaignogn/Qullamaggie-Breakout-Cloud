# Research ↔ Trading synchronization contract (research_trading_sync_skill)

Status: DRAFT — coordination only; no trading logic changed.
Updated: 2026-10-24

## Workstream ownership
- Research Lab thread: historical cases, OHLCV snapshots, annotations, training/validation/test, backtests, win rate, net expectancy (R), rule proposals and evidence.
- Trading System thread: stage 1 momentum scan, stage 2 setup lifecycle, stage 3 breakout signals, eventual order/risk management.

## Related coordination files
- `AGENTS.md`
- `PROJECT_STATE.json`
- `skills/project_coordination/SKILL.md` (entry point)
- `skills/project_coordination/develop_sync_skill.md` (detailed workflow)

## Source of truth
This GitHub repository is the cross-thread handoff point. Each thread must read the latest relevant files and commit before making changes; chat history is not real-time shared state.

## Data contract (proposal)
- Research outputs: rule_id, version, stage, parameters, training_period, validation_period, test_period, sample_count, win_rate, expectancy_net_R, profit_factor, max_drawdown, assumptions, approval_status, source_commit.
- Lifecycle: EXPERIMENTAL -> VALIDATED -> APPROVED -> RETIRED. Only APPROVED rules may be used by production screening.
- Trading feedback: setup_id, symbol, as_of_date, stage, status, strategy_version, signal_time, entry/stop/exit, fees, slippage, realized_R, data_quality.

## Invariants
- Stage 1 uses the union of top momentum windows; a stage 2 FORMING/READY setup is not dropped merely for failing a subsequent stage 1 screen.
- No future candles in historical setup decisions; no assumption of intrabar sequence without suitable data.
- Triggered signals are not fills; no auto-trading without separate approval.
- Research win rate and expectancy are not production performance until independently tested.
- Do not change production rule files from the Research Lab workstream without review.

## Handoff procedure
1. Research thread publishes versioned experiment report and proposed rule JSON with source commit.
2. Trading thread reads proposal, checks compatibility, and runs integration tests.
3. After independent validation and approval, Trading thread pins the approved version.
4. Trading thread publishes execution/signal outcome data for Research Lab evaluation.
5. Both threads update this file when interfaces change.

## Current status
Coordination document created. No automatic live cross-thread notifications, database sync, or deployed Research Lab integration is yet established.
