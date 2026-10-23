"""Compact per-ticker OHLCV data for local hover charts (no chart network calls)."""
from __future__ import annotations

import json
import os
from pathlib import Path


def save_price_caches(frames: dict, as_of: str, folder: Path, source: str, limit: int = 180):
    folder.mkdir(parents=True,exist_ok=True)
    for symbol,df in frames.items():
        if not symbol or df.empty:
            continue
        subset=df.loc[df.index.strftime("%Y-%m-%d") <= as_of].tail(limit)
        if subset.empty:
            continue
        bars=[]
        for date,r in subset.iterrows():
            vals=[float(r[c]) for c in ("open","high","low","close")]
            if not all(0 < x < 1e12 for x in vals):
                continue
            bars.append({"date":date.strftime("%Y-%m-%d"),"open":round(vals[0],6),
                         "high":round(vals[1],6),"low":round(vals[2],6),
                         "close":round(vals[3],6),"volume":int(r["volume"])})
        payload={"symbol":symbol,"source":source,"as_of":bars[-1]["date"] if bars else None,
                 "interval":"1d","adjusted":source=="yahoo","bars":bars}
        temp=folder / f"{symbol}.json.tmp"
        temp.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        os.replace(temp,folder / f"{symbol}.json")


def read_price_cache(symbol: str, folder: Path):
    file=folder / f"{symbol}.json"
    if not file.is_file(): return None
    try:
        payload=json.loads(file.read_text(encoding='utf-8'))
        if payload.get("symbol")!=symbol or not isinstance(payload.get("bars"),list):
            return None
        return payload
    except (OSError,ValueError,TypeError):
        return None