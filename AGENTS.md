# Qullamaggie agent collaboration instructions

For all Research Lab and Trading System development:
1. Read `PROJECT_STATE.json` and `docs/research_trading_sync_skill.md` before edits.
2. Follow `skills/project_coordination/SKILL.md` and `skills/project_coordination/develop_sync_skill.md`.
3. Retrieve relevant other-thread decisions where available and needed, but never assume full cross-thread access or real-time notifications.
4. Prefer isolated feature branches and PRs for shared interfaces; avoid conflicting edits.
5. Update `PROJECT_STATE.json` after substantive work; report actual commits, test status and deployment status.
6. Do not promote experimental research rules to live screening without review and explicit approval; never auto-execute orders without authorization.
