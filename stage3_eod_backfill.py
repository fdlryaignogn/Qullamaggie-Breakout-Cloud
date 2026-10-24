"""Opt-in, deterministic EOD WATCH metric backfill from already-published charts.

No market downloads, new scan timestamps, human approval changes or orders.
This script processes *both* private tracking and public snapshot records.
Its default mode only previews; --apply writes the two coordinated files.
Production GitHub publication should use a reviewed atomic PR merge.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from datetime import date
from pathlib import Path

from stage3_eod import enrich_from_published_charts

ROOT = Path(__file__).resolve().parent


def _identity(watch: dict) -> tuple:
    return watch.get("setup_id"), watch.get("symbol")


def _eod_fields(row: dict) -> dict:
    return {k: v for k, v in row.items() if k.startswith("eod_")}


def prepare_backfill(tracking: dict, published: dict, chart_dir: Path) -> tuple[dict, dict, int]:
    """Calculate a complete coordinated update, failing closed on mismatched data."""
    meta = published.get("metadata") or {}
    as_of = meta.get("as_of_date")
    if meta.get("phase") != "success" or not meta.get("last_success"):
        raise ValueError("A verified successful published scan is required")
    if not isinstance(as_of, str) or len(as_of) != 10:
        raise ValueError("Invalid EOD as-of date")
    try:
        if date.fromisoformat(as_of).isoformat() != as_of:
            raise ValueError("Bad date")
    except ValueError as ex:
        raise ValueError("Invalid EOD as-of date") from ex

    public_state = published.get("state") or {}
    private_rows = tracking.get("3") or []
    public_rows = public_state.get("3") or []
    if len(private_rows) != len(public_rows) or private_rows != public_rows:
        raise ValueError("Tracking and published Stage-3 rows disagree; refusing overwrite")

    parent_lookup = {p.get("setup_id"): p for p in tracking.get("2", [])}
    public_parents = {p.get("setup_id"): p for p in public_state.get("2", [])}
    prepared = copy.deepcopy(tracking)
    enrich_from_published_charts(prepared, chart_dir, as_of)
    revised_public = copy.deepcopy(published)
    changed = 0
    seen = set()
    for i, original in enumerate(private_rows):
        if original.get("status") != "WATCH":
            continue
        key = _identity(original)
        if key in seen or not key[0] or not key[1]:
            raise ValueError("Duplicate or invalid WATCH setup identity")
        seen.add(key)
        p = parent_lookup.get(key[0])
        q = public_parents.get(key[0])
        if (not p or not q or p.get("symbol") != key[1] or q.get("symbol") != key[1]
                or p.get("setup_status") != "READY" or q.get("setup_status") != "READY"):
            raise ValueError("WATCH needs an identical manually approved READY parent")
        pivot = float(original.get("breakout_level") or 0)
        if not math.isfinite(pivot) or pivot <= 0:
            raise ValueError("Invalid approved breakout level")
        new = prepared["3"][i]
        if new.get("eod_as_of") != as_of or new.get("eod_data_status") != "FRESH":
            raise ValueError("Missing, mismatched or stale chart for " + str(key[1]))
        fields = _eod_fields(new)
        if not fields or fields.get("eod_event") is None:
            raise ValueError("No valid EOD observations for " + str(key[1]))
        current = _eod_fields(original)
        if current.get("eod_as_of") == as_of and current.get("eod_data_status") == "FRESH":
            if current != fields:
                raise ValueError("Conflicting saved current-session EOD values for " + str(key[1]))
            continue
        # Do not touch status, pivot, approvals, audit history, or user trade fields.
        merged = {**original, **fields}
        prepared["3"][i] = merged
        revised_public["state"]["3"][i] = copy.deepcopy(merged)
        changed += 1
    if changed:
        # Revision asks open dashboards to fetch changed JSON, without a new scan alert.
        revised_public["revision"] = int(revised_public.get("revision") or 0) + 1
    return prepared, revised_public, changed


def _write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".eod.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(tmp, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or apply safe same-session EOD WATCH backfill")
    parser.add_argument("--tracking", type=Path, default=ROOT / "data/tracking_state.json")
    parser.add_argument("--published", type=Path, default=ROOT / "site/data/latest.json")
    parser.add_argument("--apply", action="store_true", help="Write updated tracking + public files")
    args = parser.parse_args()
    tracking = json.loads(args.tracking.read_text(encoding="utf-8"))
    published = json.loads(args.published.read_text(encoding="utf-8"))
    new_tracking, new_public, changed = prepare_backfill(
        tracking, published, args.published.parent / "charts"
    )
    if args.apply and changed:
        _write(args.tracking, new_tracking)
        _write(args.published, new_public)
    print(json.dumps({"as_of": published["metadata"]["as_of_date"],
                      "watches_changed": changed, "applied": bool(args.apply and changed),
                      "new_scan": False, "orders": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
