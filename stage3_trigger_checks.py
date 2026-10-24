"""Production Stage-3 EOD *eligibility* checks for HUMAN confirmed breakout events.

No experiment-specific 1.5x volume/3% proximity thresholds are imposed here.
All checks concern completed EOD data, an already approved READY parent and
a verifiable daily close-cross or a post-approval daily hold above pivot.
Triggered != executed or filled.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, date, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from scanner import SYMBOL_RE, clean_frame
from stage3_eod import eod_observation

NY = ZoneInfo("America/New_York")
EOD_RULE = "EOD_CLOSE_CROSS_MANUAL_V1"
POST_APPROVAL_RULE = "EOD_POST_APPROVAL_MANUAL_V1"
# The website and GitHub Actions offer one canonical action. The two former
# internal names remain supported by the validator for historical regression
# tests and audited compatibility; a fresh confirmation still has only one
# valid EOD event type for a given completed session.
TRIGGER_ACTIONS = {"CONFIRM_TRIGGER": None,
                   "CONFIRM_EOD_TRIGGER": EOD_RULE,
                   "CONFIRM_POST_APPROVAL": POST_APPROVAL_RULE}
EVIDENCE_FIELDS = (
    "eod_event", "eod_close", "eod_prev_close", "eod_distance_pct",
    "eod_volume_ratio", "eod_atr14", "eod_adr20_pct", "eod_ref_stop",
    "eod_ref_risk_per_share", "eod_ref_risk_atr"
)


def _check(code: str, ok: bool, description: str, required: bool = True) -> dict:
    return {"code": code, "pass": bool(ok), "required": required,
            "description": description}


def assess_eod_trigger(parent: dict, watch: dict, metadata: dict,
                       charts_dir: Path, *, action: str = "CONFIRM_EOD_TRIGGER") -> dict:
    """Fail-closed mandatory conditions, separated from optional context fields."""
    if action not in TRIGGER_ACTIONS:
        raise ValueError("Unsupported manual EOD confirmation action")
    as_of = metadata.get("as_of_date")
    symbol = watch.get("symbol")
    parent_match = bool(parent and parent.get("setup_id") == watch.get("setup_id")
                        and parent.get("symbol") == symbol
                        and parent.get("setup_status") == "READY")
    checks = [_check("READY_PARENT", parent_match, "Matching human-approved READY setup")]
    reviewer = parent.get("manual_reviewer") if parent_match else None
    reviewed_at = parent.get("manual_reviewed_at") if parent_match else None
    timestamp = None
    try:
        timestamp = datetime.fromisoformat(str(reviewed_at).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = None
    except (TypeError, ValueError, OverflowError):
        pass
    approved = bool(reviewer and str(reviewer).strip() and timestamp)
    checks.append(_check("HUMAN_APPROVAL", approved, "Dated authenticated human READY approval"))
    try:
        session = date.fromisoformat(str(as_of))
        valid_session = session.isoformat() == as_of
    except (TypeError, ValueError, OverflowError):
        valid_session = False
        session = None
    # A review after the 16:00 New York close cannot authorize that same
    # session's EOD observation, even if its calendar date still matches.
    asof_approved = bool(approved and valid_session and
                        timestamp.astimezone(NY) <= datetime.combine(
                            session, time(16, 0), NY))
    checks.append(_check("APPROVED_BY_CLOSE", asof_approved,
                         "READY was approved by 16:00 New York on this EOD date"))
    valid_snapshot = bool(valid_session and metadata.get("phase") == "success"
                          and metadata.get("last_success"))
    checks.append(_check("PUBLISHED_EOD", valid_snapshot, "Published completed EOD snapshot"))
    pivot = None
    try:
        pivot = float(watch.get("breakout_level"))
        if not math.isfinite(pivot) or pivot <= 0:
            pivot = None
    except (ValueError, TypeError):
        pass
    checks.append(_check("APPROVED_PIVOT", pivot is not None, "Positive saved breakout pivot"))
    evidence = None
    correct_chart = False
    if (parent_match and valid_snapshot and pivot is not None
            and isinstance(symbol, str) and SYMBOL_RE.fullmatch(symbol)):
        try:
            chart = json.loads((Path(charts_dir) / (symbol + ".json")).read_text(encoding="utf-8"))
            if (chart.get("symbol") == symbol and chart.get("interval") == "1d"
                    and chart.get("adjusted") is True and chart.get("as_of") == as_of):
                frame = clean_frame(pd.DataFrame(chart["bars"]))
                if not frame.empty and frame.index[-1].strftime("%Y-%m-%d") == as_of:
                    evidence = eod_observation(frame, pivot, as_of)
                    correct_chart = evidence is not None
        except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError):
            pass
    checks.append(_check("VERIFIED_DAILY_CHART", correct_chart,
                         "Matching symbol/date/adjusted 1d chart with no future bars"))
    saved_match = bool(
        evidence and watch.get("eod_as_of") == as_of
        and watch.get("eod_data_status") == "FRESH"
        and all(watch.get(key) == evidence.get(key) for key in EVIDENCE_FIELDS)
    )
    checks.append(_check("SAVED_EOD_MATCH", saved_match,
                         "Saved EOD observations agree with the verified daily bars"))
    cross = bool(evidence and evidence.get("eod_event") == "EOD_CROSS"
                 and evidence["eod_close"] > pivot
                 and evidence["eod_prev_close"] <= pivot)
    above = bool(evidence and evidence.get("eod_event") == "ABOVE_PIVOT"
                 and evidence["eod_prev_close"] > pivot
                 and evidence["eod_close"] > pivot)
    if action == "CONFIRM_EOD_TRIGGER":
        checks.append(_check("EOD_CLOSE_CROSS", cross,
                             "First upward EOD close-cross after READY approval"))
    elif action == "CONFIRM_POST_APPROVAL":
        checks.append(_check("POST_APPROVAL_HOLD", above,
                             "Latest completed EOD still above pivot; previous close also above"))
    else:
        # Mutually exclusive daily close conditions: the preceding close is
        # either <= pivot (new cross) or > pivot (still above), not both.
        # Do not trust a caller-supplied classification or browser selection.
        checks.append(_check("EOD_ELIGIBLE_PATTERN", cross or above,
                             "Completed close-cross OR completed post-approval hold above saved pivot"))

    # Volume and risk fields are reference information, not invented hard gates.
    ratio = evidence.get("eod_volume_ratio") if evidence else None
    atr = evidence.get("eod_atr14") if evidence else None
    adr = evidence.get("eod_adr20_pct") if evidence else None
    risk = evidence.get("eod_ref_risk_atr") if evidence else None
    ready = all(item["pass"] for item in checks if item["required"])
    if action == "CONFIRM_TRIGGER":
        rule = EOD_RULE if cross else POST_APPROVAL_RULE if above else None
        confirmation_type = ("FIRST_EOD_CROSS" if cross else
                             "POST_APPROVAL_HOLD" if above else None)
    else:
        rule = TRIGGER_ACTIONS[action]
        confirmation_type = ("FIRST_EOD_CROSS" if action == "CONFIRM_EOD_TRIGGER"
                             else "POST_APPROVAL_HOLD")
    return {"rule": rule, "action": action,
            "confirmation_type": confirmation_type,
            "allowed": ready, "as_of_date": as_of,
            "checks": checks, "evidence": evidence,
            "context": {"rvol20": ratio, "atr14": atr, "adr20_pct": adr,
                        "reference_risk_atr": risk,
                        "volume_threshold_required": False,
                        "hypothetical_risk_not_an_order": True},
            "is_order": False, "is_fill": False, "intraday_trigger_time": None}
