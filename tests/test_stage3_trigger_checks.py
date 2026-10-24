"""End-of-day trigger is an authenticated EOD *signal* confirmation only."""
import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from stage3_eod import eod_observation
from stage3_review import apply_stage3_action
from stage3_trigger_checks import assess_eod_trigger, EOD_RULE


def fixture(tmp_path, *, review_at="2026-10-23T19:00:00+00:00",
            prior_close=99.5, last_close=100.5, volume=200):
    as_of = "2026-10-23"
    ix = pd.bdate_range(end=as_of, periods=40)
    df = pd.DataFrame({
        "open": [99.5]*40, "high": [101.0]*40, "low": [98.0]*40,
        "close": [99.5]*40, "volume": [100]*40,
    }, index=ix)
    df.loc[ix[-2],"close"] = prior_close
    df.loc[ix[-1],["close","high","low","volume"]] = [last_close,102.0,98.0,volume]
    metric = eod_observation(df,100,as_of)
    chart = {"symbol": "ABC", "as_of": as_of, "interval": "1d",
             "adjusted": True,
             "bars": [{"date": d.strftime("%Y-%m-%d"), **{
                 k: float(df.loc[d,k]) for k in ("open","high","low","close","volume")}}
                 for d in ix]}
    charts = tmp_path / "charts"
    charts.mkdir(exist_ok=True)
    (charts/"ABC.json").write_text(json.dumps(chart), encoding="utf-8")
    parent = {"setup_id":"ABC-1","symbol":"ABC","setup_status":"READY",
              "manual_reviewer":"trusted-reviewer","manual_reviewed_at":review_at,
              "base_high":100.0}
    watch = {"setup_id":"ABC-1","symbol":"ABC","status":"WATCH",
             "breakout_level":100.0, **metric}
    tracking = {"1":[],"2":[parent],"3":[watch],"history":[]}
    published = {"revision":120,"running":False,
                 "metadata":{"phase":"success","as_of_date":as_of,
                             "last_success":"2026-10-23T23:12:25Z"},
                 "state":copy.deepcopy(tracking)}
    t = tmp_path/"tracking.json"
    p = tmp_path/"latest.json"
    t.write_text(json.dumps(tracking), encoding="utf-8")
    p.write_text(json.dumps(published), encoding="utf-8")
    return t,p,chart


def act(t,p,**kwargs):
    opts={"symbol":"ABC","setup_id":"ABC-1","action":"CONFIRM_EOD_TRIGGER",
          "note":"Confirmed price close-cross with validated EOD daily chart",
          "actor":"trusted-reviewer","expected_revision":120,
          "expected_as_of_date":"2026-10-23","confirmed":True,
          "review_timestamp":"2026-10-24T10:00:00+00:00"}
    opts.update(kwargs)
    return apply_stage3_action(t,p,**opts)


def test_manual_eod_trigger_is_persisted_once_without_fill_or_new_scan(tmp_path):
    t,p,_=fixture(tmp_path)
    previous=json.loads(p.read_text())
    result=act(t,p)
    saved=json.loads(p.read_text())
    row=saved["state"]["3"][0]
    assert result["from"]=="WATCH" and result["to"]=="TRIGGERED"
    assert row["trigger_rule"]==EOD_RULE
    assert row["triggered_at"]=="2026-10-24T10:00:00+00:00"
    assert row["eod_trigger_as_of"]=="2026-10-23"
    assert row["eod_trigger_close"]==100.5
    assert row["eod_trigger_evidence"]["eod_event"]=="EOD_CROSS"
    assert row["status"]=="TRIGGERED"
    assert row["eod_trigger_evidence"]["rvol20"]==2
    assert saved["state"]["history"][0]["action"]=="CONFIRM_EOD_TRIGGER"
    assert saved["state"]["history"][0]["trigger_session"]=="2026-10-23"
    assert saved["revision"]==previous["revision"]+1
    assert saved["metadata"]==previous["metadata"]
    assert saved["state"]["2"]==previous["state"]["2"]
    assert json.loads(t.read_text())["3"]==saved["state"]["3"]
    assert not {"trigger_time","entry_price","fill_price","order_id"} & set(row)
    with pytest.raises(ValueError,match="WATCH"):
        act(t,p,expected_revision=121)


@pytest.mark.parametrize("time_stamp", [
    "2026-10-24T05:56:07+00:00", # 2026-10-24 01:56 in New York
    "2026-10-24T00:01:00-04:00",
    "2026-10-23T14:00:00",       # naive
])
def test_approval_later_than_eod_session_or_naive_is_ineligible(tmp_path,time_stamp):
    t,p,_=fixture(tmp_path,review_at=time_stamp)
    before=t.read_bytes(),p.read_bytes()
    parent=json.loads(t.read_text())["2"][0]
    watch=json.loads(t.read_text())["3"][0]
    metadata=json.loads(p.read_text())["metadata"]
    check=assess_eod_trigger(parent,watch,metadata,tmp_path/"charts")
    assert not check["allowed"]
    with pytest.raises(ValueError,match="requirements not met"):
        act(t,p)
    assert (t.read_bytes(),p.read_bytes())==before


def test_missing_chart_fails_without_changing_state(tmp_path):
    t,p,_=fixture(tmp_path)
    (tmp_path/"charts"/"ABC.json").unlink()
    before=t.read_bytes(),p.read_bytes()
    with pytest.raises(ValueError,match="VERIFIED_DAILY_CHART"):
        act(t,p)
    assert (t.read_bytes(),p.read_bytes())==before


def test_wrong_adjustment_or_chart_date_fails_closed(tmp_path):
    t,p,chart=fixture(tmp_path)
    c=tmp_path/"charts"/"ABC.json"
    for change in ({"adjusted":False},{"interval":"5m"},
                   {"as_of":"2026-10-22"},{"symbol":"DEF"}):
        c.write_text(json.dumps({**chart,**change}))
        with pytest.raises(ValueError,match="VERIFIED_DAILY_CHART"):
            act(t,p)


def test_non_cross_or_conflicting_saved_eod_rejected(tmp_path):
    t,p,chart=fixture(tmp_path,prior_close=101,last_close=101)
    # Already above pivot, no fresh upward close-cross this EOD.
    check=assess_eod_trigger(json.loads(t.read_text())["2"][0],
                             json.loads(t.read_text())["3"][0],
                             json.loads(p.read_text())["metadata"],tmp_path/"charts")
    assert not check["allowed"]
    assert any(c["code"]=="EOD_CLOSE_CROSS" and not c["pass"] for c in check["checks"])
    with pytest.raises(ValueError,match="EOD_CLOSE_CROSS"):
        act(t,p)

    t,p,_=fixture(tmp_path)
    v=json.loads(t.read_text());q=json.loads(p.read_text())
    v["3"][0]["eod_close"]=999
    q["state"]["3"][0]["eod_close"]=999
    t.write_text(json.dumps(v));p.write_text(json.dumps(q))
    with pytest.raises(ValueError,match="SAVED_EOD_MATCH"):
        act(t,p)


def test_no_volume_ratio_is_context_unknown_not_hard_trigger_block(tmp_path):
    t,p,_=fixture(tmp_path,volume=0)
    row=json.loads(t.read_text())["3"][0]
    assert row["eod_volume_ratio"] is None
    result=act(t,p)
    assert result["to"]=="TRIGGERED"
    eod=json.loads(p.read_text())["state"]["3"][0]["eod_trigger_evidence"]
    assert eod["rvol20"] is None


def test_trigger_requires_explicit_confirmation(tmp_path):
    t,p,_=fixture(tmp_path)
    before=t.read_bytes(),p.read_bytes()
    with pytest.raises(ValueError,match="confirmation"):
        act(t,p,confirmed=False)
    assert (t.read_bytes(),p.read_bytes())==before
