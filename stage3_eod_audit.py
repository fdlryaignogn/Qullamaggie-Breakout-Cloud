"""Read-only audit of public Stage-3 EOD observations against published 1d charts.

This is not a trading rule, price refresh, database synchronization or deployment.
No files are written; the as-of date always comes from the existing snapshot.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from stage3_eod import enrich_from_published_charts

ROOT = Path(__file__).resolve().parent
METRICS = (
    "eod_event", "eod_close", "eod_distance_pct",
    "eod_volume_ratio", "eod_atr14", "eod_adr20_pct",
    "eod_ref_stop", "eod_ref_risk_atr",
)


def audit_snapshot(snapshot_path: Path) -> dict:
    """Report whether persisted EOD fields agree with validated chart-derived values."""
    published = json.loads(snapshot_path.read_text(encoding="utf-8"))
    meta = published.get("metadata") or {}
    as_of = meta.get("as_of_date")
    if meta.get("phase") != "success" or not isinstance(as_of, str) or len(as_of) != 10:
        raise ValueError("Audit requires a successful dated EOD snapshot")
    state = published.get("state") or {}
    original = state.get("3") or []
    calculated = copy.deepcopy(state)
    enrich_from_published_charts(calculated, snapshot_path.parent / "charts", as_of)
    computed = {w.get("setup_id"): w for w in calculated.get("3", [])}
    results = []
    counts = {"PERSISTED_MATCH": 0, "DERIVED_NOT_PERSISTED": 0,
              "METRIC_MISMATCH": 0, "CHART_UNAVAILABLE": 0, "NOT_WATCH": 0}
    for watch in original:
        if watch.get("status") != "WATCH":
            status = "NOT_WATCH"
            eod = None
        else:
            candidate = computed.get(watch.get("setup_id")) or {}
            if candidate.get("eod_as_of") != as_of or candidate.get("eod_data_status") != "FRESH":
                status = "CHART_UNAVAILABLE"
                eod = None
            else:
                eod = {key: candidate.get(key) for key in METRICS}
                if watch.get("eod_as_of") != as_of or watch.get("eod_data_status") != "FRESH":
                    status = "DERIVED_NOT_PERSISTED"
                elif any(watch.get(key) != eod[key] for key in METRICS):
                    status = "METRIC_MISMATCH"
                else:
                    status = "PERSISTED_MATCH"
        counts[status] += 1
        results.append({
            "symbol": watch.get("symbol"), "setup_id": watch.get("setup_id"),
            "status": status, "eod_as_of": as_of if eod is not None else None,
            "eod_event": eod.get("eod_event") if eod else None,
            "eod_close": eod.get("eod_close") if eod else None,
            "eod_volume_ratio": eod.get("eod_volume_ratio") if eod else None,
            "eod_atr14": eod.get("eod_atr14") if eod else None,
            "eod_adr20_pct": eod.get("eod_adr20_pct") if eod else None,
        })
    return {
        "as_of_date": as_of, "phase": meta["phase"],
        "chart_values_are_historical": True, "files_modified": False,
        "watch_count": sum(w.get("status") == "WATCH" for w in original),
        "counts": counts, "entries": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit saved Stage-3 EOD metrics without making changes")
    parser.add_argument("--snapshot", type=Path, default=ROOT / "site/data/latest.json")
    parser.add_argument("--strict", action="store_true", help="Fail on mismatching persisted metric fields")
    args = parser.parse_args()
    report = audit_snapshot(args.snapshot)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    if args.strict and report["counts"]["METRIC_MISMATCH"]:
        parser.exit(2, "Persisted Stage-3 EOD metrics disagree with published charts\n")


if __name__ == "__main__":
    main()
