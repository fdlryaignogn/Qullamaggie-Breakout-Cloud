"""Explainable Stage-3 end-of-day breakout observations, NOT intraday trade signals.

EOD snapshots use only complete daily OHLCV candles up to the published
as-of session. A last-session low is a hypothetical stop *reference*, not
a trade recommendation, filled stop, or any inferred entry.
"""
from __future__ import annotations

import math
import pandas as pd


def _rounded(value, places=2):
    value = float(value)
    return round(value, places) if math.isfinite(value) else None


def eod_observation(df: pd.DataFrame, pivot: float, as_of: str) -> dict | None:
    """Return a validated EOD-only WATCH annotation or None for stale/invalid bars.

    ATR14 = arithmetic mean of latest 14 true ranges (requires preceding close).
    ADR20 = arithmetic mean of latest 20 daily (high-low)/low percentages.
    RVOL20 = last completed daily volume / mean of 20 *prior* daily volumes.
    All periods are trading sessions, and values are descriptive only.
    """
    try:
        pivot = float(pivot)
        if not math.isfinite(pivot) or pivot <= 0 or df is None or len(df) < 2:
            return None
        d = df.loc[df.index.strftime("%Y-%m-%d") <= as_of]
        if len(d) < 2 or d.index[-1].strftime("%Y-%m-%d") != as_of:
            return None
        recent=d.iloc[-1]
        prev=d.iloc[-2]
        close, high, low, prev_close = (
            float(recent["close"]),float(recent["high"]),float(recent["low"]),float(prev["close"]))
        if not all(math.isfinite(v) and v > 0 for v in (close, high, low, prev_close)):
            return None
        if low > high or close < low-1e-7 or close > high+1e-7:
            return None
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        return None
    if close > pivot and prev_close <= pivot:
        event = "EOD_CROSS"
    elif close > pivot:
        event = "ABOVE_PIVOT"
    elif high > pivot:
        event = "TOUCH_ONLY"
    else:
        event = "BELOW_PIVOT"
    # Positive distance indicates closing above the level.
    gap = 100*(close/pivot-1)
    result = {
        "eod_as_of": as_of, "eod_data_status": "FRESH",
        "eod_close": _rounded(close,4), "eod_prev_close": _rounded(prev_close,4),
        "eod_high": _rounded(high,4), "eod_low": _rounded(low,4),
        "eod_distance_pct": _rounded(gap),
        "eod_event": event, "eod_volume_ratio": None,
        "eod_atr14": None, "eod_adr20_pct": None,
        "eod_ref_stop": None, "eod_ref_risk_per_share": None,
        "eod_ref_risk_atr": None,
        "eod_note": "Daily data only; EOD_CROSS is not an intraday confirmed trigger or execution."
    }
    # Zero or missing volume is unavailable, not normal/low volume.
    if len(d)>=21:
        try:
            vol=float(d.volume.iloc[-1])
            prior=d.volume.iloc[-21:-1].astype(float)
            if vol>0 and len(prior)==20 and (prior>0).all() and prior.notna().all():
                average=float(prior.mean())
                if average>0 and math.isfinite(average) and math.isfinite(vol):
                    result["eod_volume_ratio"]=_rounded(vol/average)
        except (TypeError,ValueError,AttributeError):
            pass
    if len(d)>=15:
        try:
            last15=d.iloc[-15:]
            ranges=[]
            for k in range(1,len(last15)):
                h,l,c0=(float(last15.high.iloc[k]),float(last15.low.iloc[k]),
                        float(last15.close.iloc[k-1]))
                if not all(math.isfinite(x) and x>0 for x in (h,l,c0)) or h<l:
                    raise ValueError("bad ATR range")
                ranges.append(max(h-l,abs(h-c0),abs(l-c0)))
            result["eod_atr14"]=_rounded(sum(ranges)/14,4)
        except (TypeError,ValueError):
            pass
    if len(d)>=20:
        try:
            last20=d.iloc[-20:]
            vals=[(float(h)-float(l))/float(l)*100 for h,l in zip(last20.high,last20.low)]
            if all(math.isfinite(x) and x>=0 for x in vals):
                result["eod_adr20_pct"]=_rounded(sum(vals)/20)
        except (TypeError,ValueError,ZeroDivisionError):
            pass
    # Pivot entry and the latest candle low are only hypothetical references.
    # Do not set initial_stop, risk_per_share, suggested_max_shares or TRIGGERED.
    if low<pivot:
        result["eod_ref_stop"]=_rounded(low,4)
        result["eod_ref_risk_per_share"]=_rounded(pivot-low,4)
        atr=result["eod_atr14"]
        if atr is not None and atr>0:
            result["eod_ref_risk_atr"]=_rounded((pivot-low)/atr)
    return result


def enrich_stage3_eod(state:dict, frames:dict, as_of:str) -> None:
    """Annotate existing WATCH entries without changing approvals or statuses."""
    parents={x.get("setup_id"):x for x in state.get("2",[])
             if x.get("setup_status")=="READY" and x.get("setup_id")}
    for watch in state.get("3",[]):
        if watch.get("status")!="WATCH":
            continue
        parent=parents.get(watch.get("setup_id"))
        if not parent or parent.get("symbol")!=watch.get("symbol"):
            watch["eod_data_status"]="PAUSED" if not parent else "MISMATCH"
            continue
        sym=watch.get("symbol")
        daily=frames.get(sym)
        pivot=watch.get("breakout_level") or parent.get("base_high")
        result=eod_observation(daily,pivot,as_of)
        if result is None:
            watch["eod_data_status"]="STALE_OR_INSUFFICIENT"
            # Historical metrics remain visibly tagged to the *older* as-of date.
            continue
        watch.update(result)
