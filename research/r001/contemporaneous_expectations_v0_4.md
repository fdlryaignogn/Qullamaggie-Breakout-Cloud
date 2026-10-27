# R-001 / Contemporaneous public analyst estimates evidence v0.4 (2026-10-28)

**Status:** Research-only, PROVISIONAL, *not* a validated direct observation of the fraction already priced into AAPL. No production screening, no B-001 activation, no normalized Price-In model.

## Point-in-time design
- Source set is dated, **pre-release contemporary news** citing analyst consensus, **not** independently retrieved Thomson/First Call or Reuters historical vendor snapshots. Article publication date is known to day precision; vendor snapshot UTC and analyst count remain **null**. Do not synthesize a time from the publisher's web-display clock.
- Match each news quote to fiscal quarter (not calendar quarter), the actual Apple earnings press release and a later R-001 breakout event. Only quotes with `article_public_date < earnings_public_date < breakout_event_date` can be selected, in absence of release-time proof.
- Strictly preserve alternate earlier pre-release quotes and later after-release retrospective claims. The best pre-release quote may conflict with subsequent vendor-retrospective narratives; **do not replace the original source based on its agreement with realized future price returns**.
- EPS quoted consensus (0.36/0.37 in FY2005 Q4; 0.50/0.52 in FY2006 Q4) is **META, not a matched predictor**. Apple reported $0.50 FY2005 Q4 diluted EPS including $0.12 tax-related benefit, and $0.62 FY2006 Q4 **preliminary** diluted EPS subject to historical options-grant restatement. Analyst coverage GAAP/non-GAAP comparability has not been independently checked; `eps_surprise_pct=null`.
- Revenue expected and actual are both USD millions and comparable by fiscal quarter; compute **provisional** `sales_surprise_pct` from 100 * (actual - quoted consensus)/quoted consensus. Do not normalize it or claim that surprise explains future equity price on its own.

## Original source register
| Quote report date | Quarter | Sales consensus USD m | EPS quote | Classification | Source |
|---|---|---:|---:|---|---|
| 2005-10-07 | FY2005 Q4 | 3,720 | $0.37 | pre-release alternate; Forbes article lists subsequent update | https://www.forbes.com/2005/10/07/apple-earnings-ipod-nano-1007markets01.html |
| 2005-10-09 | FY2005 Q4 | 3,680 | $0.36 | **selected nearest dated pre-release news quote**; vendor-vintage unverified | https://macdailynews.com/2005/10/09/anticipation_excruciating_as_the_perfect_apple_storm_looms/ |
| 2005-10-11 | FY2005 Q4 | 3,740 | $0.36 (also discusses $0.37 adjusted benchmark) | after-release retrospective; **ineligible** | https://macdailynews.com/2005/10/11/apple_q4_05_earnings_report_best_quarter_best_year_in_company_history/ |
| 2006-07-11 | FY2006 Q4 | 4,970 | $0.52 | pre-release early news quote; quarter ending misdated in article; no automated estimate-revision conclusion | https://www.macworld.com/article/180722/stock-11.html |
| 2006-10-12 | FY2006 Q4 | 4,670 | $0.50 | pre-release corroborating quote | https://appleinsider.com/articles/06/10/12/apple_expected_to_beat_wall_streets_q4_estimates.html |
| 2006-10-13 | FY2006 Q4 | 4,670 | $0.50 | **selected nearest dated pre-release quote**, corroborated October 12 | https://macdailynews.com/2006/10/13/apple_expected_to_post_higher_profit_27_sales_growth/ |
| 2006-10-18 | FY2006 Q4 | 4,670 | $0.51 | after-release retrospective; **ineligible** | https://macdailynews.com/2006/10/18/apple_q4_earnings_results/ |

Actual primary releases:
- FY2005 Q4: published 2005-10-11, $3,680m revenue, $0.50 reported EPS including $0.12 special tax benefit. https://www.apple.com/newsroom/2005/10/11Apple-Reports-Fourth-Quarter-Results/
- FY2006 Q4: published 2006-10-18, $4,840m revenue, $0.62 **preliminary** diluted EPS. https://www.apple.com/newsroom/2006/10/18Apple-Reports-Preliminary-Fourth-Quarter-Results/

**Selected provisional sales surprises:**
- As of **2006-01-06** AAPL first in-window event, FY2005Q4: $3,680m vs $3,680m dated 2005-10-09; `0.00000000%`. If instead using earlier 2005-10-07 Forbes snapshot, `-1.07526882%`; this variation is explicitly preserved. Revenue growth can be very large even without an upside surprise.
- As of **2007-01-10** AAPL later sensitivity event, FY2006Q4: $4,840m vs $4,670m dated 2006-10-13; `+3.64025696%`. EPS surprise remains null, not the naïve (($0.62/$0.50)-1)*100, because basis and preliminary results require separate verification.

## Price-response diagnostic from owner-private historical data
Private user-uploaded `r001_aapl_audit.zip` / `aapl_fmp_2005_2009_ohlcv.csv`, exact source CSV SHA256:
`bdf7342a4e6f86b97fb320e0b353d6618016dd6de46ca0d2f4699d5aa7886985`.

- **FY2005Q4:** after-close Oct 11, 2005 earnings day close $1.84 to next-session Oct 12 close $1.76 in the owner's split-adjusted two-decimal CSV: `-4.34782609%`. **Video iPod launch on Oct 12** is a major simultaneous new-information confounder.
- **FY2006Q4:** Oct 18, 2006 close $2.66 to next-session Oct 19 close $2.82: `+6.01503759%`. Announced results were preliminary and past option awards required possible restatements.
- These are **raw closing returns from a rounded adjusted-vendor source**, not abnormal/index-adjusted price effects, nor live trade returns. Do not infer any causal earnings announcement premium or a Price In percentage.

## Durable files
- `site/data/r001_event_comparison_v0_4.json` — versioned public **metadata-only** register. v0.3 is preserved. 122 fields = **75 INPUT + 7 OUTPUT + 40 META** for two provisional AAPL research events, and seven contemporary quote observations. No full FMP bars or analyst-vendor database exported.
- `research/r001/validate_contemporaneous_expectations_v0_4.mjs` + `research/r001/test_contemporaneous_expectations_v0_4.mjs` — reproducible PIT, evidence/conflict, calc, and no-fake-score assertions.
- [Native Google Sheet](https://docs.google.com/spreadsheets/d/1HjClNJgZsxLPMYelzanZG0WFbZGn0RvZZVgIDzwk7vk/edit): 11 tabs. Existing `Event_Compare` retains Name | Schema | INPUT/OUTPUT/META | two events, with 11 new rows; `Events_ML` adds 11 machine columns; `Schema_Dictionary` adds bilingual types and roles; `Expectations_PIT` contains 14 line items (seven news quotes, separate revenue/EPS basis); new `PriceIn_Evidence` has one row per case. `README` documents calculations, confounders and model gating.
- `site/historical-superstocks-schema.html` bilingual table loads v0.4 and displays a concise source-linked pre-release expectation comparison; its **two date inputs** and browser-local OHLCV cache are unchanged.

## Validation status and next gate
Executed on exact fetched GitHub source in V8: `validatePreReleaseEvidence` PASS plus adversarial detection of future quote, post-release selection, fictional vendor clock, corrupted sales surprise, non-comparable EPS surprise, invented normalized score, and late/corrupted reaction. Google Sheets metadata and bounded readback: PASS, including native formulas and 11 tabs. Standalone eight-case Node test runner committed; actual Node CI execution and GitHub Pages GUI remain independently unverified unless subsequently checked.

**Remaining before Price In scoring:** Historical data-vendor snapshot and analyst-count verification, consensus adjustment/currency/accounting consistency, dated market/peer index and abnormal returns, contemporaneous universe including delisted controls, externally validated normalization/calibration on non-overlapping training stock events. B-001 gate remains blocked.
