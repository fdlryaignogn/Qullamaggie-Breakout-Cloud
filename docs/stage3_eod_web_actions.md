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
| CONFIRM_EOD_TRIGGER | WATCH → TRIGGERED | Human confirms validated EOD close-cross **after** all mandatory conditions pass; terminal for this setup, **not an order or fill** |
| CONFIRM_POST_APPROVAL | WATCH → TRIGGERED | Human confirms a **later** completed EOD holds above approved pivot after READY; distinct from first breakout; no order/fill |

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
volume and risk context. The `CONFIRM_EOD_TRIGGER` option is disabled when
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
6. The previous daily close was at/below pivot and the just-completed
   daily close is strictly above it (`EOD_CROSS`).

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

## Two independent EOD confirmations (owner-approved, 2026-10-25)

The user may manually choose one of two `WATCH -> TRIGGERED` paths:

- `CONFIRM_EOD_TRIGGER` / `FIRST_EOD_CROSS`: approved READY **by 16:00 New York on the current completed session**, previous EOD close at/below saved pivot, latest EOD close above pivot (`EOD_CROSS`). The signal is not a fill.
- `CONFIRM_POST_APPROVAL` / `POST_APPROVAL_HOLD`: READY was approved **by the latest completed session's 16:00 New York close**, and the latest EOD close **and preceding EOD close** are both above the saved pivot (`ABOVE_PIVOT`). This is explicitly a **later post-approval confirmation**, never the original breakout and never a retroactive entry.

Both are separately shown in the web Action select. Each has its own visible pass/fail checklist and GitHub independently recalculates it from the original same-session adjusted daily chart plus approval timestamp. The post-approval path has no minimum number of holding days, entry-price inference, fixed RVOL multiplier, or live order submission.

Example: Friday initial EOD breakout, Saturday READY approval, Monday EOD still above pivot -> Monday `CONFIRM_POST_APPROVAL` may be manually confirmed. Friday's breakout itself remains ineligible. Saturday READY + Friday snapshot alone never qualifies. A Monday READY approved after **16:00 New York** cannot confirm Monday EOD; the next completed session must be assessed.

Data persisted on human confirmation includes `trigger_rule` (distinct mode), `eod_trigger_confirmation_type`, original READY approval timestamp, *latest* as-of date and close, actor and audit history. No intraday `trigger_time`, simulated fill, broker order or auto-trigger is created.

This is a user-approved operational distinction between the timing of EOD observation and subsequent manual confirmation, not a Research Lab performance claim or auto-promoted experimental strategy filter.

## Visible but not actionable Trigger checks (2026-10-25)

Both `CONFIRM_EOD_TRIGGER` and `CONFIRM_POST_APPROVAL` remain **selectable in the
Action menu**, even when their requirements are unmet. Selecting either action
shows the independent mandatory checklist, EOD as-of session, and the READY
approval timestamp with the failed requirements clearly described. This is a
**diagnostic selection only**; the GitHub submission button is disabled for a
non-qualifying Trigger, and the server again refuses any bypass attempts.

The published 2026-10-23 sample demonstrates why this is necessary: NIQ,
RBRK and RPD had a fresh daily `EOD_CROSS` that Friday but READY approval
was given on Saturday 2026-10-24. First cross fails the pre-close approval
gate. Post-approval hold fails the pre-close approval gate **and** requires a
new completed EOD with both closes above the pivot. The next possible EOD
session is Monday 2026-10-26, subject to a successful scan and price behavior.

A disabled **submit** action must never be interpreted as an actual accepted
trigger, order, or trade; ordinary KEEP_WATCH, NO_TRADE, ARCHIVE workflows
remain available to authenticated human reviewers.
