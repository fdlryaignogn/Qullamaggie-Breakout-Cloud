# R-001 tranche v0.1 — evidence and missingness audit
2026-10-25 | C-002 | status SOURCE DISCOVERY ONLY, **NOT an accepted validated tranche**.

| Candidate | Dated product/business source lead | Verified breakout date | Verified OHLCV | Historical cap | Winner label |
|---|---|---|---|---|---|
| MNST / historical HANS | 2003-03-31 FY2002 10-K index; 2005-03-16 FY2004 10-K index | MISSING | MISSING | MISSING | MISSING |
| NVDA | 1999-02-24 industry report; 1999 10-Q mirror filing date pending | MISSING | MISSING | MISSING | MISSING |
| AAPL | 2007-01-09 original iPhone release; 2007-07-25 earnings release | MISSING | MISSING | MISSING | MISSING |

Source URLs and precise claim limitations: evidence_manifest_v0_1.json. No numerical historical price/volume/market cap invented. 0/3 verified breakout cases, 0/3 validated price histories, 0 controls. Source publication dates must be checked against the *yet-to-be-determined* event date.

## Reproducibility and tests
Run `python research/r001/test_manifest_v0_1.py` from repo root. This checks candidate IDs, URL structure, event/price provenance guards, and publication cutoff leakage. It does **not** verify source truth or prove a successful breakout.

## Blockers
Acquire trustworthy daily OHLCV and split history for early MNST/HANS, NVDA and AAPL; establish actual historical shares outstanding, contemporaneous benchmark and listed/delisted control universe. Confirm original SEC filing accession/publication time. Data license constraints may prohibit raw series in GitHub.

## Coordinator decision requested
DEFER B-001 activation. First tranche has a reproducible protocol and dated source leads, but has not yet met the C-002 validated-tranche gate. Next step: source and verify at least one mechanically selected historical event and its as-of features.
