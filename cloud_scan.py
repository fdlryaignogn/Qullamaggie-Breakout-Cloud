"""Scheduled Github Actions job, using the V2.7 all-US EOD scanner.

Only publishes a market-wide scan when the scan itself succeeded and coverage
and date checks pass. Old GitHub Pages data is intentionally never overwritten
with failed, stale, partial, or fabricated results.
"""
from __future__ import annotations
import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
from server import Store, DATA, ROOT, METADATA_PATH

SITE=ROOT/'site'
LATEST=SITE/'data'/'latest.json'


def last_complete_session() -> str:
    ny=datetime.now(ZoneInfo('America/New_York'))
    if ny.hour < 18 and ny.date().weekday() < 5:
        limit=(ny-timedelta(days=1)).date()
    else:
        limit=ny.date()
    sessions=xcals.get_calendar('XNYS').sessions_in_range((limit-timedelta(days=15)).isoformat(),limit.isoformat())
    if len(sessions)==0: raise RuntimeError('NYSE calendar returned no completed session')
    return sessions[-1].date().isoformat()


def atomic_json(path:Path,obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
    os.replace(temp,path)


def publish(snapshot):
    meta=snapshot['metadata']; state=snapshot['state']
    if meta.get('phase') not in ('success','idle') or not meta.get('last_success'):
        raise RuntimeError('Scan not successful; refusing to publish')
    if meta.get('last_scan_universe_mode')!='us':
        raise RuntimeError('Not a full-US-market scan; refusing to publish')
    if float(meta.get('coverage') or 0)<.90:
        raise RuntimeError('Full-universe quote coverage below 90%; refusing to publish')
    if int(meta.get('universe_size') or 0)<1000:
        raise RuntimeError('Suspiciously small US listing pool; refusing to publish')
    if meta.get('as_of_date')!=last_complete_session():
        raise RuntimeError('Market data stale for expected completed NYSE session; refusing to publish')
    # Always show only publicly shareable, non-account state. Do not publish
    # a user's private account, risk balances, API keys, or unapproved notes.
    bad_fields={'api_key','secret','password','account_number','account_balance','equity','risk_fraction'}
    public_state={**state}
    for stage in ('1','2','3'):
        public_state[stage]=[{k:v for k,v in row.items() if k not in bad_fields}
                             for row in state.get(stage,[])]
    payload={'revision':int(datetime.now(timezone.utc).timestamp()),'running':False,
             'metadata':{**meta,'phase':'success','scanner_version':'3.0-cloud'},
             'state':public_state}
    # Avoid stale charts when a formerly followed symbol has disappeared.
    dest=SITE/'data'/'charts';dest.mkdir(parents=True,exist_ok=True)
    keep={r.get('symbol') for stage in ('1','2','3') for r in state.get(stage,[])
          if r.get('symbol') and (stage!='1' or r.get('status')!='ARCHIVED')}
    # Never retain yesterday's chart for the same symbol after a successful refresh.
    for old in dest.glob('*.json'): old.unlink()
    src=DATA/'price_cache'
    copied=0
    for symbol in sorted(keep):
        source=src/f'{symbol}.json'
        if source.exists():
            try:
                chart=json.loads(source.read_text(encoding='utf-8'))
                if chart.get('symbol')==symbol and chart.get('as_of')==meta['as_of_date']:
                    shutil.copy2(source,dest/f'{symbol}.json');copied+=1
            except (ValueError,OSError):
                logging.warning('Ignored invalid chart %s',source)
    payload['metadata']['public_chart_count']=copied
    atomic_json(LATEST,payload)
    logging.info('Published %s stage-1 rows / %s charts',len(state['1']),copied)


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    expected=last_complete_session()
    prev=json.loads(LATEST.read_text(encoding='utf-8')) if LATEST.exists() else {}
    prior=prev.get('metadata') or {}
    if prior.get('as_of_date')==expected and prior.get('last_scan_universe_mode')=='us' and prior.get('phase')=='success':
        logging.info('Market session %s already published; nothing to do',expected)
        return
    # GitHub-hosted pages are public. Only migrate tracking state with explicit consent.
    store=Store(ROOT/'universe.csv','yahoo',.02,False,DATA/'csv',universe_mode='us')
    logging.info('Cloud scan starting; target market session %s',expected)
    store._scan_worker()  # synchronous; writes state + metadata on successful scan
    if store.metadata.get('phase')!='success':
        raise RuntimeError('Cloud scan failed; keeping previous published JSON. '+str(store.metadata.get('last_error')))
    publish(store.snapshot())

if __name__=='__main__': main()