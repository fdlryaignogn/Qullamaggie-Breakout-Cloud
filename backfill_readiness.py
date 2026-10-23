"""One-time V3.1 readiness backfill from already verified public EOD chart caches.

This does not fetch new market data or alter the previous successful scan time.
It only evaluates existing tracked setups from the same verified market date.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from scanner import clean_frame, merge_scan
from server import DATA, ROOT, persist

LATEST=ROOT / "site/data/latest.json"
CHARTS=ROOT / "site/data/charts"


def backfill() -> int:
    published=json.loads(LATEST.read_text(encoding="utf-8"))
    meta=published.get("metadata") or {}
    if meta.get("phase") != "success" or meta.get("last_scan_universe_mode") != "us":
        raise RuntimeError("Cannot backfill without a verified published US scan")
    as_of=meta["as_of_date"]
    state=json.loads((DATA / "tracking_state.json").read_text(encoding="utf-8"))
    target=[r for r in state.get("2",[]) if
            r.get("setup_status") not in ("ARCHIVED","INVALIDATED","REJECT") and
            not (r.get("last_reviewed_at")==as_of and r.get("readiness_recommendation"))]
    frames={}
    for row in target:
        sym=row.get("symbol")
        path=CHARTS / (str(sym) + ".json")
        if not path.exists(): continue
        try:
            payload=json.loads(path.read_text(encoding="utf-8"))
            if payload.get("as_of") != as_of or payload.get("symbol") != sym:
                continue
            frame=clean_frame(pd.DataFrame(payload["bars"]))
            if frame.index[-1].strftime("%Y-%m-%d") == as_of:
                frames[sym]=frame
        except (ValueError, TypeError, KeyError):
            continue
    if not frames:
        return 0
    # Pass the existing active stage-1 rows unchanged; backfill must not archive
    # any momentum winners or re-rank based on a subset of cached charts.
    winners=[dict(x) for x in state.get("1",[]) if x.get("status")!="ARCHIVED"]
    updated=merge_scan(state,frames,winners,{"as_of_date":as_of})
    updated["1"]=state["1"]
    before=sum(bool(x.get("readiness_recommendation")) for x in state.get("2",[]))
    after=sum(bool(x.get("readiness_recommendation")) for x in updated.get("2",[]))
    if after <= before:
        return 0
    persist(updated)
    public_state=published["state"]
    bad_fields={"api_key","secret","password","account_number","account_balance",
                "equity","risk_fraction"}
    for key in ("2","3"):
        public_state[key]=[{k:v for k,v in row.items() if k not in bad_fields}
                           for row in updated.get(key,[])]
    public_state["history"]=[{k:v for k,v in row.items() if k not in bad_fields}
                             for row in updated["history"]]
    public_state["updatedAt"]=updated["updatedAt"]
    published["revision"] = int(published.get("revision") or 0) + 1
    published["readiness_updated_at"]=datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Preserve last_success and as_of_date: no fabricated new scan notification.
    temp=LATEST.with_suffix(".json.tmp")
    temp.write_text(json.dumps(published,ensure_ascii=False,allow_nan=False,indent=2),encoding="utf-8")
    temp.replace(LATEST)
    return after-before


if __name__=="__main__":
    print(f"Backfilled readiness on {backfill()} existing setups")
