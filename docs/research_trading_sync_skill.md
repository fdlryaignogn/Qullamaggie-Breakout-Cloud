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

## EOD Trigger UI clarity correction (2026-10-25)
- Both Trigger modes must stay selectable **for inspection** when the required checklist fails; they show specific failed checks and approval/EOD timestamps. Submission stays disabled unless that mode is eligible. The server repeats all guards, without allowing backdated events.
- For the 2026-10-23 EOD snapshot, NIQ/RBRK/RPD were approved on 2026-10-24; neither first-cross nor post-approval hold qualifies on that older EOD. Next EOD may qualify only after publication of a new completed session and verified price evidence.
- No change to research parameters, trade execution, or Stage 1/Stage 2 rules.

## Stage 4 Post-Trigger Trading System boundary (2026-10-25)

- Owner requested a **fourth tab** for post-Trigger trade planning and fundamental/evidence review; this Trading System feature is independent of Research Lab's historical tests. See `docs/stage4_trade_planning.md`.
- Stage 4 consumes only persisted Stage 3 `TRIGGERED` with authentic manual review, never Watch or `EOD_CROSS` inferred retrospectively. It cannot change Stage 1, Stage 2, Stage 3 or publish trades.
- The calculator is strictly user-entered hypothetical entry/stop/risk/equity/cash/slippage/fee/lot planning, with risk- and cash-capped position size. Broker connectivity, automatic orders and realized P&L are absent. Account amounts stay in tab memory, not in public GitHub JSON.
- Official SEC companyfacts annual XBRL fields and recent Form 4 **filing counts** may be populated for confirmed tickers from an opt-in, identified SEC collection workflow; missing values remain `UNAVAILABLE`, not zero. SEC automation needs the `SEC_USER_AGENT` repository secret with a real contact before use.
- SEC 13F is delayed quarter-end *holdings*, **not verified current institutional buying**. Form 4 presence is **not verified insider buying**; purchase requires inspecting transaction code P and acquisition details. The public UI must show unverified statuses until separately evidenced, never automatically infer purchases or recommendations.
- Optional manually cited institutional/insider observations are labeled unverified and stored in this browser only, not cross-device or authoritative cloud. These notes have no effect on triggers or positions.
- Future Research Lab handoff of any actual approved signal/entry must preserve as-of evidence dates, authorization time, source, fees and slippage rather than fabricating fills.

## Stage 3 single Trigger action, auto-selected EOD subtype (2026-10-25)

- Supersedes earlier dashboard UX notes offering two manually selectable EOD Trigger actions. Trading System now presents **one** `CONFIRM_TRIGGER` option on an authenticated Stage-3 WATCH; it is always selectable for inspection but cannot be submitted when conditions fail.
- The browser shows the automatically detected FIRST_EOD_CROSS (previous close ≤ pivot; current completed close > pivot), POST_APPROVAL_HOLD (previous and current completed closes > pivot), or no eligible pattern. These daily price alternatives are **mutually exclusive**, not two reviewer decisions. Relevant checks and failed reasons remain visible.
- The GitHub workflow and optional auth gateway accept only the new public Trigger action. The Python backend recomputes the unique subtype from original adjusted 1d OHLCV and persisted same-session EOD fields, not from a user-supplied subtype, and records the distinct `eod_trigger_confirmation_type` and `trigger_rule` in the audit. Older internal validation aliases remain only for regression/historical compatibility.
- READY must have been manually approved by the exact **16:00:00 New York** boundary for the relevant completed EOD; stale revisions and October 23 Friday breakout with October 24 Saturday READY remain ineligible. No retroactive signal, order, fill, automatic TRIGGERED or production research threshold promotion.
- Stage 4 continues consuming the single final status `TRIGGERED` with subtype metadata and is unaffected. Research Lab remains responsible for historical validation and not UX deployment.

## Stage 2 READY is a persisted parent, NOT a visible Stage 2 queue item (2026-10-25)

- Supersedes the earlier 2026-10-25 proposal to show approved READY in Stage 2 with a child-status column and navigation. Owner explicitly wants **no READY stock listed on the Stage 2 webpage** after approval, even though its source record must remain available to Stage 3.
- Filter every `setup_status=READY` from the Stage 2 browser table, displayed Stage 2 tab count and status selection; do **not** delete it from the underlying `state['2']`, state JSON, review history or full backups. Keep FORMING / DEVELOPING and other unresolved Stage 2 states visible. Stage3 WATCH/TRIGGERED always lives and is displayed in Stage 3.
- `review_setup.py` creates Stage 3 WATCH for a manually approved READY; review continues in Stage3, with the Stage2 parent still consulted by future Stage3 evidence, Pivot and approval-time validation. A READY without a Stage3 child is a data consistency concern, not a reason to show it again in Stage2, and may require a separate audit repair.
- The same PR retains the owner requirement to show two Trigger types in Stage3 while allowing **at most one valid option** for one EOD. The browser maps either display choice to canonical `CONFIRM_TRIGGER`; the verified server independently decides and persists the real subtype. No change to Research Lab, auto-order boundaries or EOD eligibility rules.
 
## R-001 metadata comparison contract (research-only, 2026-10-25)
- Versioned machine source: `site/data/r001_event_comparison_v0_2.json`, maintained by Historical Superstocks Research; Google Sheet shows human-first matrix (Name | Schema | I/O Role | Event columns) and an `Events_ML` row-oriented tab for machines.
- `io_role: INPUT | OUTPUT | META` is **required**: `INPUT` is as-of candidate feature, `OUTPUT` is future result label not usable as X, `META` is event identity, publication/provenance, QA or eligibility context.
- Historical fundamental releases must have public `release_date < event_date` unless exact market-close publication clock is audited. Maintain period-end date independently; original reported EPS split bases and preliminary/restatement warnings must be preserved.
- ROIC/ROE/ROA, FCF and other missing historic features stay null (never zero by default) pending PIT documentation.
- This is a **research data-interface proposal**, not a change to any production rule, approved signal or research-to-trading gate. No inference from two overlapping AAPL events or outcome-driven replacement of selected event.

## R-001 Price-In feature extensions v0.3 (2026-10-27)
- Research-only schema at `site/data/r001_event_comparison_v0_3.json` retains original I/O separation and extends it with **dated analyst expectation vintages**, earnings surprises, forecast revisions, event-premium runup, peer valuation and price-reaction proxies.
- `normalization_contract_v0_3.mjs` proposes bounded signed scoring in [-1,+1] from **historical TRAIN-fitted** frozen median/MAD, direction, cohort version/vintage. An uncalibrated or unavailable feature must yield null, NOT 0. Do not choose polarity after observing candidate future winners. No fixed F/S/P aggregate weighting is authorized.
- `INPUT` as-of candidates are not automatically active screening filters; `OUTPUT` forward winner/returns must never leak into X; `META` controls source, cutoff, validation, calibration and report completeness.
- Normalization and analyst consensus must never be fetched from post-event records unless their **original before-event vintages** are explicitly reconstructible. Announcement reaction must end before the trading event cutoff.
- All original user-approved R-001 preregistered event rules, B-001 gate, Stage 1/2/3 Trading System logic and execution permissions are unchanged.


## R-001 archival consensus news evidence v0.4 (2026-10-28)
- Point-in-time market consensus may be provisionally described from a **contemporaneous, dated PRE-EARNINGS PUBLIC ARTICLE** referencing analysts, but that is **not equivalent** to a verified proprietary analyst-vendor snapshot (unknown precise vintage UTC, participant count and accounting basis). Preserve `quote_date`, `earnings_release_date`, `event_date`, provider and article URL, distinct from actual vendor timestamp.
- Required ordering: article publication **strictly before** earnings announcement date, which in turn is strictly before the candidate breakout event, unless independent precise clock audit permits a more specific rule. After-report retrospective quotes must not be substituted for pre-report consensus.
- Multiple published estimates on separate dates may conflict (AAPL FY2005Q4 $3.68bn / $3.72bn, with later retrospective $3.74bn). Keep all quotes; use explicitly documented source/date selection, not outcome-based revisions. Never infer exact forecast-revision percentage from mixed contemporary publishers without the vendor's dated vintages.
- A provisional raw **sales surprise** is arithmetic from same-period USD revenue expectations and Apple's dated actual; **EPS surprise remains null** until GAAP/non-GAAP, special tax, split and restatement comparability verified. No -1..+1 normalized Price In score from this partial evidence.
- Earnings next-session raw closing return is a descriptive owner-data diagnostic and not an abnormal market-model return; it may be confounded by same-day product launches. Source FMP private OHLCV must not be redistributed as a public series.
- Machine research source: `site/data/r001_event_comparison_v0_4.json`, dated quote report `research/r001/contemporaneous_expectations_v0_4.md`, validation `research/r001/validate_contemporaneous_expectations_v0_4.mjs`. No production Trading System or R-001/B-001 gate alteration.
