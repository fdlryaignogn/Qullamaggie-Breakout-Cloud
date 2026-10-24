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

These are manual **EOD management actions**, not buy/sell, triggers or fills.
Both terminal options require an explicit checkbox and a 1–500 character public
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
