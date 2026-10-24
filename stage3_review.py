"""Authenticated Stage-3 EOD WATCH action, persisted by GitHub Actions.

Human-confirmed fresh EOD close-cross or post-approval hold may make WATCH -> TRIGGERED.
No automatic trigger, trade execution, retrospective scan or Stage-2 approval.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
ACTIONS = {"KEEP_WATCH": "WATCH", "NO_TRADE": "NO_TRADE", "ARCHIVE": "ARCHIVED",
           "CONFIRM_EOD_TRIGGER": "TRIGGERED",
           "CONFIRM_POST_APPROVAL": "TRIGGERED"}


def apply_stage3_action(state_path: Path, latest_path: Path, *, symbol: str, setup_id: str,
                        action: str, note: str, actor: str, expected_revision: int,
                        expected_as_of_date: str, confirmed: bool = False,
                        review_timestamp: str | None = None) -> dict:
    if action not in ACTIONS:
        raise ValueError("Unsupported EOD action")
    if not actor or not actor.strip():
        raise ValueError("Authenticated GitHub actor is required")
    if not isinstance(note, str) or not 1 <= len(note.strip()) <= 500 or any(
        ord(c) < 32 or ord(c) == 127 for c in note
    ):
        raise ValueError("A public reason (1-500 characters, no controls) is required")
    if action != "KEEP_WATCH" and not confirmed:
        raise ValueError("Terminal or trigger EOD action requires manual confirmation")
    if not isinstance(expected_revision, int) or expected_revision < 0:
        raise ValueError("A current snapshot revision is required")
    if not expected_as_of_date:
        raise ValueError("Expected EOD date is required")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    public = json.loads(latest_path.read_text(encoding="utf-8"))
    meta = public.get("metadata") or {}
    if meta.get("phase") != "success" or not meta.get("last_success"):
        raise ValueError("A successful published EOD scan is required")
    if (meta.get("as_of_date") != expected_as_of_date
            or int(public.get("revision") or 0) != expected_revision):
        raise ValueError("Published EOD snapshot changed; refresh the dashboard before submitting")

    rows = [r for r in state.get("3", [])
            if r.get("setup_id") == setup_id and r.get("symbol") == symbol]
    visible = [r for r in (public.get("state") or {}).get("3", [])
               if r.get("setup_id") == setup_id and r.get("symbol") == symbol]
    if len(rows) != 1 or len(visible) != 1 or rows[0] != visible[0]:
        raise ValueError("Exactly one identical tracked and published WATCH is required")
    row = rows[0]
    if row.get("status") != "WATCH":
        raise ValueError("Only a current WATCH can be reviewed; terminal records stay terminal")
    parents = [p for p in state.get("2", [])
               if p.get("setup_id") == setup_id and p.get("symbol") == symbol
               and p.get("setup_status") == "READY"]
    public_parents = [p for p in (public.get("state") or {}).get("2", [])
                      if p.get("setup_id") == setup_id and p.get("symbol") == symbol
                      and p.get("setup_status") == "READY"]
    if len(parents) != 1 or len(public_parents) != 1:
        raise ValueError("Stage 3 action requires the existing approved READY parent")
    try:
        reviewed_at = review_timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
        timestamp = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("Review timestamp must include timezone")
        reviewed_day = timestamp.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Invalid review timestamp") from exc
    # The backend validates original adjusted daily bars and human approval
    # again; browser checkboxes and cached EOD fields are never authoritative.
    trigger_assessment = None
    if action in ("CONFIRM_EOD_TRIGGER", "CONFIRM_POST_APPROVAL"):
        from stage3_trigger_checks import assess_eod_trigger
        trigger_assessment = assess_eod_trigger(
            parents[0], row, meta, latest_path.parent / "charts", action=action)
        if not trigger_assessment["allowed"]:
            failed = [c["code"] for c in trigger_assessment["checks"]
                      if c["required"] and not c["pass"]]
            raise ValueError("EOD trigger requirements not met: " + ", ".join(failed))
    previous = row["status"]
    decision = ACTIONS[action]
    row["status"] = decision
    row["status_reason"] = note.strip()
    if trigger_assessment is not None:
        eod = trigger_assessment["evidence"]
        row["trigger_rule"] = trigger_assessment["rule"]
        row["triggered_at"] = reviewed_at
        row["eod_trigger_as_of"] = expected_as_of_date
        row["eod_trigger_confirmation_type"] = trigger_assessment["confirmation_type"]
        row["eod_trigger_approval_at"] = parents[0]["manual_reviewed_at"]
        row["eod_trigger_close"] = eod["eod_close"]
        row["eod_trigger_evidence"] = {
            "pivot": row["breakout_level"],
            "previous_close": eod["eod_prev_close"],
            "eod_close": eod["eod_close"],
            "eod_event": eod["eod_event"],
            "confirmation_type": trigger_assessment["confirmation_type"],
            "ready_approved_at": parents[0]["manual_reviewed_at"],
            "rvol20": eod["eod_volume_ratio"],
            "atr14": eod["eod_atr14"],
            "adr20_pct": eod["eod_adr20_pct"],
            "reference_risk_atr": eod["eod_ref_risk_atr"],
            "checked_requirements": [c["code"] for c in trigger_assessment["checks"]],
            "source": "published adjusted 1d OHLCV chart"
        }
        # No intraday trigger_time, entry/fill price, stop order or broker action.

    row["stage3_manual_action"] = action
    row["stage3_manual_reviewer"] = actor.strip()
    row["stage3_manual_reviewed_at"] = reviewed_at
    row["last_reviewed_at"] = reviewed_day
    row["_updated_at"] = reviewed_at
    # An EOD observation remains descriptive; do not set trigger_time, fill or stop.
    state.setdefault("history", []).insert(0, {
        "when": reviewed_at, "stage": 3, "symbol": symbol, "setup_id": setup_id,
        "from": previous, "to": decision, "action": action,
        "reason": note.strip(), "reviewer": actor.strip(),
        "trigger_rule": trigger_assessment["rule"] if trigger_assessment else None,
        "trigger_session": expected_as_of_date if trigger_assessment else None,
        "source": "authenticated GitHub Actions Stage 3 EOD review",
    })
    state["history"] = state["history"][:1000]
    state["updatedAt"] = reviewed_at
    public_row = visible[0]
    public_row.clear()
    public_row.update({k: v for k, v in row.items() if k not in {
        "api_key", "secret", "password", "account_number",
        "account_balance", "equity", "risk_fraction"
    }})
    public["state"]["history"] = [
        {k: v for k, v in item.items() if k not in {
            "api_key", "secret", "password", "account_number",
            "account_balance", "equity", "risk_fraction"
        }} for item in state["history"]
    ]
    public["state"]["updatedAt"] = reviewed_at
    public["revision"] = expected_revision + 1
    public["stage3_review_updated_at"] = reviewed_at

    # Validate both in memory before any file writes; GitHub commits the pair together.
    from review_setup import _write_json
    _write_json(state_path, state)
    _write_json(latest_path, public)
    return {"symbol": symbol, "setup_id": setup_id, "from": previous,
            "to": decision, "action": action, "reviewer": actor.strip(),
            "reviewed_at": reviewed_at, "new_revision": public["revision"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--setup-id", required=True)
    parser.add_argument("--action", required=True, choices=tuple(ACTIONS))
    parser.add_argument("--note", required=True)
    parser.add_argument("--expected-revision", required=True, type=int)
    parser.add_argument("--expected-as-of-date", required=True)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    result = apply_stage3_action(
        ROOT / "data/tracking_state.json", ROOT / "site/data/latest.json",
        symbol=args.symbol.upper(), setup_id=args.setup_id, action=args.action,
        note=args.note, actor=os.environ.get("GITHUB_ACTOR", ""),
        expected_revision=args.expected_revision, expected_as_of_date=args.expected_as_of_date,
        confirmed=args.confirm)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
