"""Three-stage EOD stock scanner; rules are independent of the HTTP/UI layers.

Momentum is ranked across the whole configured universe. The V2.5 default
is the Nasdaq Trader US-listed equity directory, with explicit coverage checks. Only stage-2 setups reviewed READY by a human can
enter stage 3. With daily OHLCV, stage 3 NEVER marks TRIGGERED automatically.
"""
from __future__ import annotations

import csv
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

LOOKBACKS = {"1m": 21, "3m": 63, "6m": 126}
COLS = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def symbols_from_csv(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or "symbol" not in {x.strip().lower() for x in reader.fieldnames}:
            raise ValueError("Universe CSV requires a 'symbol' header")
        field = next(x for x in reader.fieldnames if x.strip().lower() == "symbol")
        syms = [str(row.get(field) or "").strip().upper() for row in reader]
    syms = list(dict.fromkeys(x for x in syms if x and not x.startswith("#")))
    if not syms or len(syms) > 300:
        raise ValueError("Choose between 1 and 300 ticker symbols (Yahoo rate limits apply)")
    bad = [s for s in syms if not SYMBOL_RE.fullmatch(s)]
    if bad:
        raise ValueError("Invalid symbols: " + ", ".join(bad[:5]))
    return syms


def clean_frame(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        raise ValueError("No OHLCV rows")
    f = raw.copy()
    f.columns = [str(x).strip().lower().replace(" ", "") for x in f.columns]
    if "date" in f.columns:
        f.index = pd.to_datetime(f.pop("date"), errors="coerce", utc=True).dt.tz_convert(None)
    else:
        f.index = pd.to_datetime(f.index, errors="coerce", utc=True).tz_convert(None)
    f = f.loc[f.index.notna()]
    if not {"open", "high", "low", "close", "volume"}.issubset(f.columns):
        raise ValueError("Required columns: Date,Open,High,Low,Close,Volume")
    f = f[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
    f = f[~f.index.duplicated(keep="last")].sort_index()
    valid = f.notna().all(axis=1) & (f[["open", "high", "low", "close"]] > 0).all(axis=1) & (f.volume >= 0)
    valid &= f.high >= f[["open", "low", "close"]].max(axis=1)
    valid &= f.low <= f[["open", "high", "close"]].min(axis=1)
    return f.loc[valid].round(8)


def fetch_csv(symbols: list[str], csvdir: Path):
    frames, errors = {}, {}
    for sym in symbols:
        src = csvdir / (sym.replace("/", "_") + ".csv")
        try:
            frames[sym] = clean_frame(pd.read_csv(src))
        except Exception as ex:
            errors[sym] = f"CSV unavailable / invalid: {ex}"
    return frames, errors


def fetch_yahoo(symbols: list[str], on_progress=None, batch_size=75, pause_seconds=0.4):
    """Download daily OHLCV in batches; report progress and failed symbols.

    Note: yfinance is an unofficial best-effort provider and can rate-limit
    large all-market scans. Invalid/missing symbols are NEVER silently ranked.
    """
    import time
    try:
        import yfinance as yf
    except ImportError as ex:
        raise RuntimeError("Run: python -m pip install -r requirements.txt") from ex
    frames, errors = {}, {}
    total=len(symbols)
    for offset in range(0,total,batch_size):
        batch=symbols[offset:offset+batch_size]
        # Yahoo uses e.g. BRK-B where Nasdaq Trader lists BRK.B.
        aliases={sym:sym.replace('.', '-') for sym in batch}
        raw=None; problem=None
        for retry in range(2):
            try:
                raw=yf.download(tickers=list(aliases.values()), period="1y", interval="1d",
                    group_by="ticker", auto_adjust=True, progress=False,
                    threads=4, timeout=24, multi_level_index=True)
                if raw is not None and not raw.empty:
                    break
                problem='Empty Yahoo response'
            except Exception as ex:
                problem=f'Yahoo download error: {ex}'
            if retry==0: time.sleep(1.5)
        for sym in batch:
            try:
                if raw is None or raw.empty:
                    raise ValueError(problem or 'Empty Yahoo response')
                symbol=aliases[sym]
                sub=raw[symbol] if isinstance(raw.columns,pd.MultiIndex) else raw
                frames[sym]=clean_frame(sub)
                if len(frames[sym]) < 22:
                    raise ValueError('Insufficient 1-month return history')
            except Exception as ex:
                frames.pop(sym,None)
                errors[sym]=f'Yahoo data unavailable: {ex}'
        if on_progress:
            on_progress(offset+len(batch),total,len(frames),len(errors))
        if offset+len(batch)<total and pause_seconds:
            time.sleep(pause_seconds)
    return frames, errors


def compute_momentum(frames: dict, top_fraction: float = .02):
    """Top 1/3/6-month winner UNION, each horizon with its own eligible count.

    21 sessions require >=22 bars, 63 require >=64, 126 require >=127;
    younger IPOs can legitimately qualify in shorter windows. All returns
    have the same as-of date; never fill missing windows with 0% returns.
    """
    if not (0 < top_fraction <= .2):
        raise ValueError('top_fraction must be 0..0.2')
    if not frames:
        raise ValueError('No usable market history received')
    from collections import Counter
    last_dates=[df.index[-1].strftime('%Y-%m-%d') for df in frames.values() if not df.empty]
    if not last_dates:
        raise ValueError('No usable market history received')
    as_of,_=Counter(last_dates).most_common(1)[0]
    current={sym:df for sym,df in frames.items() if not df.empty and
             df.index[-1].strftime('%Y-%m-%d')==as_of}
    rank={} ; counts={} ; winners={} ; info={}
    for period,days in LOOKBACKS.items():
        eligible={s:f for s,f in current.items() if len(f)>days}
        ordered=sorted(((s,100*(float(f.close.iloc[-1])/float(f.close.iloc[-days-1])-1))
                        for s,f in eligible.items()),key=lambda p:(-p[1],p[0]))
        if not ordered:
            raise ValueError(f'No eligible daily returns for {period}')
        count=len(ordered); n=max(1,math.ceil(count*top_fraction))
        counts[period]=count;winners[period]={s for s,_ in ordered[:n]}
        rank[period]={s:(round(change,4),round(100*i/count,4))
                      for i,(s,change) in enumerate(ordered,1)}
    selected=set.union(*winners.values())
    rows=[]
    for sym in sorted(selected):
        row={'symbol':sym,'market':'US','as_of_date':as_of,'status':'ACTIVE',
             'pass_stage_1':'YES','last_screened_date':as_of,'last_pass_date':as_of}
        windows=[]
        for period in LOOKBACKS:
            if sym in rank[period]:
                change,percentile=rank[period][sym]
                row[f'return_{period}']=change
                row[f'rank_pct_{period}']=percentile
            if sym in winners[period]:windows.append(period.upper())
        row['selected_windows']=','.join(windows)
        if any(sym not in rank[period] for period in LOOKBACKS):
            row['data_warnings']='Insufficient price history for some momentum periods (no zero-filled returns)'
        rows.append(row)
    return rows,{'as_of_date':as_of,'eligible':counts['6m'],
                 'eligible_by_window':counts,
                 'per_window_top_count':max(1,math.ceil(counts['6m']*top_fraction)),
                 'per_window_top_counts':{p:len(s) for p,s in winners.items()},
                 'selected':len(rows),'top_fraction':top_fraction,
                 'excluded_incomplete_or_stale':len(frames)-counts['6m'],
                 'excluded_stale':len(frames)-len(current),
                 'rank_definition':'rank / eligible_count per period * 100 (lower = stronger)',
                 'lookbacks':'21/63/126 trading sessions; union of winners'}


DEFAULT_MIN_PRIOR_ADVANCE_PCT = 30.0  # System reference only, not an official mandatory filter.


def prior_advance_before_base(df: pd.DataFrame, base_start, sessions=63):
    """Close-to-close advance over `sessions` sessions ENDING before a base.

    For a base starting at index B, use closes[B-64] and closes[B-1].
    No base-day or subsequent data are included. Missing data returns None.
    """
    if not base_start or len(df) < sessions + 1:
        return None
    try:
        start = pd.Timestamp(base_start)
    except (TypeError, ValueError):
        return None
    before = df[df.index < start]
    if len(before) < sessions + 1:
        return None
    window = before.iloc[-sessions-1:]
    first = float(window.close.iloc[0])
    last = float(window.close.iloc[-1])
    if first <= 0 or not math.isfinite(first) or not math.isfinite(last):
        return None
    return {
        'prior_advance_pct': round(100 * (last / first - 1), 2),
        'prior_advance_days': sessions,
        'prior_advance_start': window.index[0].strftime('%Y-%m-%d'),
        'prior_advance_end': window.index[-1].strftime('%Y-%m-%d'),
    }


def setup_evidence(df: pd.DataFrame, base_start=None, min_prior_advance=DEFAULT_MIN_PRIOR_ADVANCE_PCT):
    """Daily, explainable setup assessment; never grants trading approval.

    Existing setups use their persisted base_start so the identity cannot drift
    when the candidate falls out of Stage 1. The latest day is not included in
    resistance or contraction measurements, avoiding lookahead.
    """
    if len(df) < 110:
        return None
    choices = []
    if base_start:
        try:
            anchored = df[(df.index >= pd.Timestamp(base_start)) & (df.index < df.index[-1])]
        except (ValueError, TypeError):
            return None
        if len(anchored) < 10:
            return None
        choices = [anchored]
    else:
        choices = [df.iloc[-n-1:-1] for n in (10, 15, 20, 30, 40)]
    options = []
    for base in choices:
        n = len(base)
        if n < 10:
            continue
        advance = prior_advance_before_base(df, base.index[0])
        if advance is None:
            continue
        gain = advance['prior_advance_pct']
        high = float(base.high.max())
        low = float(base.low.min())
        price = float(df.close.iloc[-1])
        pullback = 100 * (high - low) / high
        early = (base.high.iloc[:5] - base.low.iloc[:5]) / base.close.iloc[:5]
        late = (base.high.iloc[-5:] - base.low.iloc[-5:]) / base.close.iloc[-5:]
        contraction = float(early.mean()) > 0 and float(late.mean()) < float(early.mean()) * .85
        higher_lows = float(base.low.iloc[n//2:].min()) > float(base.low.iloc[:n//2].min())
        location = (price - low) / (high - low) if high > low else 0
        ma20 = float(df.close.iloc[-20:].mean())
        ma50 = float(df.close.iloc[-50:].mean())
        near_ma = price >= .95 * ma20 and ma20 >= .97 * ma50
        # 30% is only a reference score. Structure, not prior gain, decides
        # whether a new candidate enters FORMING.
        if not base_start and not (4 <= pullback <= 35 and .50 <= location <= 1.15 and near_ma):
            continue
        proximity = .94 * high <= price <= 1.03 * high
        checks = {
            'prior_advance': gain >= min_prior_advance,
            'base_quality': 10 <= n <= 40 and 4 <= pullback <= 35,
            'volatility_contraction': bool(contraction),
            'price_structure': bool(higher_lows and near_ma),
            'breakout_proximity': bool(proximity),
        }
        score = sum(checks.values())
        candidate = score >= 4 and checks['volatility_contraction'] and checks['price_structure'] and checks['breakout_proximity']
        options.append((score, int(candidate), int(gain >= min_prior_advance), n, base,
                        advance, high, low, pullback, higher_lows, contraction, price, ma20, ma50, checks, candidate))
    if not options:
        return None
    (score, _, _, n, b, advance, hi, lo, depth, higher, contract, price,
     ma20, ma50, checks, candidate) = max(options, key=lambda x: (x[1], x[0], x[2], x[3]))
    recommendation = 'READY_CANDIDATE' if candidate else 'FORMING'
    missing = ', '.join(k for k, ok in checks.items() if not ok) or 'none'
    return {
        **advance,
        'prior_advance_min_pct': min_prior_advance,
        'base_start': b.index[0].strftime('%Y-%m-%d'),
        'base_end': b.index[-1].strftime('%Y-%m-%d'),
        'base_length_days': n,
        'base_high': round(hi, 4),
        'base_low': round(lo, 4),
        'pullback_pct': round(depth, 2),
        'higher_lows': 'YES' if higher else 'NO',
        'volatility_contraction': 'YES' if contract else 'NO',
        'moving_average_context': f'close={price:.2f}, SMA20={ma20:.2f}, SMA50={ma50:.2f}',
        'readiness_score': score,
        'readiness_checks': checks,
        'readiness_recommendation': recommendation,
        'readiness_rationale': f'{score}/5 prototype checks; unmet: {missing}. Human review required; no automated READY.',
        'rationale': 'Algorithmic setup evaluation; breakout level and pattern require human chart review.',
        '_heuristic_score': score,
    }

def merge_scan(state: dict, frames: dict, rows: list[dict], meta: dict) -> dict:
    """Merge automated scan into long-lived tracking. Never reset READY or TRIGGERED."""
    state = {**state, "1":[dict(x) for x in state.get("1",[])],
             "2":[dict(x) for x in state.get("2",[])],
             "3":[dict(x) for x in state.get("3",[])],
             "history":list(state.get("history",[]))}
    as_of=meta["as_of_date"]
    captured=utcnow()
    newmap={r["symbol"]:r for r in rows}
    stage1={r["symbol"]:r for r in state["1"] if r.get("symbol")}
    for sym, previous in stage1.items():
        if sym in frames and sym not in newmap and previous.get("status") not in ("ARCHIVED",):
            previous["status"]="ARCHIVED"
            previous["last_screened_date"]=as_of
            previous["status_reason"]="Exited current momentum top-percentile union; stage-2 state remains independent"
            state["history"].insert(0,{"when":captured,"stage":1,"symbol":sym,"from":"ACTIVE","to":"ARCHIVED","reason":"No longer current momentum winner"})
    for r in rows:
        sym=r["symbol"]
        if sym in stage1:
            old=stage1[sym];old.update(r)
            old.setdefault("first_seen_date",as_of)
            old["last_pass_date"]=as_of
        else:
            r["first_seen_date"]=as_of;r["_updated_at"]=captured
            state["1"].append(r)
            state["history"].insert(0,{"when":captured,"stage":1,"symbol":sym,"from":"","to":"ACTIVE","reason":"New union-of-ranks winner"})
    active2={r.get("symbol"):r for r in state["2"] if str(r.get("setup_status","")).upper() not in ("ARCHIVED","INVALIDATED","REJECT")}
    for sym in sorted(set(newmap)|set(active2)):
        df=frames.get(sym)
        current=active2.get(sym)
        if df is None or df.empty:
            if current:
                current['readiness_recommendation'] = 'INSUFFICIENT_DATA'
                current['readiness_rationale'] = 'No current price data; retain setup, suspend automatic recommendation.'
            continue
        df = df.loc[df.index.strftime("%Y-%m-%d") <= as_of]
        if df.empty or df.index[-1].strftime("%Y-%m-%d")!=as_of:
            if current:
                current['readiness_recommendation'] = 'INSUFFICIENT_DATA'
                current['readiness_rationale'] = 'Price history stale; setup kept for review.'
            continue
        try:
            minimum=float(current.get('prior_advance_min_pct') or DEFAULT_MIN_PRIOR_ADVANCE_PCT) if current else DEFAULT_MIN_PRIOR_ADVANCE_PCT
        except (ValueError, TypeError):
            minimum=DEFAULT_MIN_PRIOR_ADVANCE_PCT
        evidence=setup_evidence(df, base_start=current.get('base_start') if current else None,
                                min_prior_advance=minimum)
        if current is not None:
            current["last_reviewed_at"]=as_of
            current["as_of_date"]=as_of
            current["_scanned_at"]=captured
            previous_recommendation=current.get('readiness_recommendation')
            if evidence:
                current.update({k:v for k,v in evidence.items()
                                if k.startswith('readiness_')})
                # Human READY levels are immutable during automated scans.
                # FORMING levels evolve only within the original anchored base.
                if current.get("setup_status") != "READY":
                    saved_min = current.get('prior_advance_min_pct')
                    saved_start = current.get('base_start')
                    current.update({k:v for k,v in evidence.items()
                                    if not k.startswith("_") and not k.startswith('readiness_')
                                    and k not in ('base_start', 'prior_advance_min_pct')})
                    if not saved_start:
                        current['base_start'] = evidence['base_start']
                    if saved_min is not None and str(saved_min).strip():
                        current['prior_advance_min_pct'] = saved_min
                current['algorithm_evidence'] = evidence['readiness_rationale']
            else:
                current['readiness_recommendation'] = 'INSUFFICIENT_DATA'
                current['readiness_score'] = None
                current['readiness_checks'] = {}
                current['readiness_rationale'] = 'Anchored base cannot be evaluated; keep setup and request manual review.'
                current["algorithm_evidence"] = current['readiness_rationale']
            if previous_recommendation != current.get('readiness_recommendation'):
                state['history'].insert(0, {'when':captured,'stage':2,'symbol':sym,
                    'setup_id':current.get('setup_id'),'from':previous_recommendation or '',
                    'to':current['readiness_recommendation'],'reason':'Automated recommendation only; approval unchanged'})
            # Existing human-approved READY bases can retain their original base_start
            # and be safely backfilled without moving the window forward in time.
            if not str(current.get('prior_advance_pct') or '').strip() and current.get('base_start'):
                anchored = prior_advance_before_base(df, current['base_start'])
                if anchored:
                    current.update(anchored)
            current.setdefault('prior_advance_min_pct', DEFAULT_MIN_PRIOR_ADVANCE_PCT)
            continue
        if sym not in newmap or not evidence:
            continue
        setup_id=f"{sym}-{as_of.replace('-','')}"
        used={x.get("setup_id") for x in state["2"]}
        suffix=2
        root=setup_id
        while setup_id in used:
            setup_id=f"{root}-{suffix}"; suffix+=1
        entry={"symbol":sym,"setup_id":setup_id,"as_of_date":as_of,"first_seen_date":as_of,
               "setup_status":"FORMING","last_reviewed_at":as_of,"status_reason":"Heuristic candidate; manual chart review required",
               "_updated_at":captured,"_scanned_at":captured,**evidence}
        state["2"].append(entry)
        state["history"].insert(0,{"when":captured,"stage":2,"symbol":sym,"setup_id":setup_id,"from":"","to":"FORMING","reason":"Proposed by base heuristic; not manually READY"})
    existing3={x.get("setup_id"):x for x in state["3"]}
    for parent in state["2"]:
        if parent.get("setup_status")!="READY":
            continue
        id_=parent.get("setup_id");sym=parent.get("symbol")
        if not id_ or not sym or sym not in frames:
            continue
        d=frames[sym]
        d=d.loc[d.index.strftime("%Y-%m-%d") <= as_of]
        if len(d)<2 or d.index[-1].strftime("%Y-%m-%d")!=as_of:
            continue
        try:
            level=float(parent["base_high"])
            if level<=0: continue
        except (ValueError,TypeError,KeyError):
            continue
        latest=float(d.close.iloc[-1]);prior=float(d.close.iloc[-2])
        candidate = latest>level and prior<=level
        note=(f"UNCONFIRMED EOD BREAKOUT CANDIDATE: close {latest:.4f} > base high {level:.4f}; "
              "daily candles cannot validate intraday trigger/time. Human verification required."
              if candidate else f"EOD WATCH: close {latest:.4f}, base high {level:.4f}; no confirmed intraday trigger.")
        if id_ in existing3:
            watch=existing3[id_]
            if watch.get("status") in ("TRIGGERED","ARCHIVED","INVALIDATED","NO_TRADE"):
                continue
            watch.update({"setup_status":"READY","trade_date":as_of,"last_reviewed_at":as_of,
                          "status_reason":note,"rationale":note,"_scanned_at":captured})
            # Don't override trader's breakout level or make up a stop/trigger timestamp.
            continue
        watch={"symbol":sym,"setup_id":id_,"watch_date":as_of,"trade_date":as_of,"setup_status":"READY",
               "breakout_level":round(level,4),"status":"WATCH","status_reason":note,"rationale":note,
               "last_reviewed_at":as_of,"_updated_at":captured,"_scanned_at":captured}
        state["3"].append(watch)
        state["history"].insert(0,{"when":captured,"stage":3,"symbol":sym,"setup_id":id_,"from":"","to":"WATCH","reason":"Human READY setup entered EOD watch"})
    # Calculate descriptive EOD metrics for each persistent Stage-3 WATCH.
    # Never auto-trigger, auto-trade, change an approved pivot, or use future bars.
    from stage3_eod import enrich_stage3_eod
    enrich_stage3_eod(state, frames, as_of)
    state["history"]=state["history"][:1000]
    state["updatedAt"]=captured
    return state