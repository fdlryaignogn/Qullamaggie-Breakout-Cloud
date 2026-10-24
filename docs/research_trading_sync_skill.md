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

## Trading System Stage 3 operating decision (2026-10-24)
- Stage 3 is **EOD-only** per owner direction: no minute-bar acquisition, opening-range trigger engine or intraday automation is in scope.
- Only manually approved Stage-2 READY setups are followed as Stage-3 WATCH. A daily close crossing the pivot is an `EOD_CROSS` descriptive observation, **not** an intraday TRIGGERED event, fill or order.
- A post-scan manual READY review may hydrate EOD metrics from the verified same-session public daily-chart cache. It must not alter the scan's `as_of_date` / `last_success`, fetch fresh prices, approve additional setups, infer stops/fills, or fabricate a fresh scan notification.
- Research Lab may consume versioned EOD observations with explicit session date, missing-data flags and source commit, but must not treat these observations as realized trading performance.

## EOD publication audit
- The Trading System can run `python stage3_eod_audit.py --strict` against a saved, successful `site/data/latest.json` snapshot and same-session adjusted 1d chart files.
- Audit results distinguish `PERSISTED_MATCH`, `DERIVED_NOT_PERSISTED`, `METRIC_MISMATCH`, and `CHART_UNAVAILABLE`; they are descriptive validation flags, not trading signals or Research Lab approval states.
- Browser fallback EOD metrics must verify chart symbol, as-of date, 1d interval, and adjusted-data provenance. An obsolete asynchronous chart response cannot replace newer scan data.
- The audit neither downloads prices nor writes state; it does not prove GitHub Pages is accessible or a new market session has been scanned.

## Historical EOD publication backfill (2026-10-24)
- Once-a-day WATCH values for the completed 2026-10-23 session were recoverable for NIQ, RBRK, and RPD from already published adjusted 1d charts and manual READY approvals.
- Historical metrics are committed into both `data/tracking_state.json` and `site/data/latest.json` together through a reviewed PR. The original scan's `metadata.as_of_date`, `metadata.last_success`, approvals and history must remain unchanged. The public data revision may increment to make open dashboards reload the corrected snapshot.
- `stage3_eod_backfill.py` is an opt-in deterministic repair utility: preview by default; `--apply` only under operator supervision, with chart provenance, parent/record consistency, idempotence and conflict checks. Do not use it to create a newer scan or imply the public site was visually verified.
- A stored `EOD_CROSS` remains a historical daily observation, not a validated trade signal, order, or realized return. Research Lab promotion still follows the documented human-approved strategy lifecycle.

## Experimental Stage 3 EOD V2 classification handoff (2026-10-24)
- Research-only candidate logic: `stage3_eod_v2_research.py` and `research/proposals/stage3_eod_v2_0_1_0.json`; explanation in `docs/stage3_eod_v2_experimental.md`. Status `EXPERIMENTAL`, version 0.1.0, production disabled.
- Labels `WATCH`, `NEAR_BREAKOUT`, `EOD_BREAKOUT`, `STRONG_EOD_BREAKOUT`, `ABOVE_PIVOT`, `RECHECK`, `DATA_UNAVAILABLE` are **provisional research annotations** (3% below-pivot and 1.5x prior-volume are invented research hypotheses, not official standards).
- Report `point_in_time_eligible` separately from `classification`. Manual READY approved after the EOD session cannot be counted as a valid hypothetical signal for that past date. In the historical 2026-10-23 snapshot, NIQ/RBRK/RPD were approved only on October 24: all **ineligible** for October 23 prospective signal counts, despite EOD_CROSS.
- Handoff to Research Lab requires frozen as-of pivots and approvals, representative historical cohorts, no-leakage replay, explicit training/validation/test periods, sample size, after-cost expectancy (R), win rate, profit factor and drawdown. No performance values have been validated.
- Module is read-only and excluded from production Stage 3, Stage 2 READY approval, statuses and broker execution. Only independently validated and owner-approved future PRs can promote rules.

## Trading System Stage 3 EOD web action contract (2026-10-24)
- The Stage 3 cloud dashboard offers `查看 EOD / EOD details` to readers and a GitHub-authenticated `Action` menu for WATCH rows.
- Allowed human decisions are `KEEP_WATCH` (WATCH -> WATCH), `NO_TRADE` (WATCH -> NO_TRADE), and `ARCHIVE` (WATCH -> ARCHIVED). All require a public reason; terminal choices require explicit confirmation and cannot be silently reactivated. Stage-2 `INVALIDATED` remains the proper way to invalidate the underlying setup.
- `stage3_review.py` and `.github/workflows/review-stage3.yml` must validate current manually approved READY parent, matching persisted public/private WATCH row, authenticated actor, as-of date and optimistic revision; then update both state files and an audit event, preserving original scan last_success.
- No `TRIGGERED`, trading orders, fills, risk sizing, auto-pivot edits or promotion of experimental EOD V2 thresholds through these web Actions.
- Website OAuth is disabled unless `site/auth-config.json` is deliberately activated with separately deployed and verified secure GitHub App backend. PAT fallback is a temporary tab-memory credential, not a stored or published password.

## Trading System EOD confirmed-trigger UI contract (2026-10-24)

- The Trading System may offer human `CONFIRM_EOD_TRIGGER` as an action on an already-approved Stage-3 WATCH. It is an EOD close-cross confirmation, **not** an intraday trigger, simulated fill, purchase, or automatic order.
- For a state transition to `TRIGGERED` the server independently verifies the published as-of day and unchanged revision, human READY approval on/before that session, a consistent adjusted daily chart and persisted EOD metrics, and a *fresh upward daily closing cross* of the saved pivot. If a necessary condition fails, the action is rejected and reasons are displayed in the UI.
- Volume ratio, ATR, ADR and hypothetical low/stop are **reference metrics**; this feature does not promote Research Lab's experimental 1.5x / 3% thresholds into mandatory production trading rules.
- `TRIGGERED` records the daily evidence date, observed close, manual review timestamp and actor under `EOD_CLOSE_CROSS_MANUAL_V1`. There is **no intraday trigger_time or fill/entry execution inferred**. Every action still requires explicit authenticated human consent and an audit history entry.
- Stage 1 and Stage 2 behavior are unchanged. Retrospective NIQ/RBRK/RPD EOD_CROSS observations dated October 23 remain ineligible for an October 23 triggered event because human approval followed on October 24.

## Two-path manual EOD confirmation contract (2026-10-25)

- Owner approves two separately audited, EOD-only human decisions: `CONFIRM_EOD_TRIGGER` / first upward completed close-cross **after pre-close READY approval**, and `CONFIRM_POST_APPROVAL` / current **post-approval** EOD close still above pivot with the prior completed close also above pivot.
- The latest EOD session requires READY already approved no later than **16:00 New York**, including full timezone validation. Neither mode can annotate an earlier breakout as an entry, forge a trigger time, imply a fill, or place an order.
- Each mode has its own pass/fail checklist in the Dashboard; GitHub backend repeats all validations against adjusted same-session daily chart and persisted EOD fields. `CONFIRM_POST_APPROVAL` uses `EOD_POST_APPROVAL_MANUAL_V1` and stores `POST_APPROVAL_HOLD` separately from `EOD_CLOSE_CROSS_MANUAL_V1` / `FIRST_EOD_CROSS`.
- Research Lab continues to own parameter experiments and historical performance validation. This feature does not promote the experimental V2 volume/proximity thresholds.
