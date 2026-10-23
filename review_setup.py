"""Authenticated GitHub Actions review for Stage 2 recommendations.

The public site is read-only. Review changes must not impersonate a fresh
market scan or claim a confirmed intraday trade.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".review.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(tmp, path)


def review_setup(state_path: Path, latest_path: Path, *, symbol: str, setup_id: str,
                 decision: str, note: str, actor: str, confirmed: bool = False,
                 review_timestamp: str | None = None) -> dict:
    """Apply a human decision, audit it and update cloud JSON without new scan metadata."""
    if decision not in ("READY", "FORMING", "INVALIDATED"):
        raise ValueError("Decision must be READY, FORMING, or INVALIDATED")
    if not actor or not actor.strip():
        raise ValueError("Authenticated GitHub actor is required")
    if not note.strip() or len(note.strip()) > 500:
        raise ValueError("A public review reason (1-500 characters) is required")
    if decision == "READY" and not confirmed:
        raise ValueError("READY requires confirmed chart review")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    public = json.loads(latest_path.read_text(encoding="utf-8"))
    metadata = public.get("metadata") or {}
    if metadata.get("phase") != "success" or not metadata.get("last_success"):
        raise ValueError("No verified published market scan to review")
    matched = [r for r in state.get("2", []) if
               r.get("symbol", "").upper() == symbol.upper() and r.get("setup_id") == setup_id]
    if len(matched) != 1:
        raise ValueError("Exactly one matching tracked setup is required")
    row = matched[0]
    published = [r for r in (public.get("state") or {}).get("2", []) if r.get("setup_id") == setup_id]
    if len(published) != 1 or published[0].get("symbol") != row.get("symbol"):
        raise ValueError("Published review candidate and tracked setup disagree")
    previous = str(row.get("setup_status", "FORMING")).upper()
    if previous in ("ARCHIVED", "INVALIDATED", "REJECT"):
        raise ValueError("Archived/invalidated setup cannot be reopened; create a new setup")
    if decision == "READY":
        if row.get("readiness_recommendation") != "READY_CANDIDATE":
            raise ValueError("READY requires a current READY_CANDIDATE recommendation")
        if not all(row.get("readiness_checks", {}).get(k) for k in
                   ("volatility_contraction", "price_structure", "breakout_proximity")):
            raise ValueError("Missing validated structural readiness checks")
        try:
            pivot = float(row.get("base_high"))
        except (TypeError, ValueError):
            raise ValueError("READY requires a valid breakout pivot") from None
        if not math.isfinite(pivot) or pivot <= 0:
            raise ValueError("READY requires a positive breakout pivot")
    reviewed_at = review_timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
    review_day = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00")).astimezone(
        ZoneInfo("America/New_York")).date().isoformat()
    row["setup_status"] = decision
    row["last_reviewed_at"] = review_day
    row["manual_reviewed_at"] = reviewed_at
    row["manual_reviewer"] = actor
    row["status_reason"] = f"Human chart review by {actor}: {note.strip()}"
    row["_updated_at"] = reviewed_at
    if decision == "READY":
        row["ready_since"] = row.get("ready_since") or review_day
        matches = [r for r in state.get("3", []) if r.get("setup_id") == setup_id]
        if not matches:
            state.setdefault("3", []).append({
                "symbol": row["symbol"], "setup_id": setup_id,
                "watch_date": review_day, "trade_date": metadata.get("as_of_date"),
                "setup_status": "READY", "breakout_level": round(pivot, 4),
                "status": "WATCH", "last_reviewed_at": review_day,
                "status_reason": "Human-approved READY; EOD WATCH only, not a trade trigger",
                "_updated_at": reviewed_at,
            })
            state.setdefault("history", []).insert(0, {
                "when": reviewed_at, "stage": 3, "symbol": row["symbol"], "setup_id": setup_id,
                "from": "", "to": "WATCH", "reason": "Human READY approval; observation only",
                "reviewer": actor,
            })
        elif matches[0].get("status") == "WATCH":
            matches[0]["setup_status"] = "READY"
            matches[0]["breakout_level"] = round(pivot, 4)
    elif decision == "INVALIDATED":
        row["invalidation_reason"] = note.strip()
        for watch in state.get("3", []):
            if watch.get("setup_id") == setup_id and watch.get("status") == "WATCH":
                watch["status"] = "INVALIDATED"
                watch["status_reason"] = f"Underlying setup invalidated by {actor}"
    else:
        for watch in state.get("3", []):
            if watch.get("setup_id") == setup_id and watch.get("status") == "WATCH":
                watch["setup_status"] = "FORMING"  # paused by the dashboard
    state.setdefault("history", []).insert(0, {
        "when": reviewed_at, "stage": 2, "symbol": row["symbol"], "setup_id": setup_id,
        "from": previous, "to": decision, "reason": note.strip(), "reviewer": actor,
        "source": "authenticated GitHub Actions review",
    })
    state["history"] = state["history"][:1000]
    state["updatedAt"] = reviewed_at
    public_state = public["state"]
    # Mirrors the scanner's approved public projection. No API secrets or account data.
    bad_fields = {"api_key", "secret", "password", "account_number",
                  "account_balance", "equity", "risk_fraction"}
    for stage in ("2", "3"):
        public_state[stage] = [{k: v for k, v in entry.items() if k not in bad_fields}
                               for entry in state.get(stage, [])]
    public_state["history"] = [{k: v for k, v in entry.items() if k not in bad_fields}
                               for entry in state["history"]]
    public_state["updatedAt"] = reviewed_at
    # Bump data revision so already-open dashboards reload the human decision.
    # The successful market scan timestamp is unchanged, so no false scan alert.
    public["revision"] = int(public.get("revision") or 0) + 1
    public["review_updated_at"] = reviewed_at
    _write_json(state_path, state)
    _write_json(latest_path, public)
    return {"symbol": row["symbol"], "setup_id": setup_id, "from": previous,
            "to": decision, "reviewed_at": reviewed_at, "reviewer": actor}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--setup-id", required=True)
    parser.add_argument("--decision", required=True, choices=["READY", "FORMING", "INVALIDATED"])
    parser.add_argument("--note", required=True)
    parser.add_argument("--confirm-reviewed", action="store_true")
    args = parser.parse_args()
    result = review_setup(
        ROOT / "data/tracking_state.json", ROOT / "site/data/latest.json",
        symbol=args.symbol, setup_id=args.setup_id, decision=args.decision, note=args.note,
        actor=os.environ.get("GITHUB_ACTOR", ""), confirmed=args.confirm_reviewed,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
