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

Publication state: pending PR review/merge; do not claim live Pages verification from source checks.
