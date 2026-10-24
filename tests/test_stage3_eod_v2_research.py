"""Experimental EOD V2 must never promote hindsight into trade signals."""
import copy
import json
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from stage3_eod_v2_research import (
    analyze_published_snapshot, classify_eod_research, RULE_ID, RULE_VERSION,
)


def observation(*, event="BELOW_PIVOT", distance=-5, rv=1, prev=99, pivot=100):
    return {"eod_event": event, "eod_distance_pct": distance,
            "eod_volume_ratio": rv, "eod_prev_close": prev,
            "breakout_level": pivot}


@pytest.mark.parametrize("inputs,expected", [
    ({"event": "EOD_CROSS", "distance": .5, "rv": 2}, "STRONG_EOD_BREAKOUT"),
    ({"event": "EOD_CROSS", "distance": .5, "rv": 1.49}, "EOD_BREAKOUT"),
    ({"event": "EOD_CROSS", "distance": .5, "rv": None}, "EOD_BREAKOUT"),
    ({"event": "ABOVE_PIVOT", "distance": 3, "rv": 2}, "ABOVE_PIVOT"),
    ({"event": "TOUCH_ONLY", "distance": -1, "rv": 2}, "RECHECK"),
    ({"event": "BELOW_PIVOT", "distance": -1, "prev": 101}, "RECHECK"),
    ({"event": "BELOW_PIVOT", "distance": -2, "prev": 99}, "NEAR_BREAKOUT"),
    ({"event": "BELOW_PIVOT", "distance": -3, "prev": 99}, "NEAR_BREAKOUT"),
    ({"event": "BELOW_PIVOT", "distance": -3.01, "prev": 99}, "WATCH"),
])
def test_provisional_daily_classifications(inputs, expected):
    assert classify_eod_research(observation(**inputs)) == expected


def fixture(tmp_path):
    dates = pd.bdate_range("2026-09-01", periods=40)
    as_of = dates[-1].strftime("%Y-%m-%d")
    bars = [{"date": d.strftime("%Y-%m-%d"), "open": 99.5,
             "high": 101, "low": 98, "close": 99.5, "volume": 100} for d in dates]
    bars[-1].update({"close": 100.5, "high": 102, "volume": 200})
    charts = tmp_path / "charts"
    charts.mkdir()
    chart = {"symbol": "TEST", "as_of": as_of, "interval": "1d",
             "adjusted": True, "bars": bars}
    (charts / "TEST.json").write_text(json.dumps(chart))
    review_dt = datetime.combine(date.fromisoformat(as_of), time(17), ZoneInfo("America/New_York"))
    parent = {"symbol": "TEST", "setup_id": "TEST-1", "setup_status": "READY",
              "base_high": 100, "manual_reviewed_at": review_dt.isoformat(),
              "manual_reviewer": "authorized-test-reviewer"}
    state = {"2": [parent], "3": [{
        "symbol": "TEST", "setup_id": "TEST-1", "status": "WATCH",
        "breakout_level": 100}], "1": [], "history": []}
    doc = {"revision": 123, "metadata": {"phase": "success",
           "as_of_date": as_of, "last_success": "a historical time"},
           "state": state}
    path = tmp_path / "latest.json"
    path.write_text(json.dumps(doc))
    return path, doc, chart, as_of


def test_research_only_and_review_provenance(tmp_path):
    path, doc, _, as_of = fixture(tmp_path)
    before = path.read_bytes()
    report = analyze_published_snapshot(path)
    assert report["rule_id"] == RULE_ID
    assert report["rule_version"] == RULE_VERSION
    assert report["approval_status"] == "EXPERIMENTAL"
    assert report["scope"] == "RESEARCH_ONLY"
    assert report["count"] == 1
    assert report["point_in_time_eligible_count"] == 1
    row = report["observations"][0]
    assert row["classification"] == "STRONG_EOD_BREAKOUT"
    assert row["eod_event"] == "EOD_CROSS"
    assert row["eod_volume_ratio"] == 2
    assert row["point_in_time_eligible"] is True
    assert row["eligibility_reason"] == "READY_AS_OF_EOD"
    assert row["earliest_research_available_at"].startswith(as_of + "T17:")
    assert row["production_status"] == "WATCH"
    assert row["is_trade"] is False and report["orders_submitted"] is False
    assert path.read_bytes() == before  # Never edits tracked or public state.


def test_approval_after_asof_never_becomes_historical_signal(tmp_path):
    path, doc, _, as_of = fixture(tmp_path)
    after = datetime.combine(date.fromisoformat(as_of) + timedelta(days=1),
                             time(1), ZoneInfo("America/New_York"))
    doc["state"]["2"][0]["manual_reviewed_at"] = after.isoformat()
    path.write_text(json.dumps(doc))
    report = analyze_published_snapshot(path)
    row = report["observations"][0]
    assert row["eod_event"] == "EOD_CROSS"  # descriptive historical observation
    assert row["classification"] == "STRONG_EOD_BREAKOUT"  # research-only hypothetical label
    assert row["point_in_time_eligible"] is False
    assert row["eligibility_reason"] == "HUMAN_APPROVAL_AFTER_EOD"
    assert report["point_in_time_eligible_count"] == 0


def test_missing_human_authentication_cannot_be_prospective(tmp_path):
    path, doc, _, _ = fixture(tmp_path)
    del doc["state"]["2"][0]["manual_reviewer"]
    path.write_text(json.dumps(doc))
    row = analyze_published_snapshot(path)["observations"][0]
    assert row["point_in_time_eligible"] is False
    assert row["eligibility_reason"] == "NO_AUTHENTICATED_REVIEW"


def test_parent_mismatch_and_nonwatch_are_excluded(tmp_path):
    path, doc, _, _ = fixture(tmp_path)
    doc["state"]["2"][0]["setup_status"] = "FORMING"
    path.write_text(json.dumps(doc))
    row = analyze_published_snapshot(path)["observations"][0]
    assert row["point_in_time_eligible"] is False
    assert row["classification"] == "DATA_UNAVAILABLE"
    assert row["eligibility_reason"] == "INVALID_SETUP"
    doc["state"]["3"][0]["status"] = "TRIGGERED"
    path.write_text(json.dumps(doc))
    assert analyze_published_snapshot(path)["count"] == 0


def test_chart_mismatch_future_tail_and_saved_disagreement_fail_closed(tmp_path):
    path, doc, chart, as_of = fixture(tmp_path)
    dst = tmp_path / "charts" / "TEST.json"
    for update in ({"symbol": "WRONG"}, {"interval": "5m"}, {"adjusted": False},
                   {"as_of": "2026-01-01"},
                   {"bars": chart["bars"] + [{"date": "2027-01-01", "open": 100,
                       "high": 101, "low": 99, "close": 100, "volume": 100}]}):
        dst.write_text(json.dumps({**chart, **update}))
        row = analyze_published_snapshot(path)["observations"][0]
        assert row["point_in_time_eligible"] is False
        assert row["data_quality"] == "UNAVAILABLE"
        assert row["classification"] == "DATA_UNAVAILABLE"
    dst.write_text(json.dumps(chart))
    doc["state"]["3"][0]["eod_as_of"] = as_of
    doc["state"]["3"][0]["eod_data_status"] = "FRESH"
    doc["state"]["3"][0]["eod_close"] = 999
    path.write_text(json.dumps(doc))
    row = analyze_published_snapshot(path)["observations"][0]
    assert row["classification"] == "DATA_UNAVAILABLE"


def test_no_zero_filled_volume_and_param_validation(tmp_path):
    path, doc, chart, _ = fixture(tmp_path)
    dst = tmp_path / "charts" / "TEST.json"
    chart["bars"][-1]["volume"] = 0
    dst.write_text(json.dumps(chart))
    row = analyze_published_snapshot(path)["observations"][0]
    assert row["classification"] == "EOD_BREAKOUT"
    assert row["eod_volume_ratio"] is None
    for inputs in ({"near_below_pct": -1}, {"strong_rvol20": 0},
                   {"strong_rvol20": float("nan")}):
        with pytest.raises(ValueError):
            analyze_published_snapshot(path, **inputs)


def test_snapshot_not_successful_rejected(tmp_path):
    path, doc, _, _ = fixture(tmp_path)
    doc["metadata"]["phase"] = "failed"
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="successful"):
        analyze_published_snapshot(path)
