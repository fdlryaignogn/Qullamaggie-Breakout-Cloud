# R-001 / Price In and signed normalization research design v0.3

Status: **EXPERIMENTAL SCHEMA ONLY — no calibrated scores, no model training, no change to preregistered R-001 event rules**.
Owner authorized continuing the discussion of scoring each predictor from -1 to +1 with + favoring upside and - against upside, while distinguishing fundamentals, earnings surprise and already-priced-in risk.

## Why this is not a single observed "percentage priced in"
The amount already reflected in price cannot be observed from price alone. Strong past EPS and sales may be fully anticipated. Genuine surprises require **dated consensus that existed BEFORE publication**, compatible GAAP / non-GAAP / split bases, a vendor's historical expectation vintages, and an event cutoff. Pre-announcement abnormal price movement, analyst revisions, relative valuation and previously observable market reactions are **proxies**, not direct measurements. When data are missing, the score is **null, never zero**.

Research references: Fink, *A Review of the Post-Earnings-Announcement Drift*, 2021 (https://doi.org/10.1016/j.jbef.2020.100446) and Zhang, *Analyst Responsiveness and the Post-Earnings-Announcement Drift*, 2008 (https://doi.org/10.1016/j.jacceco.2008.04.004). PEAD does not prove that a particular historic stock was underpriced; frictions/risk compensation and specification dependence are important.

## Three distinguishable families
1. **Fundamental strength F:** Sales YoY, EPS YoY and acceleration, ROIC, ROE, cash-flow quality. Values must be from published dates before the breakout; historical accounting basis comparability matters.
2. **Expectation surprise S:** Recorded consensus EPS/revenue vintage vs announced actual; numerator and accounting basis matched; forecast revision 30/90d; source and number of analysts.
3. **Priced-in headwind P:** Pre-report and pre-breakout market-relative run-ups, valuation premium vs dated peers, and earnings reaction observed before the breakout (never afterwards). A larger run-up can mean favorable momentum AND a headwind; sign **must be learned and validated** out of sample, not arbitrarily inverted.

No artificial composite weights or "future-upside score" are committed: F/S/P composites stay null until enough independent company cases and matched failing controls are available. No outcome-informed case switching or future announcements.

## Versioned machine contract
- \`site/data/r001_event_comparison_v0_3.json\` extends **v0.2** (v0.2 remains immutable history) from 73 to **111** fields across the original two **PROVISIONAL** AAPL events.
- 38 new fields: consensus, publication and reaction timestamps, surprise/revision/run-up/valuation raw proxies, 11 individual normalized scores, 3 proposed composite scores, vintage/fit status.
- Each field retains human Chinese/English name, stable \`key\`, type, group, semantic \`role\` and \`io_role: INPUT | OUTPUT | META\`. v0.3 has 74 INPUT, 7 OUTPUT, 30 META fields.
- Scores in both sample events are **null**; no valid 2005/2006 frozen historical analyst consensus, peer benchmark, or normalization reference cohort has been established.
- Score flags: \`normalization_status=UNCALIBRATED_NO_FROZEN_COHORT\`, \`expectation_data_status=MISSING_PIT_ANALYST_CONSENSUS\`, \`priced_in_identification_status=NOT_DIRECTLY_OBSERVABLE\`; \`ml_training_ready=false\`.
- Raw historical FMP OHLCV remains owner-held in private local browser IndexedDB/ZIP, NOT included in public JSON.

## Mathematical transform (a proposal, not a trained scoring model)

For an eligible raw numerical predictor x and feature-specific frozen reference statistics fit entirely on an earlier training period:

    z = (x - reference_median) / (2 * 1.4826 * reference_MAD)
    signed_norm = direction * tanh(z), direction in {-1, +1}

The scaling constant 2 and the robust-MAD method are **initial hyperparameters for later validation**, not an empirical discovery. Percentile/rank mapping can be compared in a future experiment, but rank also requires a dated reference distribution. Cross-section should generally be matched by era and industry, with cohort sample / symbol / calendar-quarter counts. **Do not calibrate using two overlapping AAPL events.**

\`research/r001/normalization_contract_v0_3.mjs\` rejects scores (returns null) without: finite raw value, finite median, MAD>0, sample count >=100, distinct company symbols >=30, historical quarters >=8, dataset role TRAIN, \`locked=true\`, \`direction=±1\`, documented polarity evidence ID, and training end/reference vintage/direction-lock **strictly before the target event**. These thresholds are minimum research safety parameters, not validated optimal values. Learned direction must come only from past training data; a fixed + for sales is a hypothesis, not guaranteed upside.

Explicitly distinguish:
- **Normalized INPUT** is an *as-of* feature candidate, not automatically a confirmed beneficial direction.
- **OUTPUT labels** (\`winner_252\`, future return) must not be normalized into X.
- **META** is identity, source, availability, calibration vintage, quality and eligibility; never quietly used as a predictive field.
- \`null\` means missing or uncalibrated, **not** market neutral 0.

## Point-in-time surprise rules
Sales surprise = 100*(actual_sales - consensus_sales)/consensus_sales, **only if** actual and consensus refer to identical period/currency and the dated consensus existed before publication; consensus_sales>0.

EPS surprise = 100*(actual_EPS - consensus_EPS) / max(abs(consensus_EPS), prelocked_reference_denominator_floor). Historical comparable reporting basis, share split, currency and GAAP/non-GAAP flags required. Small or negative consensus EPS is high variance and may warrant separate treatment.

Publication clock: where only YYYY-MM-DD is known, use strictly prior release day relative to breakout (\`release_date < event_date\`), not an assumed before-open announcement. Prior-earnings reaction can be a valid predictor **only if its observable price-reaction window ends before the breakout as-of cutoff**. Pre-breakout run-up must be benchmark-relative and dated. Revisions after earnings or breakout cannot be historical inputs.

## Research deliverables (native Google Sheets)
https://docs.google.com/spreadsheets/d/1HjClNJgZsxLPMYelzanZG0WFbZGn0RvZZVgIDzwk7vk/edit

Original six tabs stay intact and unchanged historical v0.2 values:
- \`Event_Compare\`: append 38 v0.3 schema rows; columns A:Name, B:Schema, C:IO Role, D/E:event metadata; null stays blank.
- \`Events_ML\`: append 38 additional schema-key columns to one-event-per-row machine data.
- \`Schema_Dictionary\`: append 38 bilingual rows.
- \`README\`: updated instructions and limitations.
Four additional tabs:
- \`Normalization_Spec\`: per-feature raw field, sign/polarity caveat, formula and status.
- \`Expectations_PIT\`: **header-only** raw consensus input template, no invented rows.
- \`Calibration_Register\`: **header-only** vintage-locked reference median/MAD/direction evidence, no fitted data.
- \`Normalized_ML\`: one event per row, \`norm__<numeric_raw_field>\` columns **blank** until validated training references exist.

Public webpage \`site/historical-superstocks-schema.html\` reads v0.3 metadata only, has bilingual filters (all/fundamental/expectation/price-in/normalized) and a cautionary note. The user's existing **two-date input** local daily chart and indexedDB browser cache are retained.

## Executed verification, as of 2026-10-27
- Google Sheets connector native metadata + bounded range readback confirms **10 tabs**, new 38 columns/rows, A/B/C/D/E role layout, all score values blank, normalized row layout and empty PIT template.
- Pure V8 execution of the **exact retrieved committed** module against exact committed JSON: **18 assertion checks PASS** (bounds, polarity inversion, missing input handling, training-sample guard, vintage exclusion, EPS basis mismatch, conservative release date, no OUTPUT leakage, no invented score, schema version/completeness). One hypothetical 3680-vs-3500 consensus **unit fixture** is not historical analyst consensus.
- Page HTML JavaScript parsing / bilingual translation inventory / two date inputs to be rechecked before PR merge.
- Node test runner file: \`research/r001/test_normalization_contract_v0_3.mjs\`. GUI deployment or live-browser IndexedDB not implied by static checks.
- v0.3 has **NO valid historical observed Price-In level or score**. Data-quality statuses remain provisional and R-001→B-001 gated.

## Next evidence acquisition
Find licensed point-in-time consensus vintages and earnings-release times for the 2005-10-11 and 2006-10-18 AAPL earnings, as well as point-in-time benchmark, peers, and controls (including delisted names). Verify EPS split/basis accounting before computing historical surprises. Then freeze raw and calibration datasets and test with *rolling out-of-sample* windows for predictive value, drawdowns and total transaction costs. Do not backfit sign on AAPL's known 2006/2007 winner labels.
