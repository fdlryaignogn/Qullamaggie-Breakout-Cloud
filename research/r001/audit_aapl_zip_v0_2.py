"""R-001 AAPL audit: validate a user-supplied FMP Colab ZIP, no API key or network.

Usage: python audit_aapl_zip_v0_2.py r001_aapl_audit.zip [summary.json]
Only verifies the provided 2005-2009 slice and frozen v0.1 formula.
"""
import csv
import hashlib
import io
import json
import sys
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

OHLCV_FILE = 'aapl_fmp_2005_2009_ohlcv.csv'
CANDIDATES_FILE = 'aapl_breakout_candidates_UNVERIFIED.csv'
EXPECTED_FIELDS = ['date', 'open', 'high', 'low', 'close', 'volume']
Q = Decimal


def fail_if(condition, message):
    if condition:
        raise ValueError(message)


def parse_csv(blob):
    return list(csv.DictReader(io.StringIO(blob.decode('utf-8-sig'))))


def analyze(zip_path):
    with zipfile.ZipFile(zip_path) as package:
        names = set(package.namelist())
        required = {OHLCV_FILE, CANDIDATES_FILE, 'manifest.json'}
        fail_if(not required.issubset(names), 'Required ZIP members missing')
        fail_if(any(package.getinfo(p).file_size > 2_000_000 for p in required), 'Oversized input')
        data_blob = package.read(OHLCV_FILE)
        candidates_blob = package.read(CANDIDATES_FILE)
        manifest = json.loads(package.read('manifest.json'))
    digest = hashlib.sha256(data_blob).hexdigest()
    fail_if(digest != manifest['sha256_csv'], 'SHA256 mismatch')
    fail_if(manifest['case_id'] != 'R001-AAPL-01', 'Unexpected case')
    fail_if(manifest['request_from'] != '2005-01-01' or manifest['request_to'] != '2009-12-31', 'Unexpected source window')
    fail_if(manifest['source'] != 'FMP stable historical-price-eod/full', 'Unexpected source')
    rows = parse_csv(data_blob)
    fail_if(len(rows) != manifest['row_count'], 'Row-count mismatch')
    fail_if(not rows or set(rows[0]) != set(EXPECTED_FIELDS), 'Invalid OHLCV columns')
    days = []
    for row in rows:
        d = date.fromisoformat(row['date'])
        o, h, l, c = [Q(row[x]) for x in ('open', 'high', 'low', 'close')]
        vol = Q(row['volume'])
        fail_if(min(o,h,l,c)<=0 or vol<0, 'Invalid nonpositive prices/volume')
        fail_if(h<max(o,c,l) or l>min(o,c,h), 'Invalid OHLC relationship')
        fail_if(bool(days) and d <= days[-1]['date'], 'Dates not strictly increasing')
        fail_if(d.weekday()>=5, 'Weekend bar')
        days.append({'date':d, 'open':o,'high':h,'low':l,'close':c,'volume':vol})
    fail_if(days[0]['date'].isoformat()!=manifest['first_session'] or days[-1]['date'].isoformat()!=manifest['last_session'], 'Manifest date mismatch')
    calculated = []
    for idx in range(252,len(days)):
        bar=days[idx]
        prev60=max(x['high'] for x in days[idx-60:idx])
        prev20=sum((x['close']*x['volume'] for x in days[idx-20:idx]),Q('0'))/Q('20')
        if bar['close'] > prev60 and bar['close'] > bar['open'] and prev20 >= 1_000_000:
            future=days[idx+1:idx+253]
            doubled=(max(x['close'] for x in future)>=2*bar['close']) if len(future)==252 else None
            calculated.append((idx,prev60,prev20,doubled))
    exported = parse_csv(candidates_blob)
    fail_if(len(exported)!=manifest['candidate_count'] or len(exported)!=len(calculated), 'Candidate-count mismatch')
    fail_if(not calculated, 'No breakout candidates')
    counts={'true':0,'false':0,'censored':0}
    for (idx, p60, dollar, doubled),row in zip(calculated,exported):
        raw=days[idx]
        fail_if(row['date']!=raw['date'].isoformat(), 'Candidate date mismatch')
        for f in ('open','high','low','close','volume'):
            fail_if(Q(row[f])!=raw[f], f'Candidate OHLCV mismatch: {f}')
        fail_if(Q(row['prior_60_high'])!=p60, 'Prior high mismatch')
        fail_if(abs(Q(row['prior_20_nominal_dollar_volume_proxy'])-dollar)>Q('1'), 'Prior dollar volume mismatch')
        fail_if(row['candidate_only_not_verified'].lower()!='true', 'Candidate missing provisional flag')
        expected='' if doubled is None else str(doubled)
        fail_if(row['future_252_session_doubling_label_RESEARCH_ONLY']!=expected, 'Forward label mismatch')
        counts['censored' if doubled is None else 'true' if doubled else 'false']+=1
    first_idx,prior_high,dollar,label=calculated[0]
    event=days[first_idx]
    forward=days[first_idx+1:first_idx+253]
    def percent(x): return round(float((x/event['close']-1)*100),4)
    ret={str(h):{'date':days[first_idx+h]['date'].isoformat(), 'close':str(days[first_idx+h]['close']), 'return_pct':percent(days[first_idx+h]['close'])} for h in (63,126,252)}
    highday=max(forward,key=lambda x:x['close'])
    lowday=min(forward,key=lambda x:x['close'])
    summary={
       'case_id':'R001-AAPL-01',
       'status':'PROVISIONAL_FIRST_IN_WINDOW_NOT_TRANCHE_VALIDATED',
       'source_sha256':digest,
       'downloaded_at_utc':manifest['downloaded_at_utc'],
       'row_count':len(days),
       'sample_start':days[0]['date'].isoformat(),
       'sample_end':days[-1]['date'].isoformat(),
       'candidate_count':len(calculated),
       'candidate_label_counts':counts,
       'first_event':{
          'date':event['date'].isoformat(), 'sample_row_zero_indexed':first_idx,
          'open':str(event['open']), 'high':str(event['high']), 'low':str(event['low']), 'close':str(event['close']),
          'volume':int(event['volume']),'prior_60_session_high':str(prior_high),
          'prior_20_dollar_volume_proxy':float(dollar),
          'future_252_label':label, 'forward_63_126_252':ret,
          'forward_max_close':str(highday['close']), 'forward_max_close_date':highday['date'].isoformat(), 'forward_max_gain_pct':percent(highday['close']),
          'forward_min_close':str(lowday['close']), 'forward_min_close_date':lowday['date'].isoformat(), 'forward_min_loss_vs_event_close_pct':percent(lowday['close']),
          'forward_252_observations':len(forward),
       },
       'notes':['OHLCV slice begins 2005; first event is left-truncated, not earliest ever AAPL breakout',
                'OHLC prices rounded to cents; one-cent breakout margin may affect classification',
                'FMP full-close split adjusted per vendor documentation, vendor corporate-action factor and full volume matching still pending',
                'No market benchmark or contemporaneous delisted control universe',
                'Outputs are not a trading backtest or production rule'],
       'validation':{'sha256':'PASS','input_ohlcv_integrity':'PASS','candidate_dates_and_labels_recalculated':'PASS','historical_split_volume_source_provenance':'PARTIAL','universe_and_controls':'MISSING'}
    }
    return summary

if __name__=='__main__':
    if len(sys.argv) not in (2,3):
        raise SystemExit('Usage: python audit_aapl_zip_v0_2.py input.zip [summary.json]')
    r=analyze(sys.argv[1]);result=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if len(sys.argv)==3:
        Path(sys.argv[2]).write_text(result,encoding='utf-8')
    print(result)
