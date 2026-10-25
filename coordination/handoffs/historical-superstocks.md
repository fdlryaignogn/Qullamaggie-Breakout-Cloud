# Historical Superstocks — Handoff Summary

## Current Status
- As of: 2026-10-25
- Active: R-001 under C-002; first tranche source discovery, **not validated**.
- Proposed first cases: MNST, NVDA, AAPL; verified cases: **0**.

## Completed Work
- Initial source-discovery protocol, evidence manifest, quality report and test script committed.
- No historical case or control is verified yet.

## Key Decisions
- C-001 research-first sequencing; C-002 first-tranche authorization.
- Preserve point-in-time provenance and non-winner controls. B-001 waits for accepted tranche and owner activation.

## GitHub References
- `research/r001/methodology_v0_1.md`
- `research/r001/evidence_manifest_v0_1.json`
- `research/r001/quality_report_v0_1.md`
- `research/r001/test_manifest_v0_1.py`
- `PROJECT_STATE.json`; `coordination/C-002-first-tranche-dual-source.md`

## Tests & Blockers
- Project state: local analogous structural smoke and py_compile passed; committed GitHub script **not run in CI**; no historical outcome test.
- Missing: PIT OHLCV and corporate-action provenance, historical share counts/delisted universe, actual qualifying dates and controls.

## Next Actions
- Verify historical OHLCV sources and event definitions; gather filing dates and control feasibility.
- Publish first audited evidence tranche, tests, and GitHub references; request coordinator acceptance before B-001 activation.
