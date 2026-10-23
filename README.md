# Qullamaggie Breakout Cloud (V3)

Automated *end-of-day* US-stock breakout screening research dashboard. All rules are based on the three Project Skill documents, with explicitly configured thresholds; this is **not** official Qullamaggie software and **not** an execution or investment advice service.

### Deployment

- **Website:** https://fdlryaignogn.github.io/Qullamaggie-Breakout-Cloud/
- **Dashboard workflow:** `.github/workflows/publish-site.yml`, deployed via GitHub Pages.
- **Automated scanner:** `.github/workflows/daily-scan.yml`, scheduled on US weekdays at **18:30 America/New_York** (GitHub schedule may be delayed).
- **Code tests:** `.github/workflows/test.yml`, runs 27 Python tests in GitHub Actions.
- **Current launch status:** the dashboard and scanner *source code* are deployed; the **first successful real US-wide cloud scan has not been verified**. Until then the live `site/data/latest.json` is an empty `phase=pending` placeholder, **not a stock-picking signal**.

### Research logic

1. Momentum: calculate returns across 21/63/126 completed trading sessions, rank per period and take the **union** of the top 2% selections. Ranking is over successfully downloaded, eligible US-listed equities; the system must achieve >90% completeness to publish.
2. Setup: screen for possible pre-breakout patterns; keep existing developing setups under observation even if no longer ranked in Stage 1. A prior 63-session advance of 30% is a **reference threshold, not a hard official requirement**. `READY` requires human review.
3. Breakout: monitor only setups previously confirmed `READY`. Daily bars alone cannot confirm an intraday `TRIGGERED`; no orders are placed.

### Data quality, publication & limitations

The scanner uses Nasdaq Trader's Nasdaq/other-listed equity directories and Yahoo Finance via `yfinance`. These are **not** guaranteed complete/reliable data feeds. Yahoo rate limits can cause a scan to run slowly or fail. Failed/stale/partial scans **must not overwrite** the previously published stock list. The updater verifies US-universe scope, expected last completed NYSE session and coverage threshold before publishing.

The cloud site is deliberately **read-only**: edits made locally in Windows V2.7 (e.g. `READY`) are **not synchronized** to the public GitHub Pages view, and would require a private authenticated editing channel. Do not commit API keys, account balances, trade journals or other personal data into this **public** repository.

### Monitoring

Check the [GitHub Actions page](https://github.com/fdlryaignogn/Qullamaggie-Breakout-Cloud/actions) for scan/test/deployment outcomes. In case of a failed full-market scan, investigate the Actions logs; do not mistake the last published results for today's data. The website displays the last published date for this reason.

GitHub may deactivate scheduled workflows after prolonged repository inactivity or delay queued jobs. Scheduled scans run independently of whether your laptop is on.
