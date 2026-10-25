# C-003 — Standardized GitHub Handoff Summaries and Thread Continuity

Status: OWNER_APPROVED | Date: 2026-10-25
Scope: coordination and documentation only. Supplements C-001 and C-002; no additional research, platform features, trading rules, scheduled scan changes or broker execution authorized.

## Canonical handoff files

- Historical Superstocks Research: `coordination/handoffs/historical-superstocks.md`
- Candlestick Breakout Research: `coordination/handoffs/breakout-research.md`
- Trading Platform: `coordination/handoffs/trading-platform.md`

Each workstream maintains its own concise, **latest-state** Markdown file; Git history preserves prior revisions. Do not duplicate chat transcripts. Keep claims attributable to actual commits, data files and test reports. GitHub source files and `PROJECT_STATE.json` remain authoritative; a handoff summary is a navigation and continuity aid, not a substitute.

## Required sections in each summary

1. **Current Status** — phase, scope, as-of date, active directive, whether authorized/blocked.
2. **Completed Work** — verified deliverables and separately unverified/in-progress items.
3. **Key Decisions** — owner-approved decisions with directive/PR links; distinguish proposals.
4. **GitHub References** — source file paths, commits, PRs, reproducible datasets.
5. **Tests & Blockers** — exact executed tests and results, unrun tests, evidence gaps and dependencies.
6. **Next Actions** — bounded next milestone, handoff readiness, approvals required.

## Update and delivery procedure

Update when a meaningful milestone completes, an important approved decision/dependency changes, or a thread is about to reach its conversation length limit / hand over to a successor. Do **not** update on every chat message. Commit on an isolated branch/PR when practical; include actual test results and update `PROJECT_STATE.json` for substantive status changes. A documentation-only change needs structure/link checks, not invented runtime test claims. If unable to push, explicitly report failure and supply the proposed diff for owner action.

Historical Research is the only active research workstream. It must update its handoff at the first R-001 milestone and before any thread rollover. Current R-001 source-discovery files are not validated stock cases. Breakout Research and Trading Platform need not perform new work merely to populate these files; update on their next approved activation, important status change or rollover.

## Thread restart instruction (approved canonical text)

> 請接續 Qullamaggie 專案工作。先讀取 GitHub Repository `fdlryaignogn/Qullamaggie-Breakout-Cloud` 的 `AGENTS.md`、`PROJECT_STATE.json`、`docs/research_trading_sync_skill.md`、`skills/project_coordination/SKILL.md`、`skills/project_coordination/develop_sync_skill.md`、最新中央協調指令，以及你所屬工作範圍的 `coordination/handoffs/` 文件。以 GitHub 已提交狀態為正式依據，確認目前進度、未完成事項和下一步，不要重新開始已完成的工作，也不要自行擴大範圍。先核對當前 GitHub Commit 和測試狀態，發現衝突先回報。

## Owner notification and limits

ChatGPT threads are **not** automatically notified by a GitHub commit. Owner may paste a short notification directing each thread to C-003. No cross-thread automatic execution is implied. Continue C-002 sequencing: R-001 first; B-001 A/B/C design remains gated by validated tranche and explicit activation; P-001 deferred. Temporary scan pause still requires separate confirmed reversible plan.
