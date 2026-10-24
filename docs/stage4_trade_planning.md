# Stage 4: Post-Trigger Trade Planning & Fundamental Review

**Ownership:** Trading System. **Scope:** read-only EOD, manual planning; no broker orders or fills. **Status:** PR implementation; browser and SEC live feed not independently verified.

## UI and upstream contract

The fourth tab appears beside Momentum (1), Setup (2) and EOD Trigger (3).
`site/stage4.html` uses the exact same read-only cloud `site/data/latest.json`
snapshot as Stages 1–3. It selects ONLY Stage-3 records with
`status == "TRIGGERED"`, including either `FIRST_EOD_CROSS` or
`POST_APPROVAL_HOLD`. A WATCH, historical EOD_CROSS, or inferred price break
**must never** be promoted automatically.

The Stage 3 TRIGGERED row links to Stage 4 by `setup_id`. Stage 4 shows
human reviewer, signal type, signal EOD session, saved breakout pivot, and
observed EOD close; there is no invented intraday trigger time, fill or order.
On the current October 23, 2026 sample there are **zero genuine TRIGGERED**
records; the new tab intentionally shows an empty source list. A standalone
risk-calculation **scenario** remains usable for evaluation without creating
a fake stock signal.

## Risk/position sizing calculator

All fields are entered or confirmed by the human (no live pricing):

- Equity USD, per-plan risk percent, available cash USD, proposed long entry,
  initial stop, optional profit target, assumed entry slippage percent,
  estimated **round-trip** fees USD, and positive whole-share lot size.
- Assume `filled_entry = entry * (1 + slippage / 100)`,
  `budget = equity * risk_percent / 100`,
  `per_share_risk = filled_entry - stop` (must be **strictly positive**),
  `shares_by_risk = floor((budget - fees) / per_share_risk)`,
  `shares_by_cash = floor((cash - fees) / filled_entry)`, and
  `suggested_max_shares = lot * floor(min(shares_by_risk,shares_by_cash) / lot)`.
  The calculator deliberately deducts the full assumed round-trip fees from
  both budgets as a **conservative** upper-bound estimate.
- Estimated total risk = `shares * per_share_risk + fees`; capital required
  = `shares * filled_entry + fees` **when shares > 0**. With zero shares,
  both estimated risk and required cash are zero (no planned transaction).
  Optional reward/risk R = `(target - filled_entry) / per_share_risk`.
- Missing, invalid, NaN, reverse-stop, impossible fee budget or non-integral
  lot inputs **fail closed**, rather than generating a size. A positive but
  inadequate budget may legitimately return **zero shares**.
- Equity/risk/cash/entry inputs live only in the current JavaScript page memory.
  The browser does **not** upload these details to GitHub, third-party APIs,
  or persist them as account values. A user-initiated copy includes the
  scenario numbers in the clipboard.
- The link to the saved signal close / daily low is **explicitly optional** and
  labeled a hypothetical scenario. Do not treat a closing price or daily low
  as an executable entry or a guaranteed stop. Gaps, fees, slippage and
  trading conditions can cause greater losses.

The 0.5% default risk percent is merely an editable numerical example,
**not an official Qullamaggie threshold**. The warning for chosen risk
above 2% is an interface caution, **not** a validated strategy rule.

## Fundamentals from SEC EDGAR

`stage4_sec_fundamentals.py` is a **read-only** SEC provider that runs only
for actual TRIGGERED stock symbols. It uses the SEC ticker/CIK mapping, SEC
companyfacts (10-K **annual**, period and filed date), and SEC issuer
submissions (number of recent Form 4 filings). Source URLs, period ends and
filing dates accompany the historical facts. Supported current fields:

- Annual GAAP revenue (USD) and only comparable, same-tag annual YoY revenue
  growth; no invented growth when unavailable.
- Annual GAAP net income (USD), diluted EPS (USD/share).
- Number of Form 4 filings within the recent 90-day window, explicitly marked
  **filings only, not verified insider purchases**.

**Configuration dependency:** Repository secret `SEC_USER_AGENT` must be set
to an identifying project contact, for example
`QullamaggieBreakout Research contact@example.org`. Never place that real
contact email in public JSON or client code. The scheduled/manual workflow
`.github/workflows/stage4-sec-fundamentals.yml` skips SEC downloads
when the secret is absent. It can run after the daily EOD scan on
Tue–Sat at 02:17 UTC. When refreshed, it commits only
`site/data/stage4_fundamentals.json` and republishes GitHub Pages because
a GITHUB_TOKEN commit does not trigger a normal site push workflow.

No source connection, no matched CIK, missing facts, failed SEC query, or
mismatched EOD snapshot must display **UNAVAILABLE**, not zero or an affirmative
financial claim. Only show companyfacts tagged annual when 10-K FY annual
period lasts 320–380 days, to avoid mislabeled YTD data. 10-Q quarterly
dynamics are intentionally deferred pending precise comparable-period rules.

## Institutional manager and insider evidence

- SEC Form 13F reports **quarter-end institutional holdings**, usually up
  to 45 days after the quarter. It does not prove *today's* fund purchases,
  a particular "big bank" buy or beneficial shares bought after reporting.
  Verification would require named filer, matching security/CUSIP, period,
  prior report and actual filing date. **No automatic institution-buy label**.
- Form 4 reports insider transactions, commonly within two business days,
  but a Form 4 **existence/count alone is not a purchase**. A responsible
  "purchase" verification checks non-derivative stock, code **P**, acquisition
  direction, shares, price, transaction date, reporting person and amendments.
  **No automatic insider-buy label**.
- The fourth tab provides SEC primary-source links and an optional **manual
  filing observation** form with date, named entity, HTTPS filing link and
  factual note. These observations are unverified self-entered notes, stored
  **only in this browser's localStorage**, not GitHub, and explicitly
  do **not** change institution/insider purchase indicator statuses.
  This browser-only limitation must be addressed in a future authenticated
  cloud review feature if cross-device storage is needed.

Source material: [SEC EDGAR filing search](https://www.sec.gov/search-filings),
[SEC companyfacts API](https://www.sec.gov/edgar/sec-api-documentation),
[SEC Form 13F FAQ](https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f),
[SEC Forms 3/4/5 guidance](https://www.sec.gov/about/forms/forms-3-4-5.pdf).

## Safety and handoff

Stage 4 plans do not retroactively change Stage 2 READY or Stage 3 TRIGGERED,
do not generate a broker trade, and do not publish personal account values.
There is no automatic "APPROVED TO BUY" and no historical backfill of actual
prices or holdings. Research Lab remains responsible for historical
performance validation, not for building this UI.

**Next work:** verify actual Pages rendering and real authenticated Stage 3
TRIGGERED -> Stage 4 linkage; configure SEC identity and test actual
companyfacts availability; define a separately authorized cloud trade-plan
decision workflow if desired; build dated/filing-verified institutional and
insider *purchase* calculations (not merely ownership) after evidence reviews.
