"""Local-only dashboard + daily scanner (stdlib HTTP server).

Run on your own machine. Do not expose this unauthenticated service to the internet.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import threading
import time
import webbrowser
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from pathlib import Path
from zoneinfo import ZoneInfo

from scanner import (compute_momentum, fetch_csv, fetch_yahoo,
                     merge_scan, symbols_from_csv, utcnow, SYMBOL_RE)
from chart_cache import save_price_caches, read_price_cache
from us_universe import get_us_equities

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STATE_PATH = DATA / "tracking_state.json"
METADATA_PATH = DATA / "scan_metadata.json"
STATE_LOCK = threading.RLock()
MAX_BODY = 6_000_000
SCAN_MIN_INTERVAL = timedelta(hours=24)
SCANNER_VERSION = "3.1"
MIN_MARKET_COVERAGE = .90  # full-US ranking must have >=90% quote coverage


def scan_cooldown_until(last_success, now=None):
    """UTC instant at which a new scan is allowed, or None.

    Only a successful completed scan starts the 24-hour window. Failed runs,
    browser edits and malformed timestamps do not advance this clock.
    """
    if not isinstance(last_success, str) or not last_success.strip():
        return None
    try:
        finished = datetime.fromisoformat(last_success.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if finished.tzinfo is None or finished.utcoffset() is None:
        return None
    now = now or datetime.now(timezone.utc)
    finished = finished.astimezone(timezone.utc)
    now = now.astimezone(timezone.utc)
    # Bad/future timestamps must not suppress scanning indefinitely.
    if finished > now + timedelta(minutes=5):
        return None
    until = finished + SCAN_MIN_INTERVAL
    return until if now < until else None


def empty_state():
    return {"1":[], "2":[], "3":[], "history":[], "updatedAt":None}


def load_state():
    if not STATE_PATH.exists():
        return empty_state()
    raw=json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw,dict):
        raise ValueError("Stored state must be an object")
    for k in ("1","2","3","history"):
        if not isinstance(raw.get(k),list):
            raise ValueError("Stored state has invalid section " + k)
    return raw


def persist(state):
    DATA.mkdir(parents=True, exist_ok=True)
    tmp=STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    os.replace(tmp,STATE_PATH)


def validate_incoming(x):
    if not isinstance(x,dict):
        raise ValueError("Expected data object")
    out={}
    for key in ("1","2","3","history"):
        rows=x.get(key,[])
        if not isinstance(rows,list) or len(rows)>10_000:
            raise ValueError("Invalid or oversized section "+key)
        if any(not isinstance(r,dict) for r in rows):
            raise ValueError("Section requires records")
        out[key]=rows
    out["updatedAt"]=x.get("updatedAt")
    return out


def expected_last_session(now_ny: datetime) -> str:
    """Most recent US weekday session expected to have EOD prices.

    Intentionally not an exchange-holiday calendar: holiday data may be unchanged.
    Data publication safety cutoff is NY 18:30. If market data are late,
    users can press Run Scan manually.
    """
    from datetime import timedelta
    dt = now_ny.date()
    if (now_ny.hour, now_ny.minute) < (18, 30):
        dt -= timedelta(days=1)
    while dt.weekday() >= 5:
        dt -= timedelta(days=1)
    return dt.isoformat()


class Store:
    def __init__(self, universe, provider="yahoo", top_fraction=.02, auto=True, csvdir=None, universe_mode="file"):
        self.universe=Path(universe)
        if universe_mode not in ("us", "file"):
            raise ValueError("universe_mode must be us or file")
        self.universe_mode=universe_mode
        self.provider=provider
        self.top_fraction=top_fraction
        self.auto=auto
        self.csvdir=Path(csvdir) if csvdir else DATA / "csv"
        self.lock=STATE_LOCK
        self.state=load_state()
        self.revision=1
        self.running=False
        self.metadata={"phase":"idle","last_success":None,"last_error":None,"last_attempt":None,
                       "startup_action":"pending",
                       "source":provider,"universe_file":self.universe.name}
        if METADATA_PATH.exists():
            try:
                prior=json.loads(METADATA_PATH.read_text(encoding="utf-8"))
                if isinstance(prior,dict): self.metadata.update(prior)
            except Exception: logging.warning("Ignored malformed scan_metadata.json")
        self.metadata["phase"]="idle"
        self.metadata["universe_mode"] = self.universe_mode
        self.metadata["scanner_version"] = SCANNER_VERSION
        self.scheduler_thread=None

    def snapshot(self):
        with self.lock:
            metadata=deepcopy(self.metadata)
            next_allowed=scan_cooldown_until(metadata.get("last_success"))
            metadata["cooldown_until"] = next_allowed.isoformat() if next_allowed else None
            return {"state":deepcopy(self.state),"revision":self.revision,"metadata":metadata}

    def replace(self,data,revision):
        validated=validate_incoming(data)
        with self.lock:
            if revision != self.revision:
                return False,self.snapshot()
            self.state=validated
            self.state["updatedAt"]=utcnow()
            self.revision+=1
            persist(self.state)
            return True,self.snapshot()

    def launch_scan(self):
        with self.lock:
            if self.running:
                self.metadata["scan_skip_reason"] = "running"
                return False
            if scan_cooldown_until(self.metadata.get("last_success")):
                self.metadata["scan_skip_reason"] = "cooldown"
                logging.info("Scan skipped: last successful scan is less than 24 hours old")
                return False
            self.running=True
            self.metadata.update({"phase":"running","last_attempt":utcnow(),
                                  "last_error":None,"scan_skip_reason":None})
        threading.Thread(target=self._scan_worker,daemon=True,name="QullaScan").start()
        return True

    def _progress(self, done, total, downloaded, errors):
        with self.lock:
            self.metadata['progress']={
                'phase':'downloading', 'done':done,'total':total,
                'downloaded':downloaded,'failed':errors,
                'pct':round(100*done/max(1,total),1)}

    def _scan_worker(self):
        try:
            listing={}
            with self.lock:
                self.metadata['progress']={'phase':'loading_universe','done':0,'total':0,'pct':0}
            if self.universe_mode == 'us':
                symbols,listing=get_us_equities(DATA / 'listing_cache')
                logging.info('US equity universe from Nasdaq Trader: %s listed symbols',len(symbols))
            else:
                symbols=symbols_from_csv(self.universe)
                listing={'universe_scope':'User-supplied custom CSV watch universe (not full US market)',
                         'listing_cached':False,'filtered_equities':len(symbols)}
            with self.lock:
                self.metadata['progress']={'phase':'downloading','done':0,'total':len(symbols),'pct':0}
                self.metadata['universe_target_size']=len(symbols)
                self.metadata['universe_target_mode']=self.universe_mode
            if self.provider=='csv':
                frames,errors=fetch_csv(symbols,self.csvdir)
                self._progress(len(symbols),len(symbols),len(frames),len(errors))
            else:
                frames,errors=fetch_yahoo(symbols,on_progress=self._progress,
                                          batch_size=75 if self.universe_mode=='us' else 25)
            completeness=len(frames)/len(symbols)
            required_coverage=MIN_MARKET_COVERAGE if self.universe_mode=='us' else .80
            if completeness<required_coverage:
                raise RuntimeError(f'Yahoo/CSV daily data coverage only {len(frames)}/{len(symbols)} = {completeness:.1%}; '
                                   f'minimum {required_coverage:.0%} required for credible ranks. '
                                   f'This is not a full-US-market result. Sample failures: {dict(list(errors.items())[:4])}')
            with self.lock:
                self.metadata['progress']={'phase':'ranking','done':len(symbols),'total':len(symbols),'pct':100}
            rows,meta=compute_momentum(frames,self.top_fraction)
            eligible_coverage=meta['eligible_by_window']['1m']/len(symbols)
            if eligible_coverage < required_coverage:
                raise RuntimeError(f'Only {meta["eligible_by_window"]["1m"]}/{len(symbols)} stocks have '
                                   f'21-session returns on the same as-of date; less than {required_coverage:.0%}. '
                                   'Incomplete market-wide data: results not published.')
            meta.update({'source':self.provider,'universe_mode':self.universe_mode,
                         'last_scan_universe_mode':self.universe_mode,
                         'universe_file':self.universe.name if self.universe_mode=='file' else 'Nasdaq Trader: nasdaqlisted + otherlisted',
                         'universe_size':len(symbols),'downloaded':len(frames),
                         # Detailed per-ticker failures can be thousands of entries;
                         # keep summary metadata bounded for browser and disk.
                         'download_error_count':len(errors),'download_error_sample':dict(list(errors.items())[:20]),
                         'coverage':round(eligible_coverage,4),'market_coverage_pct':round(100*eligible_coverage,1),
                         'completed_at':utcnow(), 'listing_info':listing,
                         'limitations':'US-listed equities, not OTC; yfinance is unofficial and may rate-limit. '
                                       'No investment advice. Stage-2 READY and stage-3 TRIGGERED require human review.'})
            with self.lock:
                self.state=merge_scan(self.state,frames,rows,meta)
                self.revision+=1
                persist(self.state)
                self.metadata.update(meta)
                self.metadata.update({'phase':'success','last_success':utcnow(),
                                      'last_error':None,'progress':None})
                symbols_for_charts={r.get('symbol') for st in ('1','2','3') for r in self.state.get(st,[])
                                    if r.get('symbol') and
                                    (st=='1' and r.get('status')!='ARCHIVED' or st!='1')}
            try:
                # All-US scanning may contain many thousands of equities: do
                # not create a price JSON file for each name, only tracked ones.
                save_price_caches({sym:frames[sym] for sym in symbols_for_charts if sym in frames},
                                  as_of=meta['as_of_date'],folder=DATA / 'price_cache',source=self.provider)
            except Exception:
                logging.exception('Chart cache update failed; scan records preserved')
        except Exception as ex:
            logging.exception('Scan unsuccessful')
            with self.lock:
                self.metadata.update({'phase':'error','last_error':str(ex),'progress':None})
        finally:
            with self.lock:
                self.running=False
                try:
                    METADATA_PATH.parent.mkdir(parents=True,exist_ok=True)
                    temp=METADATA_PATH.with_suffix('.tmp')
                    temp.write_text(json.dumps(self.metadata,ensure_ascii=False,indent=2),encoding='utf-8')
                    os.replace(temp,METADATA_PATH)
                except Exception: logging.exception('Failed to save scan metadata')

    def startup_scan(self):
        """One-click startup: avoid a full download when cached EOD is current.

        When outdated, launch in background; serving and browser opening do not
        wait for Yahoo download. This check is weekday-based, not holiday-aware.
        """
        if not self.auto:
            with self.lock: self.metadata["startup_action"] = "disabled"
            return False
        target=expected_last_session(datetime.now(ZoneInfo("America/New_York")))
        with self.lock:
            # 24 hours is a hard lower bound, including if EOD is stale or
            # a chart cache is missing. Fresh scans are never run unnecessarily.
            if scan_cooldown_until(self.metadata.get("last_success")):
                self.metadata["startup_action"] = "cooldown"
                self.metadata["scan_skip_reason"] = "cooldown"
                logging.info("Startup: previous successful scan is within 24 hours; keeping results")
                return False
            previous=str(self.metadata.get("as_of_date") or "")
            any_tracked=any(self.state.get(stage) for stage in ("1","2","3"))
            chart_cache_present=any((DATA / "price_cache").glob("*.json"))
            same_universe=self.metadata.get('last_scan_universe_mode','file')==self.universe_mode
            if self.metadata.get("last_success") and same_universe and previous >= target and (chart_cache_present or not any_tracked):
                self.metadata["startup_action"] = "cached"
                logging.info("Startup: prices current through %s (expected session %s); reusing cached scan",previous,target)
                return False
            self.metadata["startup_action"] = "scan"
        logging.info("Startup: last EOD %s, expected >= %s (or chart cache missing); checking scan",previous or "none",target)
        return self.launch_scan()

    def start_scheduler(self):
        if not self.auto:return
        def schedule():
            attempted_session=None
            while True:
                ny=datetime.now(ZoneInfo("America/New_York"))
                if ny.weekday()<5 and (ny.hour,ny.minute)>=(18,30):
                    session=ny.date().isoformat()
                    with self.lock:
                        current_asof=str(self.metadata.get("as_of_date") or "")
                    with self.lock:
                        pending_us=self.universe_mode=='us' and self.metadata.get('last_scan_universe_mode','file')!='us'
                    if session!=attempted_session and (current_asof < session or pending_us):
                        # launch_scan enforces the same successful-scan 24h
                        # limit for scheduled and manually requested updates.
                        if self.launch_scan():
                            attempted_session=session
                    elif current_asof>=session:
                        attempted_session=session
                time.sleep(60)
        self.scheduler_thread=threading.Thread(target=schedule,daemon=True,name="QullaSchedule")
        self.scheduler_thread.start()


class Handler(BaseHTTPRequestHandler):
    store: Store = None
    def send_json(self,status,data):
        raw=json.dumps(data,ensure_ascii=False,allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers();self.wfile.write(raw)

    def do_GET(self):
        route=urlsplit(self.path)
        if route.path in ("/","/dashboard.html") and not route.query:
            raw=(ROOT/"dashboard.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers();self.wfile.write(raw)
        elif route.path=="/api/state" and not route.query:
            self.send_json(200,self.store.snapshot())
        elif route.path=="/api/status" and not route.query:
            snapshot=self.store.snapshot()
            self.send_json(200,{"revision":snapshot["revision"],"metadata":snapshot["metadata"],
                                "running":self.store.running})
        elif route.path=="/api/chart":
            args=parse_qs(route.query)
            symbols=args.get("symbol",[])
            if len(symbols)!=1 or not SYMBOL_RE.fullmatch(symbols[0]):
                self.send_json(400,{"error":"Invalid chart symbol"});return
            symbol=symbols[0]
            with self.store.lock:
                tracked=any(r.get("symbol")==symbol for stage in ("1","2","3")
                            for r in self.store.state.get(stage,[]))
            if not tracked:
                self.send_json(404,{"error":"Symbol is not in a tracked stage"});return
            payload=read_price_cache(symbol,DATA / "price_cache")
            if payload is None:
                self.send_json(404,{"error":"No cached daily prices yet. Run a successful scan."});return
            self.send_json(200,payload)
        else:self.send_json(404,{"error":"Not found"})

    def _allowed_origin(self):
        origin=self.headers.get('Origin')
        host=self.headers.get('Host','')
        return not origin or origin in (f'http://{host}', f'https://{host}')

    def do_POST(self):
        if not self._allowed_origin():
            self.send_json(403,{"error":"Cross-origin requests are not permitted"});return
        if self.path=="/api/scan":
            started=self.store.launch_scan()
            metadata=self.store.snapshot()["metadata"]
            reason=None if started else metadata.get("scan_skip_reason", "running")
            # Cooldown is a normal no-op, not an error: preserve existing data.
            status=202 if started else (200 if reason=="cooldown" else 409)
            self.send_json(status,{"started":started,"reason":reason,"metadata":metadata})
        else:self.send_json(404,{"error":"Not found"})

    def do_PUT(self):
        if not self._allowed_origin():
            self.send_json(403,{"error":"Cross-origin requests are not permitted"});return
        if self.path!="/api/state":
            self.send_json(404,{"error":"Not found"});return
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size < 1 or size > MAX_BODY:
                self.send_json(413,{"error":"Invalid size / max 6 MB"});return
            parsed=json.loads(self.rfile.read(size))
            revision=parsed.get("revision")
            if not isinstance(revision,int):
                raise ValueError("revision must be an integer")
            ok,out=self.store.replace(parsed.get("state"),revision)
            self.send_json(200 if ok else 409,out)
        except (ValueError,TypeError,KeyError,UnicodeDecodeError) as ex:
            self.send_json(400,{"error":str(ex)})

    def log_message(self,fmt,*args):
        if not self.path.startswith('/api/status'):
            logging.info('%s - '+fmt,self.address_string(),*args)


def main():
    parser=argparse.ArgumentParser(description="Local Qullamaggie Three-Stage EOD scanner")
    parser.add_argument("--host",default="127.0.0.1",help="Default localhost only. Do not expose to public internet.")
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--provider",choices=("yahoo","csv"),default="yahoo")
    parser.add_argument("--csv-dir",default=str(DATA/"csv"))
    parser.add_argument("--universe",default=str(ROOT/"universe.csv"),help="Custom universe.csv when --universe-mode file")
    parser.add_argument("--universe-mode",choices=("us","file"),default=None,
                        help="us = Nasdaq Trader all US-listed equities (default Yahoo); file = user CSV universe")
    parser.add_argument("--top-pct",type=float,default=2.,help="Per-window top percentage (1 to 20)")
    parser.add_argument("--no-auto",action="store_true",help="Disable both startup freshness scan and weekday 18:30 New York scheduler")
    parser.add_argument("--no-browser",action="store_true")
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    if not (1 <= args.top_pct <= 20):parser.error("top-pct must be between 1 and 20")
    if args.host not in ('127.0.0.1','localhost','::1'):
        logging.warning("No authentication is provided; do NOT expose this server to public networks.")
    mode=args.universe_mode or ('us' if args.provider=='yahoo' else 'file')
    store=Store(args.universe,args.provider,args.top_pct/100,not args.no_auto,args.csv_dir,universe_mode=mode)
    Handler.store=store
    httpd=ThreadingHTTPServer((args.host,args.port),Handler)
    store.startup_scan()
    store.start_scheduler()
    url=f"http://{args.host}:{args.port}/"
    print(f"Dashboard: {url}")
    print(f"Version {SCANNER_VERSION} | Price provider: {args.provider} | universe mode: {mode}")
    print('US mode: full US-listed equity directory (Nasdaq Trader), excluding ETFs, units, rights, warrants, preferreds and debt')
    print('A full US Yahoo scan may take significant time or fail due to rate limits; incomplete results are never presented as full-market rankings.')
    print("Startup freshness check + weekday auto scan 18:30 New York:",not args.no_auto)
    print("Successful scan cooldown: 24 hours (applies to auto AND manual Run Scan)")
    print("Press Ctrl+C to stop. Daily data only: no automatic intraday TRIGGERED or orders.")
    if not args.no_browser:
        threading.Timer(1.0,lambda:webbrowser.open(url)).start()
    try:httpd.serve_forever(poll_interval=.4)
    except KeyboardInterrupt:print("\nStopping server")
    finally:httpd.shutdown();httpd.server_close()

if __name__=="__main__":main()