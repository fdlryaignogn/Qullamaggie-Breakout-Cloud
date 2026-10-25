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
