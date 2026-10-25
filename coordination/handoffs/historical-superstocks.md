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

## Research UI milestone — bilingual web schema viewer (2026-10-25)
- Owner authorized a human-readable schema table and daily chart with Traditional Chinese / English switch. This UI-only deliverable **merged to main** in [PR #27](https://github.com/fdlryaignogn/Qullamaggie-Breakout-Cloud/pull/27), merge SHA `78092fd38c277579aad9a487eec9ddd763add6e9`; source readback PASS, **live GitHub Pages not yet browser-verified**.
- Page: `site/historical-superstocks-schema.html`; linked from `site/research.html`. Reuses dashboard language key.
- Human-readable ML schema columns separate point-in-time observable inputs from forward outcomes/quality. Historic AAPL 2006 first-event vs 2007 later-success remains **provisional**; full case audit still pending in [PR #26](https://github.com/fdlryaignogn/Qullamaggie-Breakout-Cloud/pull/26).
- Daily candlesticks / volume / closing-line chart use **visitor's own local ZIP/CSV**; **no FMP raw OHLCV, API key or series bundled publicly** because ordinary FMP licenses do not allow public redistribution.
- Verification: JavaScript syntax PASS; CSV parser 5/5 cases PASS; independent headless Chromium DEFLATE-RAW audit ZIP compatibility PASS (51,527-byte decoded CSV); data-i18n keys 49/49 translated in both languages; no network-fetch, external scripts or embedded historical market-data series in HTML. GitHub Pages live browser test **NOT EXECUTED**.
- Research phase unchanged: 0 accepted cases, 0 controls; R-001->B-001 gate blocked. This viewer is a display tool, not research approval, ML training data or a change to production strategy.
