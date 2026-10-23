"""Stage 2 V3.1 readiness, authenticated review, and UI regression checks."""
import json
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scanner import setup_evidence, merge_scan
from review_setup import review_setup


def narrowing_base():
    dates = pd.bdate_range("2025-04-01", periods=240)
    prices = np.r_[np.linspace(15, 25, 130), np.linspace(25, 42, 70),
                   np.linspace(40, 42, 40)]
    width = np.r_[np.full(200, .018), np.linspace(.040, .003, 40)]
    high = prices * (1 + width)
    low = prices * (1 - width)
    return pd.DataFrame({"open":prices, "close":prices, "high":high, "low":low,
                         "volume":np.full(240, 300000)}, index=dates)


def test_reference_threshold_is_not_hard_filter():
    df=narrowing_base()
    original=setup_evidence(df)
    assert original is not None
    strict=setup_evidence(df,min_prior_advance=200)
    assert strict is not None
    assert strict["readiness_checks"]["prior_advance"] is False
    assert strict["base_start"]


def test_anchored_setup_keeps_identity_and_does_not_auto_ready():
    df=narrowing_base()
    e=setup_evidence(df)
    assert e is not None
    assert "readiness_checks" in e
    date=df.index[-1].strftime("%Y-%m-%d")
    old={"1":[], "2":[{"symbol":"TEST","setup_id":"TEST-ORIGINAL","setup_status":"FORMING",
          "base_start":e["base_start"],"prior_advance_min_pct":200,
          "base_high":e["base_high"]}], "3":[], "history":[]}
    updated=merge_scan(old, {"TEST":df}, [], {"as_of_date":date})
    candidate=updated["2"][0]
    assert candidate["base_start"] == e["base_start"]
    assert candidate["setup_id"] == "TEST-ORIGINAL"
    assert candidate["setup_status"] == "FORMING"
    assert "readiness_recommendation" in candidate
    assert candidate["prior_advance_min_pct"] == 200
    assert updated["3"] == []


def _state_and_public(tmp):
    state={"1":[], "2":[{"symbol":"TEST","setup_id":"TEST-20261023","setup_status":"FORMING",
        "base_high":42.0,"readiness_recommendation":"READY_CANDIDATE",
        "readiness_score":5,"readiness_checks":{"volatility_contraction":True,
        "price_structure":True,"breakout_proximity":True}}],
        "3":[], "history":[]}
    metadata={"phase":"success","as_of_date":"2026-10-23",
              "last_success":"2026-10-23T23:12:25+00:00"}
    current={"revision":123,"metadata":metadata,"state":json.loads(json.dumps(state))}
    state_path=tmp/"tracking.json";latest_path=tmp/"latest.json"
    state_path.write_text(json.dumps(state));latest_path.write_text(json.dumps(current))
    return state_path,latest_path


def test_ready_requires_explicit_human_review(tmp_path):
    state_path,latest_path=_state_and_public(tmp_path)
    kwargs=dict(symbol="TEST",setup_id="TEST-20261023",decision="READY",
                note="Base and pivot checked",actor="authorized-reviewer")
    with pytest.raises(ValueError,match="confirmed chart review"):
        review_setup(state_path,latest_path,**kwargs)
    assert json.loads(latest_path.read_text())["state"]["3"] == []
    review_setup(state_path,latest_path,confirmed=True,**kwargs,
                 review_timestamp="2026-10-24T01:00:00+00:00")
    cloud=json.loads(latest_path.read_text())
    assert cloud["metadata"]["last_success"] == "2026-10-23T23:12:25+00:00"
    assert cloud["revision"] == 123
    assert cloud["state"]["2"][0]["setup_status"] == "READY"
    assert cloud["state"]["3"][0]["status"] == "WATCH"
    assert cloud["state"]["3"][0]["breakout_level"] == 42.0
    assert "trigger_time" not in cloud["state"]["3"][0]
    assert cloud["state"]["history"][0]["reviewer"] == "authorized-reviewer"


def test_reject_not_ready_candidate_and_missing_authentication(tmp_path):
    state_path,latest_path=_state_and_public(tmp_path)
    payload=json.loads(state_path.read_text())
    payload["2"][0]["readiness_recommendation"]="FORMING"
    state_path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="READY_CANDIDATE"):
        review_setup(state_path,latest_path,symbol="TEST",setup_id="TEST-20261023",
                     decision="READY",note="Checked",actor="reviewer",confirmed=True)
    with pytest.raises(ValueError, match="Authenticated"):
        review_setup(state_path,latest_path,symbol="TEST",setup_id="TEST-20261023",
                     decision="FORMING",note="Wait",actor="")


def test_metric_summary_removed_but_stage_tab_counts_remain():
    html=(Path(__file__).resolve().parents[1]/"site/index.html").read_text()
    assert '<section class="metrics"' not in html
    for n in (1,2,3):
        assert f'id="count{n}"' in html
    assert "readiness_recommendation" in html
