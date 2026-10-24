"""Read-only cloud EOD audit regressions; does not fetch or alter market data."""
import json

import pandas as pd

from stage3_eod_audit import audit_snapshot
from stage3_eod import enrich_from_published_charts


def fixture(tmp_path):
    dates = pd.bdate_range("2026-09-01", periods=40)
    bars = [{"date": d.strftime("%Y-%m-%d"), "open": 99.5, "high": 101,
             "low": 98, "close": 99.5, "volume": 100} for d in dates]
    bars[-1].update({"close": 100.5, "high": 102, "volume": 200})
    as_of = bars[-1]["date"]
    folder = tmp_path / "charts"
    folder.mkdir()
    chart = {"symbol": "ABC", "as_of": as_of, "interval": "1d",
             "adjusted": True, "bars": bars}
    (folder / "ABC.json").write_text(json.dumps(chart), encoding="utf-8")
    state = {"2": [{"symbol": "ABC", "setup_id": "ABC-1", "setup_status": "READY",
                    "base_high": 100}],
             "3": [{"symbol": "ABC", "setup_id": "ABC-1",
                    "status": "WATCH", "breakout_level": 100}]}
    snapshot = tmp_path / "latest.json"
    snapshot.write_text(json.dumps({"metadata": {"phase": "success",
        "as_of_date": as_of}, "state": state}), encoding="utf-8")
    return snapshot, state, as_of


def test_old_watch_rows_are_derived_but_never_written(tmp_path):
    snapshot, _, as_of = fixture(tmp_path)
    before = snapshot.read_bytes()
    result = audit_snapshot(snapshot)
    assert snapshot.read_bytes() == before
    assert result["as_of_date"] == as_of and result["files_modified"] is False
    assert result["counts"]["DERIVED_NOT_PERSISTED"] == 1
    assert result["entries"][0]["eod_event"] == "EOD_CROSS"
    assert result["entries"][0]["eod_volume_ratio"] == 2


def test_persisted_metrics_match_or_fail_audit(tmp_path):
    snapshot, state, as_of = fixture(tmp_path)
    enrich_from_published_charts(state, tmp_path / "charts", as_of)
    record = json.loads(snapshot.read_text())
    record["state"] = state
    snapshot.write_text(json.dumps(record))
    assert audit_snapshot(snapshot)["counts"]["PERSISTED_MATCH"] == 1
    record["state"]["3"][0]["eod_atr14"] = 999
    snapshot.write_text(json.dumps(record))
    result = audit_snapshot(snapshot)
    assert result["counts"]["METRIC_MISMATCH"] == 1
    assert result["entries"][0]["status"] == "METRIC_MISMATCH"


def test_wrong_chart_is_reported_unavailable(tmp_path):
    snapshot, _, _ = fixture(tmp_path)
    source = tmp_path / "charts" / "ABC.json"
    chart = json.loads(source.read_text())
    chart["as_of"] = "2026-10-22"
    source.write_text(json.dumps(chart))
    result = audit_snapshot(snapshot)
    assert result["counts"]["CHART_UNAVAILABLE"] == 1
    assert result["entries"][0]["eod_event"] is None
