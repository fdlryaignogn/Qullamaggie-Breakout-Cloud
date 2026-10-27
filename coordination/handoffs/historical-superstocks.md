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

## R-001 signed normalization / Price-In research-schema v0.3 — 2026-10-27
- **Merged main:** [PR #30](https://github.com/fdlryaignogn/Qullamaggie-Breakout-Cloud/pull/30), merge SHA `b0519f065a0799783d33eaaf21d9355bfd4d17c5`. Github cloud scanner CI run 40452631793 SUCCESS; readback of main-branch v0.3 JSON and HTML script PASS. Native Google Sheets now 10 tabs and v0.3 renamed; live Pages URL not accessible to independent web checker, GUI not verified.
- Owner approved continuing -1..+1 input-feature design with a distinction between F (fundamental strength), S (surprise versus market expectation) and P (already-priced-in proxy/headwind). This is **research metadata**, not a prediction of percent priced in or production screening feature.
- Machine JSON `site/data/r001_event_comparison_v0_3.json` extends prior 73 fields to **111** (74 INPUT, 7 OUTPUT, 30 META). The 2 historical AAPL cases are unchanged and provisional; all consensus-dependent and 14 normalized/composite scores remain **null**, without any artificial scores.
- Pure normalization module, regression tests and method: `research/r001/normalization_contract_v0_3.mjs`, `research/r001/test_normalization_contract_v0_3.mjs`, `research/r001/price_in_normalization_v0_3.md`. Signed tanh score refuses absent vintage, direction, frozen historical cohort or missing raw data; no future labels as model X.
- Existing native Google Sheet was extended rather than replaced: `Event_Compare` +38 rows, `Events_ML` +38 columns, `Schema_Dictionary` +38 bilingual rows; extra tabs `Normalization_Spec`, `Expectations_PIT`, `Calibration_Register`, `Normalized_ML`. Browser webpage bilingual group filters added; local OHLCV cache and 2-date daily chart preserved.
- Main evidence gap: historical analyst consensus vintages (2005/2006), benchmark / peer PIT series and training controls. Without these, **NO observable Price-In percentage or trainable price-in model score**; research acceptance and R-001→B-001 gate unchanged.
- Tests as executed: native Google Sheet metadata / bounded readback PASS; pure V8 exact-module checks PASS for polarity, bounds, leakage and nullness. User web browser live verification still pending. This handoff is owner-directed continuation, NOT coordinator approval to start B-001.


## R-001 contemporaneous expectations, v0.4 evidence milestone (2026-10-28)
- Owner-approved Price-In research continued by locating historical **public pre-earnings** quotes instead of inventing consensus. Sources: dated Forbes 2005-10-07; MacDailyNews 2005-10-09; AppleInsider 2006-10-12; MacDailyNews quoting MarketWatch 2006-10-13; Macworld 2006-07-11 early estimate; retrospective reports retained but excluded from selection.
- **Provisional sales surprise:** FY2005Q4 pre-report quote 3,680 vs released 3,680 USD m => 0% (alternative earlier pre-report 3,720 => -1.0753%); FY2006Q4 4,670 vs preliminary released 4,840 USD m => +3.6403%. Conflicting forecast vintages and missing original analyst database timestamp explicitly flagged. EPS surprise remains null due special-tax/reporting/restatement basis.
- Owner-held FMP private ZIP close-to-next-session raw reactions -4.3478% Oct 2005 and +6.0150% Oct 2006, **not abnormal/market adjusted**, and October 2005 has the video iPod launch confounder. These observations are not causal Price-In proof.
- Schema v0.4: `site/data/r001_event_comparison_v0_4.json` (122 fields; 75 INPUT / 7 OUTPUT / 40 META), seven archived news quote observations; validator `research/r001/validate_contemporaneous_expectations_v0_4.mjs`, eight-case Node regression script, research explanation `research/r001/contemporaneous_expectations_v0_4.md`. Google Sheet 11 tabs includes new `PriceIn_Evidence` and expanded `Expectations_PIT`. Website bilingual price quote view and original two-date chart.
- **No normalized Price-In scores, accepted historical cases, delisted controls or active B-001.** Historical analyst original feed, benchmark abnormal returns, EPS GAAP basis and cross-company calibration still missing. Workflow awaits separate research acceptance and owner activation.
