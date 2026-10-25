# Stage 3 EOD cloud web Actions

The Stage 3 tab of the public GitHub Pages Dashboard now provides a **read-only
EOD details** button for every WATCH entry, and an **Action** menu for WATCH
records. The public site itself remains read-only; clicking an Action does not
modify localStorage or send a broker order.

## Cloud actions (authenticated GitHub reviewer only)

| Action | Stage 3 transition | Meaning |
| --- | --- | --- |
| KEEP_WATCH | WATCH → WATCH | Keep tracking the manually approved READY setup and save a review reason |
| NO_TRADE | WATCH → NO_TRADE | Human decided not to trade this setup; terminal for that setup |
| ARCHIVE | WATCH → ARCHIVED | Human closed Stage 3 tracking; terminal for that setup |
| CONFIRM_TRIGGER | WATCH → TRIGGERED | **One human action**; GitHub auto-classifies FIRST_EOD_CROSS or POST_APPROVAL_HOLD from the verified EOD chart; never an order or fill |

These are manual **EOD management or signal confirmation actions**, never buy/sell orders or fills.
Both terminal options and EOD TRIGGERED require an explicit checkbox and a 1–500 character public
reason. For structural invalidation of the underlying setup, use the existing
Stage 2 `INVALIDATED` review flow, which also invalidates its Stage 3 WATCH.

### Security and persistence

- A visitor may open EOD details but cannot submit an action without
  authenticated GitHub review access. The `auth-config.json` currently disables
  GitHub App login; a short-lived GitHub fine-grained PAT may be used with only
  this repo's **Actions: write** scope. PAT is kept in page memory only.
- The existing optional OAuth gateway has a dedicated `/stage3/dispatch`
  route with input/role validation and the same GitHub Actions scope
  enforcement. Enabling the gateway requires a separate tested deployment.
- Workflow: `.github/workflows/review-stage3.yml`. Python validation:
  `stage3_review.py`.
- The browser sends the displayed `expected_revision` and
  `expected_as_of_date`. The GitHub workflow re-reads the latest persisted
  snapshot, verifies matching Stage 2 READY parent, identical public/private
  WATCH records, actor identity, and the exact EOD revision. Stale actions
  are rejected, not silently applied to updated prices.
- When accepted, the two JSON state files are committed together and GitHub
  Pages is republished by the review workflow (a GITHUB_TOKEN commit does not
  automatically trigger ordinary push-based site publishing).
- An accepted dispatch means **queued**, not successful. Refresh the public
  snapshot or check the GitHub Actions run to verify completion.

### Invariants

- Do not add intraday data, opening-range triggers or automatic `TRIGGERED`.
- Do not alter Stage 1 momentum/Stage 2 manual READY approvals.
- Do not alter EOD observations/pivots, `metadata.as_of_date` or
  `metadata.last_success` when recording manual Stage 3 decisions.
- Retain a public audit trail: reviewer, time, previous and new Stage 3 states,
  reason, setup ID, and change source. Never collect account or credential data
  in review reasons.
- NO_TRADE and ARCHIVED are terminal in this interface, preventing accidental
  reopening or duplicated orders.
- Stage 3 V2 volume and proximity labels remain **EXPERIMENTAL** research
  annotations; they are not a basis for automatic trade actions.

## Test and deployment truth

`tests/test_stage3_review.py` covers guarded transitions, reviewer, stale
revision/date, confirmed terminal choices, preservation of prices/approvals,
and repeated action rejection. `review-auth/tests/stage3_eod_actions.test.mjs`
covers the OAuth dispatch route's input validation and frontend gating.

A source merge or passing unit test alone does not prove the public Dashboard
has reloaded or that an authenticated Action was exercised live. Only claim
runtime/deployment success after independently verifying a real published
GitHub Actions run and matching public data.

## EOD TRIGGER requirements and UI checklist (manual only)

The Action modal shows each mandatory item with a pass/fail reason, followed by
volume and risk context. The `CONFIRM_TRIGGER` **submit** is disabled when
the browser's advisory checklist fails; the GitHub backend independently
recomputes the full conditions and rejects unqualified submissions:

1. Matching Stage-2 setup still `READY`, with named manual reviewer.
2. Timezone-aware READY approval was made on or before the completed
   EOD trading session (New York calendar day); no retrospective signals.
3. Snapshot phase `success` and pinned `metadata.as_of_date`.
4. Approved breakout pivot is finite and positive.
5. Original chart matches symbol, adjusted **1d** interval and exact session,
   with no future bar at the tail; fresh saved EOD metric fields must
   agree with recalculation.
6. The verified daily bars show **exactly one** eligible EOD pattern:
   previous close ≤ pivot and current completed close > pivot (`EOD_CROSS`),
   **or** previous close > pivot and current completed close > pivot
   (`ABOVE_PIVOT`). These patterns are mutually exclusive.

**Context only:** current volume relative to 20 *prior* sessions, ATR14, ADR20
and hypothetical risk/ATR. Do not silently impose unvalidated volume,
liquidity, stop or opening-range thresholds from research experiments.

Upon manual confirmation, `TRIGGERED` stores the EOD session, rule
`EOD_CLOSE_CROSS_MANUAL_V1`, historical observed **closing price**, actual
human confirmation timestamp, observer and auditable evidence. It does not
invent an intraday trigger time, transaction price, order ID or fill.
The former WATCH cannot be confirmed twice or automatically reverted.

The 2026-10-23 NIQ/RBRK/RPD examples have historical `EOD_CROSS`, but their
human READY approval was on **October 24** New York time. They must show
a failed point-in-time approval check and cannot be manually backdated to
`TRIGGERED` for the October 23 trading session.

Historical win-rate/expectancy and parameter exploration continue separately
under Research Lab.

## One Trigger action with two automatically audited EOD subtypes (2026-10-25)

The web interface has **one** `CONFIRM_TRIGGER` action. Users do not choose
a subtype. The GitHub backend independently compares original adjusted
daily OHLCV with the saved pivot and checks point-in-time READY approval:

- **FIRST_EOD_CROSS / EOD_CLOSE_CROSS_MANUAL_V1:** previous daily close ≤
  Pivot and latest completed close > Pivot; READY was approved by
  **16:00 New York** on that latest EOD session.
- **POST_APPROVAL_HOLD / EOD_POST_APPROVAL_MANUAL_V1:** previous daily
  close > Pivot and latest completed close > Pivot; READY was approved
  by **16:00 New York** on that latest EOD session.

A preceding close cannot simultaneously be ≤ and > the pivot. Thus the
two types are **mutually exclusive**, and if neither pattern exists a
manual trigger cannot be submitted. `CONFIRM_TRIGGER` stores
`stage3_manual_action=CONFIRM_TRIGGER` and separately saves the server's
`eod_trigger_confirmation_type`, `trigger_rule`, actual EOD session,
observed closing price, READY approval timestamp and GitHub reviewer.
The prior two backend validator names are for regression compatibility
only; they are no longer public choices in the dashboard, gateway or
GitHub Actions workflow.

The snapshot remains EOD-only: no intraday event time, entry/fill price,
broker order or retroactive trading performance is implied. No
experimental volume multiplier is promoted into a mandatory production rule.

Example: Friday initial daily breakout, Saturday READY approval, Monday
EOD holding above pivot may be `CONFIRM_TRIGGER`ed as
`POST_APPROVAL_HOLD` **for Monday**, without backdating Friday's signal.
If Monday closes below the pivot, neither type applies.

## One inspectable Trigger with blocked-submission reasons (2026-10-25)

`CONFIRM_TRIGGER` is **selectable for inspection** even when checks fail,
but **submission is blocked** until all required checks pass. The modal
shows the automatically detected subtype, its relevant checklist, failed
reasons, current EOD session and READY approval timestamp. Unknown
EOD patterns are explicitly reported as ineligible.

The GitHub backend revalidates original adjusted daily bars, the
published same-session EOD fields and the approval timestamp. It will
reject stale submissions and cannot be bypassed by changing browser data.

The published 2026-10-23 NIQ/RBRK/RPD EOD cross precedes 2026-10-24 READY
approval, therefore the single Trigger cannot be confirmed for Friday.
A fresh, later completed EOD observation may qualify when approved by
that session's close and still above the saved pivot.

Selecting Trigger does not itself record a signal, order or trade. The
existing KEEP_WATCH, NO_TRADE and ARCHIVE actions are unchanged.

## Dual-visible / single-eligible Trigger UI (2026-10-25)

The owner clarified that both historical EOD confirmation **subtypes** should
remain visibly listed in the Stage 3 Action menu, but **no more than one may be
selectable for a given complete EOD session**:

- **TRIGGERED ① / FIRST_EOD_CROSS:** Prior close ≤ pivot, current close >
  pivot, EOD first-cross flags and all mandatory checks passing. Only this
  option is enabled; POST_APPROVAL_HOLD is disabled.
- **TRIGGERED ② / POST_APPROVAL_HOLD:** Prior close > pivot and current close
  > pivot, EOD hold flags and all mandatory checks passing. Only this option
  is enabled; FIRST_EOD_CROSS is disabled.
- **Neither qualifies:** Both choices are displayed but **disabled**.
  Separate expandable, read-only checklists remain accessible even when
  options are disabled; the user may still KEEP_WATCH, NO_TRADE or ARCHIVE.
- **Conflicting double-pass:** Both choices disabled and source must be
  reverified. Do not allow a user to resolve contradictory data arbitrarily.

The browser submits the **canonical backend action** `CONFIRM_TRIGGER` for
either selected user-facing subtype; the backend independently recalculates
and saves `eod_trigger_confirmation_type` and `trigger_rule` from verified
adjusted daily chart evidence. The user-facing selector is advisory: a
successful GitHub dispatch is queued, not confirmed, and a stale or forged
EOD submission is rejected. No automatic order or fill is implied.

### Second-round READY is retained after entering Stage 3

`Stage2[setup_id]` is the **source Setup record**, preserving the original
base/Pivot, dates, human review decisions and actual timestamp. The
Stage3 record is a separate child keyed by matching **symbol + setup_id**;
`READY` in Stage 2 and `WATCH` in Stage 3 is expected, not duplicate
screening or failure to promote. Deleting or hiding READY in persistence
would break the Stage3 validator's READY-parent integrity checks.

The dashboard now displays a virtual **Stage 3 progress** column beside
Stage2 status: `已進第三輪 · WATCH`, `已進第三輪 · TRIGGERED`, or the matching
child's other status. A Stage2 row with a matching child provides
`查看第三輪` navigation to that exact `setup_id` in Stage 3. An approved
READY without a child is explicitly labeled not yet in Stage3. Nothing is
copied, deleted, reapproved or automatically bought from this UI change.

At the last verified 2026-10-23 published EOD, NIQ, RBRK and RPD each have
Stage2 READY and Stage3 WATCH records linked by the same symbol/setup_id.
Their October 24 READY approval cannot retroactively authorize an October 23
Trigger, so both subtype choices are currently displayed but not enabled.
