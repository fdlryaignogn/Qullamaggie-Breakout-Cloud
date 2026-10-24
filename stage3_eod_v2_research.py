"""Experimental Stage-3 EOD V2 labels: research annotations, never trade signals.

Inputs are the *published completed daily chart* and a human-approved Stage-2
parent. Production scanner/state/dashboard are not mutated by this module.
No intraday time, fill, order, future-bar or return assumptions are made.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from scanner import SYMBOL_RE, clean_frame
from stage3_eod import eod_observation

ROOT = Path(__file__).resolve().parent
RULE_ID = "STAGE3_EOD_V2"
RULE_VERSION = "0.1.0"
NY = ZoneInfo("America/New_York")
NEAR_BELOW_PCT = 3.0
STRONG_RVOL20 = 1.5


def classify_eod_research(observation: dict, *, near_below_pct: float = NEAR_BELOW_PCT,
                          strong_rvol20: float = STRONG_RVOL20) -> str:
    """Provisional label, not an approved signal or an official Qullamaggie rule."""
    if not (math.isfinite(near_below_pct) and 0 <= near_below_pct <= 20):
        raise ValueError("near_below_pct must be a finite research range [0, 20]")
    if not (math.isfinite(strong_rvol20) and strong_rvol20 > 0):
        raise ValueError("strong_rvol20 must be positive and finite")
    event = observation.get("eod_event")
    distance = observation.get("eod_distance_pct")
    previous = observation.get("eod_prev_close")
    pivot = observation.get("breakout_level")
    if event == "EOD_CROSS":
        ratio = observation.get("eod_volume_ratio")
        if ratio is not None and math.isfinite(float(ratio)) and float(ratio) >= strong_rvol20:
            return "STRONG_EOD_BREAKOUT"
        return "EOD_BREAKOUT"
    if event == "ABOVE_PIVOT":
        return "ABOVE_PIVOT"
    if event == "TOUCH_ONLY":
        return "RECHECK"  # Intraday high touched level; closing breakout NOT established.
    if event != "BELOW_PIVOT":
        return "DATA_UNAVAILABLE"
    if pivot is not None and previous is not None and float(previous) > float(pivot):
        return "RECHECK"  # Previously closed above pivot, now closed below.
    if distance is not None and -near_below_pct <= float(distance) <= 0:
        return "NEAR_BREAKOUT"
    return "WATCH"


def _review_eligibility(parent: dict, as_of: str) -> tuple[bool, str, str | None]:
    """Only a genuine *as-of* human READY may yield a prospective research label.

    Session ends at NY-local 23:59:59, allowing a post-close same-day review.
    The label remains actionable no earlier than both close and human approval;
    no intraday entry/trigger is ever implied.
    """
    review_at = parent.get("manual_reviewed_at")
    actor = parent.get("manual_reviewer")
    if parent.get("setup_status") != "READY":
        return False, "PARENT_NOT_READY", None
    if not isinstance(actor, str) or not actor.strip():
        return False, "NO_AUTHENTICATED_REVIEW", None
    if not review_at:
        return False, "MISSING_REVIEW_TIMESTAMP", None
    try:
        stamp = datetime.fromisoformat(str(review_at).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return False, "REVIEW_TIMESTAMP_NO_TIMEZONE", None
        end = datetime.combine(date.fromisoformat(as_of), time(23, 59, 59), NY)
        if stamp.astimezone(NY) > end:
            return False, "HUMAN_APPROVAL_AFTER_EOD", stamp.isoformat()
        earliest = max(
            stamp.astimezone(NY),
            datetime.combine(date.fromisoformat(as_of), time(16, 0), NY)
        )
        return True, "READY_AS_OF_EOD", earliest.isoformat()
    except (TypeError, ValueError, OverflowError):
        return False, "INVALID_REVIEW_TIMESTAMP", None


def analyze_published_snapshot(snapshot_path: Path, *,
                               near_below_pct: float = NEAR_BELOW_PCT,
                               strong_rvol20: float = STRONG_RVOL20) -> dict:
    """Produce ephemeral Research Lab observations from an existing daily snapshot."""
    # Validate parameters regardless of whether any WATCH entries exist.
    classify_eod_research({"eod_event": "BELOW_PIVOT", "eod_distance_pct": -100},
                          near_below_pct=near_below_pct, strong_rvol20=strong_rvol20)
    snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    metadata = snapshot.get("metadata") or {}
    as_of = metadata.get("as_of_date")
    if metadata.get("phase") != "success" or not isinstance(as_of, str):
        raise ValueError("Requires verified successful, dated EOD snapshot")
    try:
        if date.fromisoformat(as_of).isoformat() != as_of:
            raise ValueError("Bad date")
    except ValueError as ex:
        raise ValueError("Invalid published EOD session") from ex
    state = snapshot.get("state") or {}
    parents = {p.get("setup_id"): p for p in state.get("2", []) if p.get("setup_id")}
    results = []
    for watch in state.get("3", []):
        if watch.get("status") != "WATCH":
            continue
        setup_id, symbol = watch.get("setup_id"), watch.get("symbol")
        parent = parents.get(setup_id)
        row = {"rule_id": RULE_ID, "rule_version": RULE_VERSION,
               "approval_status": "EXPERIMENTAL", "symbol": symbol,
               "setup_id": setup_id, "as_of_date": as_of, "stage": 3,
               "production_status": "WATCH", "classification": "DATA_UNAVAILABLE",
               "point_in_time_eligible": False, "eligibility_reason": "INVALID_SETUP",
               "earliest_research_available_at": None,
               "eod_event": None, "eod_close": None, "eod_distance_pct": None,
               "eod_volume_ratio": None, "eod_atr14": None, "eod_adr20_pct": None,
               "data_quality": "UNAVAILABLE", "is_trade": False}
        if (not isinstance(symbol, str) or not SYMBOL_RE.fullmatch(symbol)
                or parent is None or parent.get("symbol") != symbol
                or parent.get("setup_status") != "READY"):
            results.append(row)
            continue
        eligible, reason, earliest = _review_eligibility(parent, as_of)
        row.update({"point_in_time_eligible": eligible, "eligibility_reason": reason,
                    "earliest_research_available_at": earliest})
        try:
            pivot = float(watch.get("breakout_level"))
            if not math.isfinite(pivot) or pivot <= 0:
                raise ValueError("Invalid pivot")
            chart = json.loads((Path(snapshot_path).parent / "charts" /
                                (symbol + ".json")).read_text(encoding="utf-8"))
            if (chart.get("symbol") != symbol or chart.get("as_of") != as_of
                    or chart.get("interval") != "1d" or chart.get("adjusted") is not True):
                raise ValueError("Wrong chart provenance")
            frame = clean_frame(pd.DataFrame(chart["bars"]))
            metric = eod_observation(frame, pivot, as_of)
            if metric is None:
                raise ValueError("No verified same-session OHLCV")
            label = classify_eod_research(
                {**metric, "breakout_level": pivot},
                near_below_pct=near_below_pct, strong_rvol20=strong_rvol20)
            row.update({"classification": label, "eod_event": metric["eod_event"],
                        "eod_close": metric["eod_close"],
                        "eod_distance_pct": metric["eod_distance_pct"],
                        "eod_volume_ratio": metric["eod_volume_ratio"],
                        "eod_atr14": metric["eod_atr14"],
                        "eod_adr20_pct": metric["eod_adr20_pct"],
                        "data_quality": "VERIFIED_DAILY_CHART"})
        except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError):
            row["eligibility_reason"] = "CHART_UNAVAILABLE"
            row["point_in_time_eligible"] = False
            row["earliest_research_available_at"] = None
        results.append(row)
    return {"rule_id": RULE_ID, "rule_version": RULE_VERSION,
            "approval_status": "EXPERIMENTAL", "scope": "RESEARCH_ONLY",
            "as_of_date": as_of, "dataset_source": "existing_published_adjusted_1d",
            "near_below_pct": near_below_pct, "strong_rvol20": strong_rvol20,
            "count": len(results),
            "point_in_time_eligible_count": sum(r["point_in_time_eligible"] for r in results),
            "no_future_data": True, "new_price_downloads": False,
            "orders_submitted": False, "production_rules_modified": False,
            "observations": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Research-only EOD V2 classifications; no trading or file writes")
    parser.add_argument("--snapshot", type=Path, default=ROOT / "site/data/latest.json")
    parser.add_argument("--near-pct", type=float, default=NEAR_BELOW_PCT)
    parser.add_argument("--strong-rvol", type=float, default=STRONG_RVOL20)
    args = parser.parse_args()
    data = analyze_published_snapshot(
        args.snapshot, near_below_pct=args.near_pct, strong_rvol20=args.strong_rvol)
    print(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
