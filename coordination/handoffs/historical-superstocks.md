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

## Research daily-chart usability enhancement — 2026-10-25
- Owner reported needing to select a ZIP on every visit and not being able to inspect arbitrary days such as July 10. UI enhanced in `site/historical-superstocks-schema.html` and **merged to main** via [PR #28](https://github.com/fdlryaignogn/Qullamaggie-Breakout-Cloud/pull/28), merge SHA `b31f5d44d5c536235c9d8fec1f8c65aa9eaf87fb`: per-browser IndexedDB cache (automatic restore after one import), **Clear saved local OHLCV**, date picker, jump / previous / next trading day, zoom windows and custom-day OHLCV inspection; shared Chinese/English controls remain.
- Explicit distinction: 2006-01-06 first in-window selected event and 2007-01-10 later exploratory event retain their original provisional outcomes. **2006-07-10 / 2007-07-10 are just observation dates**, not reclassified breakouts. Weekend selection snaps to previous available trading day with notice.
- Data handling: FMP ZIP/CSV is imported to browser memory and IndexedDB on the current origin, NOT published to GitHub/Pages or synced across devices. User may clear it; site data deletion or private-browsing mode removes/prevents persistence. Same-origin site scripts can access origin storage; do not use shared computers for private datasets.
- Verification on exact source: inline JS syntax PASS; date navigation 5/5 PASS; locally stored OHLCV validator PASS (accept valid/reject reversed and invalid OHLC); IndexedDB open/write/read/queued-delete PASS with simulated event-driven store (not a real-browser persistence test); bilingual translation coverage 60/60; uploaded AAPL dates 2006-07-10 and 2007-07-10 parsed accurately. New live page/actual browser persistence still pending user/browser verification. Main-branch source readback and JavaScript syntax PASS; PR #28 scanner workflow run 40167222967 SUCCESS (not an end-to-end chart test).
- Trading strategy and research gates unchanged (R-001 provisional, B-001 waiting). Main handoff remains versioned; see `docs/r001_schema_web_viewer.md` and related PR.
 
## R-001 Event Compare v0.2 / fundamental feature & role schema — 2026-10-25
- **Merged to main:** [PR #29](https://github.com/fdlryaignogn/Qullamaggie-Breakout-Cloud/pull/29) merge SHA `a57fd1b7fc15e7ef00239b63f195303f72b729ed`. GitHub workflow **Verify cloud scanner** success, run 40183303937; main branch HTML and v0.2 JSON readback PASS. Live browser UX/rendering unverified.
- Owner specified only **start/end dates** for daily-chart controls, plus horizontal ML comparison with columns Name, Schema, **INPUT/OUTPUT/META**, then Event Dataset columns. Existing website change is scoped to research viewer, previously cached FMP bars remain device-local.
- Created verified native Google Sheet (6 tabs): https://docs.google.com/spreadsheets/d/1HjClNJgZsxLPMYelzanZG0WFbZGn0RvZZVgIDzwk7vk/edit . Canonical versioned machine JSON `site/data/r001_event_comparison_v0_2.json` has **73 fields / 2 provisional AAPL events / 8 as-of financial quarters**, no raw daily FMP history. New validator `research/r001/validate_event_comparison_v0_2.mjs`.
- PIT results from original 2005/2006 Apple announcements: latest Sales/EPS/GM as-of each event, sequential absolute rises and YoY-growth acceleration kept as distinct predictors; 2005 Q4 tax EPS item and 2006 Q4 preliminary restatement warning flagged. Historic ROIC/ROE/ROA/TTM cash flows remain **null**, pending original accounting/balance-sheet verification.
- I/O role assertions and release-date/acceleration adversarial tests PASS, Google Sheets readback PASS, source HTML syntax PASS, zh/en translations 45/45, date inputs exactly 2. Live Pages GUI / cross-device cache persistence **NOT VERIFIED**.
- AAPL case selection and provisional labels unchanged; research handoff R-001 not accepted and B-001 not activated.
