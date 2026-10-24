---
name: project_coordination
description: Coordinate Qullamaggie Research Lab and Trading System threads using GitHub as source of truth; prevent conflicting edits and unvalidated strategy promotion.
---
# Qullamaggie Project Coordination Skill

## Mandatory startup
1. Read latest `docs/RESEARCH_LAB_SYNC.md` from default branch of `fdlryaignogn/Qullamaggie-Breakout-Cloud`.
2. Inspect latest relevant repository files and commits; do not assume chat memory is current.
3. Identify your workstream: Research Lab (training, annotation, backtest) or Trading System (screening, signals, risk, execution).
4. Check open work and conflicting edits before modifying shared interfaces.

## Mandatory completion
1. Commit changes with clear scope and tests, preferably on a feature branch and PR for shared interfaces.
2. Record what changed, current deployment status, tests passed/failed, next action and commit SHA in the handoff record or linked PR.
3. If interface or strategy contract changed, update `docs/RESEARCH_LAB_SYNC.md`.
4. Never claim a live deployment without verifying the actual URL and functionality.

## Research-to-Trading handoff
Publish rule version, stage, parameter schema, train/validation/test dates, sample size, net win rate, expectancy in R, profit factor, drawdown, costs/slippage assumptions, limitations, approval state, and source commit. Experimental rules must not silently replace production rules.

## Trading-to-Research handoff
Publish reproducible signal/trade records with setup_id, timestamps, strategy version, entry/stop/exit, costs, realized R, and data-quality flags. A trigger is not a fill.

## Safety invariants
- Preserve stage 1 momentum union logic.
- Keep existing stage 2 FORMING/READY setups when stage 1 momentum rank falls; change status only for stage 2 structural reasons.
- No lookahead in backtests; no fabricated intrabar order without intraday data.
- Human approval required before live order execution.

## Important limitation
A GitHub Skill file is not automatically installed or run in every chat. Each thread must explicitly adopt this workflow through its Project instructions or by reading this file. GitHub is shared durable state, not instant cross-thread notification.
