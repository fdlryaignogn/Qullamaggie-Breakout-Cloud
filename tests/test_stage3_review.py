"""EOD Stage-3 human actions: authorization, audit, optimistic locking and safety."""
import copy
import json

import pytest

from stage3_review import apply_stage3_action


def fixture(tmp_path):
    state_path = tmp_path / "tracking.json"
    public_path = tmp_path / "latest.json"
    parent = {"symbol": "ABC", "setup_id": "ABC-1", "setup_status": "READY",
              "manual_reviewer": "human", "base_high": 100}
    watch = {"symbol": "ABC", "setup_id": "ABC-1", "status": "WATCH",
             "breakout_level": 100, "eod_as_of": "2026-10-23",
             "eod_close": 100.5, "eod_event": "EOD_CROSS",
             "eod_data_status": "FRESH", "initial_stop": 95}
    state = {"1": [], "2": [parent], "3": [watch], "history": [],
             "updatedAt": "2026-10-23T23:50:00Z"}
    payload = {"state": copy.deepcopy(state), "revision": 120,
               "metadata": {"phase": "success", "as_of_date": "2026-10-23",
                            "last_success": "2026-10-23T23:30:00Z",
                            "scanner_version": "3.1-cloud"},
               "review_updated_at": "2026-10-24T02:00:00Z"}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    public_path.write_text(json.dumps(payload), encoding="utf-8")
    return state_path, public_path


def action(tracking, public, **kwargs):
    defaults = {"symbol": "ABC", "setup_id": "ABC-1", "action": "KEEP_WATCH",
                "note": "Reviewed completed EOD candle; maintain watch",
                "actor": "real-reviewer", "expected_revision": 120,
                "expected_as_of_date": "2026-10-23",
                "review_timestamp": "2026-10-24T11:01:00+00:00"}
    defaults.update(kwargs)
    return apply_stage3_action(tracking, public, **defaults)


def test_keep_watch_updates_audit_not_approval_or_market_scan(tmp_path):
    tracking, public = fixture(tmp_path)
    before = json.loads(public.read_text())
    output = action(tracking, public)
    now = json.loads(public.read_text())
    private = json.loads(tracking.read_text())
    assert output["from"] == output["to"] == "WATCH"
    assert now["metadata"] == before["metadata"]
    assert now["review_updated_at"] == before["review_updated_at"]
    assert now["revision"] == before["revision"] + 1
    assert now["state"]["3"] == private["3"]
    assert now["state"]["2"] == before["state"]["2"]
    assert now["state"]["3"][0]["breakout_level"] == 100
    assert now["state"]["3"][0]["eod_event"] == "EOD_CROSS"
    assert now["state"]["3"][0]["initial_stop"] == 95
    assert "trigger_time" not in now["state"]["3"][0]
    assert now["state"]["history"][0]["reviewer"] == "real-reviewer"
    assert now["state"]["history"][0]["source"].startswith("authenticated GitHub")
    assert now["stage3_review_updated_at"] == "2026-10-24T11:01:00+00:00"


@pytest.mark.parametrize("decision,expected", [("NO_TRADE", "NO_TRADE"), ("ARCHIVE", "ARCHIVED")])
def test_terminal_actions_require_confirmation_and_stay_terminal(tmp_path, decision, expected):
    tracking, public = fixture(tmp_path)
    with pytest.raises(ValueError, match="confirmation"):
        action(tracking, public, action=decision)
    result = action(tracking, public, action=decision, confirmed=True)
    assert result["to"] == expected
    saved = json.loads(public.read_text())
    assert saved["state"]["3"][0]["status"] == expected
    assert saved["state"]["2"][0]["setup_status"] == "READY"
    with pytest.raises(ValueError, match="changed|current WATCH"):
        action(tracking, public, action="KEEP_WATCH", expected_revision=121)


def test_snapshot_revision_or_date_mismatch_fails_without_writes(tmp_path):
    tracking, public = fixture(tmp_path)
    old = tracking.read_bytes(), public.read_bytes()
    with pytest.raises(ValueError, match="snapshot changed"):
        action(tracking, public, expected_revision=119)
    with pytest.raises(ValueError, match="snapshot changed"):
        action(tracking, public, expected_as_of_date="2026-10-22")
    assert old == (tracking.read_bytes(), public.read_bytes())


def test_public_private_disagreement_or_parent_not_ready_rejected(tmp_path):
    tracking, public = fixture(tmp_path)
    data = json.loads(public.read_text())
    data["state"]["3"][0]["breakout_level"] = 200
    public.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="identical tracked"):
        action(tracking, public)
    tracking, public = fixture(tmp_path)
    data = json.loads(public.read_text())
    data["state"]["2"][0]["setup_status"] = "FORMING"
    public.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="approved READY parent"):
        action(tracking, public)


@pytest.mark.parametrize("bad", [
    {"actor": ""}, {"action": "TRIGGERED"}, {"action": "INVALIDATED"},
    {"note": ""}, {"note": "a" * 501}, {"note": "line\ninvalid"},
    {"expected_revision": -1}
])
def test_input_validation_without_state_changes(tmp_path, bad):
    tracking, public = fixture(tmp_path)
    old = tracking.read_bytes(), public.read_bytes()
    with pytest.raises(ValueError):
        action(tracking, public, **bad)
    assert old == (tracking.read_bytes(), public.read_bytes())
