# Central Coordination Directive C-001 — Research-first phased execution

Status: OWNER_APPROVED | Date: 2026-10-25
Repository: fdlryaignogn/Qullamaggie-Breakout-Cloud
Authority: Project coordination thread; owner-approved sequencing and scope.
This document coordinates work. It does not authorize changes to production strategy or broker execution.

## Priority and activation sequence

1. **R-001 Historical Superstocks Research — ACTIVE / highest priority.**
   Validate the existing 20 pilot candidates, source and timestamp each historical fact, pre-register breakout-date and winner definitions, and design contemporaneous non-winner controls. Include pre-breakout product/business momentum, fundamentals, price/volume, market cap, relative strength and market context only when point-in-time evidence supports them. Deliver a reproducible initial *validated tranche* with evidence manifest, missingness/quality report, and versioned schema. Do not invent unavailable values or treat hypotheses as proven predictors.
2. **B-001 Candlestick Breakout Research — WAITING FOR R-001 HANDOFF.**
   Begin only the specific next-phase research for which R-001 has produced a usable, versioned and auditable tranche. Define a simple baseline breakout strategy, EOD signal versus executable next-session fill assumptions, costs/slippage, R expectancy, win rate, drawdown, training/validation/out-of-sample protocol and no-lookahead tests. Coordinate additional historical feature requirements back to R-001. Do not wait for the *entire* historical research program to finish; gate by tranche acceptance.
3. **P-001 Trading Platform — DEFERRED / ON-DEMAND.**
   Do not start new web features or broad Stage 1–4 enhancements now. Engage only if R-001 or B-001 identifies a concrete blocking need for data exchange, annotation, visualization, persistence or verification, and after the owner approves the bounded task. Existing operational defects/security issues may be reported for prioritization; no scope expansion is implied.

## Cross-workstream handoff gates

- **R-001 -> B-001:** publish at least one validated tranche with case IDs, historical as-of cutoffs, source provenance, OHLCV adjustment conventions, breakout-date methodology, quality/missingness flags, and a concrete testable hypothesis. Coordinator checks evidence and owner authorizes B-001 activation.
- **B-001 -> P-001:** publish a reproducible research requirement and minimal interface proposal with inputs, outputs, tests, risks and acceptance criteria. Coordinator reviews dependency and owner authorizes a bounded P-001 task.
- Each phase can pause at a milestone; the next phase may begin when its dependency is satisfied. Full completion of the prior workstream is not required.
- Keep Research Lab experimental outputs separate from APPROVED production screening rules; follow docs/research_trading_sync_skill.md.

## Daily stock scanning

Owner permits a temporary pause of daily stock scanning while research is prioritized. **This directive does not itself disable any workflow.** Before pausing, Trading System owner must inventory the exact scheduled workflow(s), data publication dependencies, freshness effects, and recovery/re-enable steps; report the plan for owner confirmation. Do not delete historical scan snapshots, Stage-2 tracked setups, approvals, or audit history. Mark public data stale/paused if necessary; do not imply current scans are running.

## Operating constraints and reporting

- At the start of work, read AGENTS.md, PROJECT_STATE.json, docs/research_trading_sync_skill.md, skills/project_coordination/SKILL.md and detailed develop_sync_skill.md.
- GitHub committed code and state are authoritative; chat context is supplementary and not live-synchronized.
- Work on scoped branches/PRs for shared changes; report actual commit SHA, tests, deployment and blockers; update PROJECT_STATE.json after substantive work.
- Preserve Stage-1 momentum union, persistent Stage-2 FORMING/READY lifecycle, point-in-time EOD guards, and human approval.
- No new production trading rules, intraday feed, automatic orders, broker integration or platform feature expansion without separate owner approval.

## Immediate instructions by thread

**Historical research thread:** Read this directive and begin R-001. Return a short milestone plan for the first validated tranche, data-source constraints, acceptance checks and GitHub tracking location before substantive implementation.

**Breakout research thread:** Read this directive. Do not start new strategy experiments yet. Prepare only a concise list of minimum R-001 handoff data and any conflicting current commitments; wait for explicit activation.

**Trading platform thread:** Read this directive. Defer feature work. Report only (a) blocking integration dependencies and (b) an inventory and reversible pause proposal for daily scanning; do not disable workflows without explicit follow-up approval.

## Coordinator checkpoints

After each tranche: check committed artifacts, reproducibility/tests, unresolved dependencies and proposed next phase; present owner a concise approve/revise/defer decision. This directive is not a claim that other ChatGPT threads were automatically notified.
