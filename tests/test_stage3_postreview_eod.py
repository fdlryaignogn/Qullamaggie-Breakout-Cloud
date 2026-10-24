"""Post-approval EOD metrics use verified published daily charts only."""
import json
from pathlib import Path

import pandas as pd

from stage3_eod import enrich_from_published_charts
from review_setup import review_setup


def _bars():
    dates = pd.bdate_range("2026-09-01", periods=40)
    bars = []
    for date in dates:
        bars.append({"date": date.strftime("%Y-%m-%d"), "open": 99.5,
                     "high": 101, "low": 98, "close": 99.5, "volume": 100})
    bars[-1].update({"close": 100.5, "high": 102, "volume": 200})
    return bars


def _fixture(tmp_path):
    as_of = _bars()[-1]["date"]
    state = {"1": [], "2": [{
        "symbol": "ABC", "setup_id": "ABC-1", "setup_status": "FORMING",
        "base_high": 100, "readiness_recommendation": "READY_CANDIDATE",
        "readiness_checks": {
            "volatility_contraction": True, "price_structure": True,
            "breakout_proximity": True}}],
        "3": [], "history": []}
    public = {"revision": 100, "state": json.loads(json.dumps(state)),
              "metadata": {"phase": "success", "last_success": "2026-10-23T12:00:00Z",
                           "as_of_date": as_of}}
    state_path = tmp_path / "tracking.json"
    published_path = tmp_path / "data" / "latest.json"
    published_path.parent.mkdir()
    (published_path.parent / "charts").mkdir()
    state_path.write_text(json.dumps(state))
    published_path.write_text(json.dumps(public))
    return as_of, state_path, published_path


def test_review_hydrates_verified_eod_without_fabricated_scan(tmp_path):
    as_of, tracked, published = _fixture(tmp_path)
    chart = {"symbol": "ABC", "as_of": as_of, "interval": "1d",
             "adjusted": True, "bars": _bars()}
    (published.parent / "charts" / "ABC.json").write_text(json.dumps(chart))
    review_setup(tracked, published, symbol="ABC", setup_id="ABC-1",
                 decision="READY", note="Reviewed daily base", actor="tester",
                 confirmed=True, review_timestamp="2026-10-24T01:00:00+00:00")
    doc = json.loads(published.read_text())
    watch = doc["state"]["3"][0]
    assert watch["status"] == "WATCH"
    assert watch["eod_data_status"] == "FRESH"
    assert watch["eod_event"] == "EOD_CROSS"
    assert watch["eod_as_of"] == as_of
    assert watch["eod_volume_ratio"] == 2
    assert watch["eod_atr14"] > 0
    assert watch["eod_adr20_pct"] > 0
    assert "trigger_time" not in watch and "initial_stop" not in watch
    assert doc["metadata"]["last_success"] == "2026-10-23T12:00:00Z"
    assert doc["revision"] == 101


def test_mismatched_or_missing_chart_does_not_fake_metrics(tmp_path):
    as_of, tracked, published = _fixture(tmp_path)
    wrong = {"symbol": "ABC", "as_of": "2026-10-22", "interval": "1d",
             "adjusted": True, "bars": _bars()}
    (published.parent / "charts" / "ABC.json").write_text(json.dumps(wrong))
    review_setup(tracked, published, symbol="ABC", setup_id="ABC-1",
                 decision="READY", note="Reviewed daily base", actor="tester",
                 confirmed=True, review_timestamp="2026-10-24T01:00:00+00:00")
    watch = json.loads(published.read_text())["state"]["3"][0]
    assert watch["eod_data_status"] == "STALE_OR_INSUFFICIENT"
    assert "eod_event" not in watch
    assert watch["status"] == "WATCH"


def test_enrichment_idempotent_and_preserves_approved_fields(tmp_path):
    as_of, _, published = _fixture(tmp_path)
    (published.parent / "charts" / "ABC.json").write_text(json.dumps({
        "symbol": "ABC", "as_of": as_of, "interval": "1d", "adjusted": True,
        "bars": _bars()}))
    state = {"2": [{"symbol": "ABC", "setup_id": "ABC-1", "setup_status": "READY"}],
             "3": [{"symbol": "ABC", "setup_id": "ABC-1", "status": "WATCH",
                    "breakout_level": 100, "initial_stop": 95}]}
    enrich_from_published_charts(state, published.parent / "charts", as_of)
    saved = json.dumps(state, sort_keys=True)
    enrich_from_published_charts(state, published.parent / "charts", as_of)
    assert json.dumps(state, sort_keys=True) == saved
    assert state["3"][0]["initial_stop"] == 95
    assert state["3"][0]["status"] == "WATCH"
