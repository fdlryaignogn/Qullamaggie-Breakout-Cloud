# Historical Superstocks — Handoff Summary (2026-10-25)

## Current Status
- R-001 active under C-001 / C-002; C-003 is the handoff format.
- First *single-case demonstrator* AAPL 2005–2009 audited from owner-run FMP ZIP, **PROVISIONAL; no accepted validated tranche**.
- MNST and NVDA not started. B-001 remains gated; P-001 deferred. Owner review requested, not next-phase activation.

## Completed Work
- Pre-registered method v0.1 kept unchanged.
- Owner FMP upload: 1,259 valid AAPL daily bars 2005-01-03..2009-12-31; 75 candidate dates independently recomputed; first observed in-sample after 252-day warmup = **2006-01-06**, split-adjusted close 2.72 vs preceding 60-session high 2.71.
- First candidate subsequent 252-session maximum close gain +21.69%, minimum close change -33.46%; preregistered twofold winner **FALSE**; sample is left-truncated, not first-ever company breakout.
- Source-dated *pre-event* product and fundamentals: Intel transition, iPod nano/video iPod, 2005 Q4 $3.68bn vs $2.35bn revenue, 6.451m iPods, 2005 Nov18 shares from Dec01 10-K. **2007 iPhone was NOT known in 2006**.
- Reproducible audit CLI, regression tests, event JSON and source/quality report committed on scoped research branch. No raw FMP OHLCV files distributed in public GitHub; owner holds input ZIP.

## Key Decisions
- C-001/C-002: first chronological candidate under fixed definition; no outcome-informed event substitution and no strategy changes.
- C-003: own handoff document updated at meaningful research milestone.
- The project must NOT count this as validated historical winner or activate B-001; controls/price precision and split provenance remain required.

## GitHub References
- `research/r001/methodology_v0_1.md`
- `research/r001/aapl_case_audit_v0_2.md`
- `research/r001/aapl_case_summary_v0_2.json`
- `research/r001/audit_aapl_zip_v0_2.py`
- `research/r001/test_audit_aapl_zip_v0_2.py`
- PR branch `research/r001-aapl-fmp-audit-20261025`; project state `PROJECT_STATE.json`.
- Owner-held input source CSV SHA256 `bdf7342a4e6f86b97fb320e0b353d6618016dd6de46ca0d2f4699d5aa7886985`.

## Tests & Blockers
- Python CLI on owner upload PASS. Five unit tests PASS (positive case plus four tamper tests). `py_compile` PASS. 1,259 session dates agree with US XNYS market-calendar proxy, zero missing/extra.
- Yahoo sample confirms Jan06 2006 OHLC rounded but volume differs ~0.0143%; FMP price history is split-adjusted, original split adjustment factor series not independently fetched. Cent rounding makes $0.01 clearance near boundary.
- No full pre-2005 price history, verified contemporaneous capitalization, S&P500 benchmark, listed/delisted controls or multi-name historical hypothesis test. Repo CI not run; replay requires private owner ZIP.

## Next Actions
- Owner reviews the *negative* first-in-window AAPL example.
- If authorized: independently verify split ledger/high precision historical prices and historical control coverage, without changing preregistered rule post hoc.
- Coordinator can inspect this provisional audit but **R-001 -> B-001 gate not met**; separate owner approval required to activate B-001.
