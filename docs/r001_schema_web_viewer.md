# R-001 bilingual historical-superstocks schema web viewer

Scope: research UI only, owner request 2026-10-25. No production screening change, model training or B-001 activation.

## Files and navigation
- `site/historical-superstocks-schema.html`: Traditional Chinese / English schema table, 2005-dated AAPL evidence, 2006 selected and 2007 exploratory event labels, and private user-loaded AAPL **daily candlestick/close-line chart** with daily volume.
- `site/research.html`: Research Lab navigation link to schema viewer; switches the link label with the existing website's `qulla_breakout_dashboard_language` language preference.
- HTML is self-contained: no external JS frameworks, no API keys, no tracking requests, no back-end storage.

## Chart loading (privacy/licensing)
FMP's published terms restrict public data display and redistribution without a specific agreement:
https://site.financialmodelingprep.com/terms-of-service
https://site.financialmodelingprep.com/insights/platform/can-you-use-fmp-data-in-a-public-app-website-or-client-dashboard

**Do not commit FMP OHLCV or render a public price-history data dump.**
This page deliberately ships **without a historical price series**. The visitor must select their own `r001_aapl_audit.zip` (Colab output) or `aapl_fmp_2005_2009_ohlcv.csv`. Client-side `File` + `DecompressionStream("deflate-raw")` decodes Python ZIP deflate data when supported; users whose browsers lack support can extract the CSV locally and select it instead. Data remains in the page's JavaScript memory; it is not saved to localStorage or uploaded.

The point-in-time case dates and high-level **provisional labels** come from R-001 audit PR #26 and remain open to further review. Direct FMP price values, volume history and full daily candles are derived *locally* when the visitor selects their source archive. The page does not independently validate adjustment provenance or reproduce the source checksum; the Python audit in PR #26 does that with the original ZIP.

## Language
- Selector `繁中 / EN`, accessible `aria-pressed`, switches title, table headings, schema descriptions, product evidence, messages, chart labels, first/second event choices and training explanatory notes.
- Shares the existing Research Lab and Trading Dashboard preference `qulla_breakout_dashboard_language`, with a safe zh default when localStorage unavailable, and listens to storage changes from other tabs.
- Data column codes and numeric historical event identifiers remain language-neutral.

## Provenance / correctness guardrails
- Case `R001-AAPL-01` and selected event 2006-01-06; later 2007-01-10 remains a **non-selected** sensitivity case. Do not select the successful later event because of the outcome.
- iPhone announcement in January 2007 is NOT a 2006 pre-event feature.
- On client data import, validates ascending unique dates, required OHLCV columns and positive/OHLC-consistent candles.
- Visual window: 120 sessions preceding selected event and up to 252 after it. Future doubling computed from the *252 subsequent trading sessions* only if the full horizon exists; otherwise CENSORED. Values are descriptive and **not** executable return/trade P&L.
- This is a **human viewer** for an example schema; not a standardized production ML dataset. Controls, point-in-time delisted universe, full split-ledger, and comparable features remain to be collected separately.

## Verification record (2026-10-25)
- GitHub connector readback: new page parsed as syntactically valid JavaScript using `new Function` — PASS.
- Static invariants: shared language key, two distinct language controls, private ZIP/CSV import, no FMP API key or embedded raw historical OHLCV, and Research Lab link translated — PASS.
- Five JavaScript CSV-parser tests: valid fixture accepted; bad OHLC, duplicate date, negative volume and missing column rejected — 5/5 PASS.
- Chromium headless independent ZIP central-directory / DEFLATE-RAW compatibility test with owner's uploaded `r001_aapl_audit.zip`: decompresses `aapl_fmp_2005_2009_ohlcv.csv` to exactly **51,527 bytes** — PASS.
- **Not verified:** interactive rendering on GitHub Pages or cross-browser Safari/Firefox behaviour. No CI workflow added; data-source verification remains documented in PR #26.

## Browser review checklist
1. Open Research Lab; click **歷史飆股 Schema**.
2. Toggle 繁中 → EN → 繁中, confirm headings, table, evidence and chart picker translate; navigate to Research Lab and back and confirm preference persists.
3. Select the owner-held ZIP and confirm AAPL daily candlestick plus volume and the 2006 marker appear.
4. Switch to 2007 event; confirm the marker moves and the later result is explicitly **not** the selected initial event.
5. Switch to daily closing-line view; confirm chart changes without sending a network request.
6. Open in a clean browser session; absent a local ZIP/CSV, chart must show a truthful **waiting for local data** state, not fabricated historical candles.
7. Inspect requests/storage to ensure user price series never goes to server.

Publication state: PR #27 merged to main; live Pages browser checks remain user acceptance work.

## Owner-requested daily chart usability update — 2026-10-25

Reason: Previously users had to reselect the FMP ZIP on **every visit** and could only jump between two recorded breakout events. This is now a practical historical **date browser**, separate from the frozen research event selector.

### New controls
- Import the owner-held `r001_aapl_audit.zip` or extracted CSV **once per browser/site origin**. Validated OHLCV bars are stored in **IndexedDB** under `qulla_r001_private_ohlcv_v1` / `series` / `R001-AAPL-01:2005-2009` and restored on later visits. The source ZIP is not placed on a server and no raw FMP bars are committed to GitHub.
- `Clear saved local OHLCV` explicitly deletes that IndexedDB entry and removes the locally stored focused date. Browser site-data clearing, private browsing or a different device/browser also remove/prevent the saved copy. Data is not synchronized across devices.
- Choose any available session via **Inspect date** (`input[type=date]`), **Go to date**, or **previous/next session**. A weekend/market holiday snaps to the nearest earlier available session with a visible notice; outside sample dates are clamped to its bounds. Example dates: 2006-07-10 and 2007-07-10 (distinct years).
- View 60, 120, 252-session centered windows or the original 120-before/252-after research-event view; switch between OHLC candlesticks/volume and closing-line display.
- Arbitrary-date mode shows the day’s **O/H/L/C/Volume**, not a breakout label or speculative winner outcome. Only the original selected 2006-01-06 and **non-selected** 2007-01-10 research presets show the descriptive future-doubling outcome. This avoids reclassifying arbitrary observation dates as newly validated signals.
- Existing zh-Hant / en translation and shared language preference persist. The last focused calendar date is in `localStorage` separately from the OHLCV bars.

### Security and implementation constraints
- Market data stays client-side **in browser IndexedDB**. Other scripts on the same website origin can technically access the browser’s IndexedDB, so users should not import licensed series in shared/public browsers. No external upload, API key, network fetch or public price history was added.
- Cache reads revalidate ascending dates and OHLC consistency; parse/write/delete errors do not falsely imply persistence. A failed replacement import preserves the last valid on-screen data. Mutations are serialized so `Clear` cannot be undone by a pending write.
- A new dataset or browser/device must still be imported once; this is **not** a cloud-synchronized OHLCV feed.

### Verification
- GitHub readback of updated HTML: JavaScript syntax parsed successfully; full `data-i18n` coverage **60/60** in both languages.
- Extracted production `readCSV` re-parsed 2006-07-10 and 2007-07-10 test fixtures: PASS.
- Extracted production `chooseDate` function: exact date, nearest preceding session for non-trading day, year switch, before/after-range clamp: 5/5 PASS.
- Extracted production `validateStoredBars`: valid data accepted, reversed dates and invalid OHLC rejected: PASS.
- Extracted production IndexedDB routines with a simulated event-driven store: open/upgrade, save, reload, serialized write-then-delete: PASS. **This is a mock, not a verified end-to-end browser persistence test.**
- Chromium GUI / GitHub Pages live rendering, actual IndexedDB on the user’s browser and private-mode behavior: **NOT YET independently verified**. The user should test after publication, and share any issues for fixes.

No strategy, labels, OHLC adjustment contract or R-001->B-001 approval changed.
 
## Version 0.2 — two-date daily chart + machine-ready side-by-side event comparison (2026-10-25)

Owner requirements: **only two date fields** for historical chart inspection (start and end); human-readable comparison grid with **A=Name, B=Schema, C=INPUT/OUTPUT/META role, D..=historical event values**. Old event-selection/dropdown and step-navigation UI removed. The previously implemented IndexedDB owner-owned OHLCV local cache is retained; the historical data are not redistributed on GitHub Pages. A date range filters local daily candles; two pre-registered event markers are displayed if they fall inside that range, but arbitrary dates do not become new research signals.

Canonical **public metadata only** artifact: `site/data/r001_event_comparison_v0_2.json`. V0.1 is preserved as history. The bilingual webpage fetches v0.2 for the matrix (no raw FMP bars); users can open the separately verified native Google Sheets document:
https://docs.google.com/spreadsheets/d/1HjClNJgZsxLPMYelzanZG0WFbZGn0RvZZVgIDzwk7vk/edit

The Sheet contains:
- `Event_Compare`: **73 schema features/metadata/labels**, first columns Name, Schema, I/O Role, followed by 2006 selected and 2007 non-selected AAPL events.
- `Events_ML`: machine-friendly one row per event and stable schema keys as the first row; blank = null, **not zero**.
- `Schema_Dictionary`: types, semantic role plus I/O role.
- `Financials_PIT`: eight actually released fiscal quarters (FY2005 Q1–Q4; FY2006 Q1–Q4) with release date, period end, published sales, EPS, growth and official Apple press-release URL.
- `Evidence_PIT`: event-tagged product evidence plus dated financial releases; `README`: formulas/limitations.

**Role separation:** `INPUT` is a *candidate* observable predictor at the time of event; `OUTPUT` is a future-determined label and MUST NEVER feed the model's X; `META` joins, dates, sources, missingness, quality and eligibility, not X/y. The JSON preserves `role` as well as strict `io_role` and can be checked by `research/r001/validate_event_comparison_v0_2.mjs`.

**Financial methodology:** The newest publicly released quarter is FY2005-Q4 (published 2005-10-11) at 2006-01-06, and FY2006-Q4 (published 2006-10-18) at 2007-01-10. Data published after an event are explicitly excluded even where the financial period ended before it. Sales/earnings *amounts* rising for 3 reported quarters is **not the same feature** as 3 quarters of rising sales/earnings *YoY growth rates*. The dataset calculates both as separate Boolean features, latest YoY rates, q0-vs-q1 acceleration (percentage points), and q0..q3 reported quarter observations. EPS by-quarter nominal reported figures require split-aware care, especially FY2005 Q1 pre-2005-02-28 2-for-1 split. 2005 Q4 EPS benefited from tax items; 2006 Q4 was preliminary and could be restated. No retroactive later statement leaks back. `ROIC`, `ROE`, `ROA`, TTM CFO/FCF fields exist as **null** until audited contemporaneous underlying accounts and definitions are available. Do not invent ROI or treat missing as zero.

**Source links:** eight per-quarter Apple press releases are embedded in `Financials_PIT` and JSON. Financial figures shown are historical reported values or transparent computations therefrom, not a later revised financial service's series.

**Validation (as-executed):** native Google Sheets metadata and bounded range readback confirms 6 tabs including correct A/B/C/D/E header and multiple input/output/metadata rows; exact committed JSON 73 fields / 2 events / 8 fiscal quarters. Repo's `validate_event_comparison_v0_2.mjs` function executed on fetched content: PASS, with three intentionally corrupt data variants rejected (wrong I/O role, wrong release date, wrong growth acceleration). HTML inline JS parsing PASS; 45/45 translatable UI keys available in each language; **exactly 2** date input elements. Browser Pages full UI and actual browser IndexedDB persistence remain **NOT VERIFIED**; user should check after merge. No A/B/C strategy changes, no production model training; B-001 remains gated.

## v0.3 — price-in normalized [-1,+1] research features (2026-10-27)

The bilingual page now consumes `site/data/r001_event_comparison_v0_3.json`, retains **only two chart dates** and browser-private user OHLCV, and offers a table-group filter for fundamental, expectations, priced-in and normalized metrics. It explicitly warns that no historic consensus/normalization cohort is available: `null` = unknown, never score zero.

Canonical design: `research/r001/price_in_normalization_v0_3.md`; implementation/QA `research/r001/normalization_contract_v0_3.mjs` and `research/r001/test_normalization_contract_v0_3.mjs`. The v0.3 metadata-only dataset extends 73 to 111 fields (74 INPUT / 7 OUTPUT / 30 META), keeps both AAPL events PROVISIONAL, and stores all 14 normalized/composite slots as null. No FMP daily bars, API secret or vendor consensus snapshots are published. Robust MAD scaling is a **draft parameterization**, not a validated alpha signal. Directional polarity and training-cohort calibration are mandatory; future-determined labels never become X.

Google Sheet with the same ID: https://docs.google.com/spreadsheets/d/1HjClNJgZsxLPMYelzanZG0WFbZGn0RvZZVgIDzwk7vk/edit — native tabs now include the original six plus `Normalization_Spec`, `Expectations_PIT` (header only), `Calibration_Register` (header only), and `Normalized_ML` (null scores).

Validation: Google Sheets metadata and bounded cell readback PASS; exact module V8 in-process checks PASS for sign, bounded outputs, null on missing calibration, time leakage, OUTPUT guard and historical missingness; HTML script syntax and localization validated before PR review. GitHub Pages runtime/IndexedDB continue to need independent browser acceptance.
