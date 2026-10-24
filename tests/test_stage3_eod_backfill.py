"""Stage 3 historical backfill is deterministic, coordinated and trade-safe."""
import copy
import json

import pandas as pd
import pytest

from stage3_eod_backfill import prepare_backfill


def fixture(tmp_path):
    dates = pd.bdate_range("2026-09-01", periods=40)
    bars = [{"date": day.strftime("%Y-%m-%d"), "open": 99.5,
             "high": 101, "low": 98, "close": 99.5, "volume": 100} for day in dates]
    bars[-1].update({"high": 102, "close": 100.5, "volume": 200})
    asof = bars[-1]["date"]
    (tmp_path / "ABC.json").write_text(json.dumps({
        "symbol": "ABC", "as_of": asof, "interval": "1d", "adjusted": True,
        "bars": bars
    }), encoding="utf-8")
    ready = {"symbol": "ABC", "setup_id": "ABC-1", "setup_status": "READY",
             "base_high": 100, "manual_reviewer": "human"}
    watch = {"symbol": "ABC", "setup_id": "ABC-1", "status": "WATCH",
             "breakout_level": 100, "initial_stop": 96,
             "status_reason": "Human approved", "last_reviewed_at": asof}
    tracking = {"1": [], "2": [ready], "3": [watch], "history": [],
                "updatedAt": "2026-10-24T01:00:00Z"}
    published = {
        "metadata": {"phase": "success", "as_of_date": asof,
                     "last_success": "2026-10-24T00:00:00Z",
                     "scanner_version": "3.0-cloud"},
        "revision": 123,
        "state": copy.deepcopy(tracking),
        "review_updated_at": "2026-10-24T01:00:00Z"
    }
    return tracking, published


def test_backfill_preserves_human_approval_and_scan_metadata(tmp_path):
    tracking, published = fixture(tmp_path)
    original_meta = copy.deepcopy(published["metadata"])
    original_history = copy.deepcopy(tracking["history"])
    new_private, new_public, n = prepare_backfill(tracking, published, tmp_path)
    assert n == 1
    for state in (new_private, new_public["state"]):
        w = state["3"][0]
        assert w["status"] == "WATCH"
        assert w["initial_stop"] == 96
        assert w["breakout_level"] == 100
        assert w["eod_event"] == "EOD_CROSS"
        assert w["eod_volume_ratio"] == 2
        assert w["eod_atr14"] > 0
        assert w["eod_as_of"] == published["metadata"]["as_of_date"]
        assert "trigger_time" not in w and "order_id" not in w
        assert state["2"][0]["manual_reviewer"] == "human"
        assert state["history"] == original_history
        assert state["updatedAt"] == tracking["updatedAt"]
    assert new_public["metadata"] == original_meta
    assert new_public["review_updated_at"] == published["review_updated_at"]
    assert new_public["revision"] == 124
    assert tracking["3"][0].get("eod_as_of") is None
    again_p, again_pub, again_n = prepare_backfill(new_private, new_public, tmp_path)
    assert again_n == 0
    assert again_p == new_private and again_pub == new_public


def test_bad_chart_and_wrong_source_fail_closed(tmp_path):
    tracking, published = fixture(tmp_path)
    chart_path = tmp_path / "ABC.json"
    original = json.loads(chart_path.read_text())
    for change in ({"as_of": "2026-10-22"}, {"adjusted": False},
                   {"interval": "5m"}, {"symbol": "OTHER"}):
        chart_path.write_text(json.dumps({**original, **change}))
        with pytest.raises(ValueError, match="Missing, mismatched or stale chart"):
            prepare_backfill(tracking, published, tmp_path)
    assert published["revision"] == 123


def test_published_or_parent_conflict_aborts_without_mutation(tmp_path):
    tracking, published = fixture(tmp_path)
    prior_t = copy.deepcopy(tracking)
    prior_p = copy.deepcopy(published)
    published["state"]["3"][0]["breakout_level"] = 101
    with pytest.raises(ValueError, match="disagree"):
        prepare_backfill(tracking, published, tmp_path)
    published = copy.deepcopy(prior_p)
    tracking["2"][0]["setup_status"] = "FORMING"
    with pytest.raises(ValueError, match="manually approved READY parent"):
        prepare_backfill(tracking, published, tmp_path)
    assert published == prior_p
    assert prior_t["3"][0]["status"] == "WATCH"


def test_conflicting_saved_eod_metrics_never_overwritten(tmp_path):
    tracking, published = fixture(tmp_path)
    saved_private, saved_public, n = prepare_backfill(tracking, published, tmp_path)
    assert n == 1
    saved_private["3"][0]["eod_close"] = 12345
    saved_public["state"]["3"][0]["eod_close"] = 12345
    with pytest.raises(ValueError, match="Conflicting saved"):
        prepare_backfill(saved_private, saved_public, tmp_path)
