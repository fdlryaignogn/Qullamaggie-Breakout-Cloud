# Stage 3 EOD Breakout Signal V2 — EXPERIMENTAL research specification

**Status:** EXPERIMENTAL · **Version:** 0.1.0 · **Production enabled:** No

Owner decision: Stage 3 remains **End of Day only**. Do not acquire minute bars,
assign an opening-range trigger, infer an execution, change Stage 3 `WATCH`,
or automatically buy/sell. Existing production `stage3_eod.py` observations
and human Stage 2 `READY` approval rules remain unchanged.

## Motivation and input data

A breakout *observation* (daily close above the saved pivot) is distinct from
a prospective, point-in-time eligible *research classification*, a live trading
signal, and a fill. This prototype uses `site/data/latest.json` and same-date,
adjusted `site/data/charts/<SYMBOL>.json` files. It recomputes EOD metrics
from original bars rather than trusting potentially stale saved summaries.
Missing/wrong charts, as-of dates, daily interval, and adjusted provenance
fail closed.

Only `WATCH` rows with matching Stage 2 `READY` parent and saved breakout pivot
receive descriptive classifications. Setup IDs remain persistent even if a
stock falls out of Stage 1 momentum rankings.

## Provisional labels (not official Kristjan Qullamaggie criteria)

Priority order:

| Exploratory label | Daily-only definition |
| --- | --- |
| `STRONG_EOD_BREAKOUT` | Previous close <= saved pivot, current close > pivot, and current volume / previous 20 sessions average >= **1.5x** |
| `EOD_BREAKOUT` | Previous close <= pivot and current close > pivot; RVOL unavailable or below 1.5x |
| `ABOVE_PIVOT` | Current and previous closes are above pivot, no fresh upward close-cross |
| `RECHECK` | High touched the pivot but close did not clear it; or previous close > pivot and latest close at/below pivot |
| `NEAR_BREAKOUT` | Current close is at/below pivot and no more than **3%** below, with no RECHECK condition |
| `WATCH` | Other valid, below-pivot daily observations |
| `DATA_UNAVAILABLE` | Required verified daily bars/pivot/parent missing or disagreeing |

The **3%** distance and **1.5x** volume thresholds are configurable research
hypotheses, not approved production parameters or mandatory official rules.
RVOL missing is **unknown**, not zero; it cannot qualify as "strong".

## Point-in-time / human approval gate

A separate `point_in_time_eligible` flag is **false** unless the matching Stage
2 parent is genuinely `READY`, the authenticated `manual_reviewer` and
timezone-aware `manual_reviewed_at` fields are present, and approval occurred
no later than 23:59:59 New York time on the EOD `as_of_date`. For an eligible
row, `earliest_research_available_at` is the **later** of US market close
(16:00 New York) and actual human approval. This is a research availability
timestamp, **not** an entry time.

In the verified 2026-10-23 market snapshot, NIQ, RBRK, and RPD each had
`EOD_CROSS`, but received human READY approval on **2026-10-24**. Their
historical daily observations are valid for study, but **all three are excluded
from point-in-time eligible signal counts for October 23**. A later human
approval must never retroactively create a hypothetical entry.

The source does not yet provide a complete historical, independently frozen
approval/pivot ledger for multiple trading dates. Therefore **full unbiased
backtesting is not established** by this prototype. A frozen pivot and
approval as-of each past session must be reconstructed before performance tests.

## Research Lab handoff and release conditions

Source: `research/proposals/stage3_eod_v2_0_1_0.json`

Read-only exploratory CLI:
```bash
python stage3_eod_v2_research.py --snapshot site/data/latest.json
```

The result provides `rule_id`, `rule_version`, `approval_status`, symbol,
setup ID, EOD as-of date, provisional label, date-qualified human eligibility,
earliest research availability time, daily OHLCV-derived context, and data
quality. No tracked file is written and no order interface exists.

Before promotion to `VALIDATED` or `APPROVED`, Research Lab must provide
a representative point-in-time cohort (including non-winners), independently
frozen pivots/review decisions, predeclared train/validation/test splits,
sample size, win rate, **net expectancy in R**, profit factor, maximum drawdown,
fees/slippage and survivorship-bias assumptions. No such results are claimed
here. Promotion requires explicit owner approval and a new reviewed GitHub PR.

## Regression and safety

- Daily OHLCV only, as-of session pinned; reject even correctly labeled charts
  that contain dates later than their as-of session.
- Wrong symbol, wrong interval or wrong adjustment mode => unavailable.
- A post-EOD human approval can **describe history** but cannot create an
  eligible historical live signal.
- The algorithm never changes status to `TRIGGERED`, creates fills, calculates
  realized returns or modifies `data/tracking_state.json` or public scan JSON.
- Existing Stage 1 union-of-momentum and long-lived Stage 2 setup behavior
  remain unchanged.
