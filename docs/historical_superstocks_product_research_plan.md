# Historical Superstocks — Product & Business Momentum pilot (proposal)

Status: EXPERIMENTAL / research design only. Approved as a research direction on 2026-10-24; **no production screening rule change**.

## Objective
Test how pre-breakout product traction, business momentum, historical market cap, unadjusted share price and liquidity relate to later superstock performance. Do not assume products alone caused price gains.

## Pilot and controls
- Start with 20 historical breakout candidates spanning decades, sectors and size bands; expand to 50–100 only after provenance checks.
- Pre-register objective breakout-date and forward-return definitions before labeling winners; include contemporaneous non-winner controls to address selection/survivorship bias.
- Record ticker identity changes, delistings, splits, mergers and point-in-time universe membership.

## Point-in-time observation schema
symbol, company_name_at_date, breakout_date, as_of_cutoff, setup_id, source_url, source_publication_date, evidence_excerpt, confidence,
unadjusted_price, split_adjusted_price, shares_outstanding_as_of, market_cap_as_of, volume_20d_shares, volume_50d_shares, dollar_volume_20d, turnover_ratio, cpi_base_date, cpi_multiplier, inflation_equivalent_market_cap, inflation_equivalent_dollar_volume,
core_product_at_date, product_stage, launch_date, product_demand_evidence, customer_adoption, distribution_growth, competitive_advantage, competitor_context, reported_revenue_yoy, reported_margin, product_catalyst, information_known_at_breakout, unknown_or_missing_flags.

Never use future filings or hindsight to label what investors knew at breakout. Separate contemporaneous public evidence from later retrospective interpretation.

## Normalization
- CPI-adjusted historical market cap/dollar volume represent purchasing-power equivalents, **not current actual market cap**.
- Share price is reported separately as contemporaneous unadjusted, split-adjusted, and optionally inflation-adjusted; do not conflate.
- Split-adjust share volume when comparing share counts; CPI does not scale share volume. Compare dollar volume and turnover using point-in-time share counts.
- Keep adjustment factors and data vendor/method explicit; do not silently substitute current shares outstanding.

## Finviz threshold research
Compare hypothetical minimum market caps (<100M, 100–300M, 300M–1B, 1–10B, >10B USD), price and dollar-volume cutoffs; report inclusion/exclusion of both winners and controls, by era and industry. Current Finviz Performance 1M/3M/6M is the user's intended Stage-1 discovery interface, but historical point-in-time research requires independently verified historical data. Finviz access/export/API and ranking semantics require validation before automation.

## Outputs
- Google Sheets: Dashboard; Historical Superstocks; Product & Business; Threshold Analysis; Case Studies; Data Quality.
- GitHub: versioned research schema, scripts, evidence manifests, tests and experiment reports. Avoid committing licensed bulk market data or credentials.
- Initial deliverable: 20-row pilot with traceable sources, completeness audit and descriptive charts. No unsupported invented numbers.
- Research-to-Trading handoff only through reviewed, versioned rule proposals and explicit approval; no automatic production promotion.

## Validation checklist
1. Each numeric metric has date, unit, source, and adjustment method.
2. Each product assertion has a publication date <= breakout information cutoff.
3. Missing shares, products, or prices remain missing, not imputed as facts.
4. At least one non-winner cohort and no-lookahead checks.
5. Record sample selection, fees/slippage assumptions if evaluating returns, and limitations.

Deployment: not implemented; Google Sheet not created; data collection not started.
