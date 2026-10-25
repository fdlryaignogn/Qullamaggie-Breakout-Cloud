# R-001 / AAPL — first in-window breakout case (audit v0.2)

Date: 2026-10-25 | Owner-approved research under C-001/C-002 | Status: **PROVISIONAL, NOT VALIDATED TRANCHE** | Source method: research/r001/methodology_v0_1.md

## FMP upload: provenance and quality
Owner-run Colab output r001_aapl_audit.zip from FMP stable historical-price-eod/full for AAPL, 2005-01-01..2009-12-31, retrieved 2026-10-25T04:36:24Z. Raw OHLCV CSV intentionally **not redistributed in public GitHub**. Source CSV SHA256: bdf7342a4e6f86b97fb320e0b353d6618016dd6de46ca0d2f4699d5aa7886985. 1,259 sessions 2005-01-03..2009-12-31, no duplicates, nulls, invalid candles or negative volumes. Session dates matched US XNYS equity calendar proxy 1,259/1,259 (not NASDAQ tick audit).

FMP says full EOD Close is stock-split-adjusted, unlike dividend-adjusted Adj Close (https://site.financialmodelingprep.com/developer/docs/stable/historical-price-eod-full). Apple confirms 2005-02-28 2:1, 2014-06-09 7:1, 2020-08-31 4:1 splits (https://investor.apple.com/faq/default.aspx). Full original trade-price/factor series missing. Yahoo historical excerpt 2006-01-06 confirms FMP rounded O 2.69 / H 2.74 / L 2.66 / C 2.72, but Yahoo volume 704,457,600 differs from FMP 704,558,208 (+100,608; approx 0.0143%). The first breakout clearance is only $0.01 with cent-rounded OHLC.

## Frozen event selection and forward outcome
v0.1: earliest event **in supplied window after 252 prior sessions** where close exceeds preceding 60-session high, bullish candle and prior 20-session mean price x volume >= USD 1m. Independently regenerated 75 candidates; 11 252-session winners, 37 nonwinners, 27 censored; overlapping candidates are not independent samples.

**Selected first in-window event: 2006-01-06** at adjusted open 2.69, high 2.74, low 2.66, close **2.72**, volume 704,558,208; prior high **2.71**; prior 20-session dollar turnover proxy **$1,543,581,642.036**. Left-censored by start 2005-01-03; it is NOT AAPL's first-ever historical breakout.

Following 63rd close (2006-04-07) 2.49 / -8.46%; 126th (2006-07-10) 1.96 / -27.94%; 252nd (2007-01-09) 3.31 / +21.69%; forward 252-session maximum close 3.31 / +21.69%, minimum close 1.81 (2006-07-14) / -33.46%. Preregistered doubling outcome **FALSE**. All forward results are descriptive; not trade P&L.

## Evidence PUBLIC before the event close (date-level PIT)
- 2005-06-06: announced planned Mac Intel CPU transition; not yet realized shipments: https://www.apple.com/newsroom/2005/06/06Apple-to-Use-Intel-Microprocessors-Beginning-in-2006/
- 2005-09-07: iPod nano announced: https://www.apple.com/newsroom/2005/09/07Apple-Introduces-iPod-nano/
- 2005-10-11: fiscal Q4 revenue **$3.68bn vs $2.35bn** a year prior (+56.6% calculated); iPod shipments **6.451m, +220% YoY**; Mac shipments **1.236m, +48% YoY**. Official Apple release https://www.apple.com/newsroom/2005/10/11Apple-Reports-Fourth-Quarter-Results/ and contemporaneous SEC filed exhibit https://www.sec.gov/Archives/edgar/data/320193/000110465905048094/a05-17462_1ex99d1.htm
- 2005-10-12: fifth-generation video-capable iPod announced: https://www.apple.com/newsroom/2005/10/12Apple-Unveils-the-New-iPod/
- 2005-12-01: FY2005 Apple Computer, Inc. 10-K filing publicly available. Reports **842,767,948** shares as of **2005-11-18** (stale vs event). Original https://www.sec.gov/Archives/edgar/data/320193/000110465905058421/a05-20674_110k.htm ; filing index https://investor.apple.com/investor-relations/sec-filings/default.aspx?language=en-US

Conditional capitalisation *estimate*, NOT actual 2006-01-06 cap: 2.72 x 7 x 4 = $76.16 2006 nominal price (assuming correct split-only history) x stale 842,767,948 shares = **$64.19bn**. Confirm contemporaneous shares and factor ledger before verified cap. Publication clock times not documented, so next-session eligibility rule recommended.

**Lookahead guard:** 2007-01-09 iPhone announcement is AFTER 2006 breakout; iPhone and subsequent sales MUST NOT be used as pre-event features even though iPhone announcement falls on the final forward observation date.

## Quality/tests/limits
Audited owner ZIP SHA256, strict OHLC/date checks, formula regeneration and all 75 labels. Local tests: 5/5 passed for recomputation and checksum, corrupted candles, altered candidates and forward-label detection; py_compile PASS. XNYS date-calendar proxy PASS. GitHub CI unexecuted; owner ZIP not committed. Remaining: provider split+volume ledger, high-precision rounding check, original historical shares at breakout, S&P500 benchmark, precise filing acceptance times, point-in-time matched listed/delisted failed-breakout controls (quarter/sector/cap, deterministic seed 1001). No survivorship-free inference.

C-002 gate **NOT READY**; B-001 not activated. Review this negative first-in-window event before authorizing further research; do not retroactively choose a 2007 winner.


## Extra event in the *preregistered all-candidates* inventory — NOT the selected event
The frozen method records **all** qualifying candidates for sensitivity, but selects the **earliest** one for the case. One later candidate on **2007-01-10** has open 3.38 / high 3.49 / low 3.34 / close **3.46**, versus prior 60 high **3.33**. In the following 252 sessions (to 2008-01-10) its maximum close is **7.14** on 2007-12-28 (**+106.36%**), with first double achieved 2007-12-07 and horizon-end close **6.36** (**+83.82%**). This later candidate has a **TRUE** descriptive 252-session doubling label; **it must not replace the first selected 2006-01-06 FALSE case**. Apple's 2007-01-09 iPhone announcement precedes the Jan-10 candidate, unlike the Jan-06-2006 case, but this comparison is merely descriptive; within-stock overlapping windows and retrospective company selection prevent causal or predictive conclusions. Source: user's archived FMP AAPL CSV, SHA256 recorded above; Jan09 Apple announcement https://www.apple.com/uk/newsroom/2007/01/09Apple-Reinvents-the-Phone-with-iPhone/.
