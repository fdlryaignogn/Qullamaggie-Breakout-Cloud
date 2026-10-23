"""US exchange-listed equity universe, sourced from Nasdaq Trader symbol files.

Coverage means listed shares on Nasdaq, NYSE, NYSE American, NYSE Arca,
Cboe/BATS and IEX as supplied by both directory files; not OTC or every
security purchasable in the United States. ETF, test issue, funds, debt,
rights, warrants, units and preferreds are excluded, while common/ordinary
shares, ADRs and REIT common shares are included where identifiable.
This is a rules-based classification, not an exchange-guaranteed taxonomy.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

NASDAQ_URL = 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'
OTHER_URL = 'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'
VALID_SYMBOL = re.compile(r'^[A-Z][A-Z0-9.\-]{0,13}$')
# Names identify instrument type; intentionally do not discard common stocks
# merely because a company's name contains e.g. Fund / Units / Trust.
NON_EQUITY_NAME = re.compile(
    r'\b(?:warrants?|rights?|preferred\s+(?:shares?|stocks?)|'
    r'preference\s+shares?|exchange.traded\s+funds?|'
    r'closed.end\s+funds?|etns?|exchange.traded\s+notes?|'
    r'senior\s+notes?|subordinated\s+notes?|'
    r'notes?\s+due\s+20\d\d|bonds?|debentures?)\b', re.I)
UNITS_ISSUE = re.compile(r'(?:\s[-–]\sunits?\b|\bunits?,\s*each\b|\bunit\s+consist)', re.I)
# Depositary Shares describing preferred interests are distinct from ADRs.
PREFERRED_DEPOSIT = re.compile(r'\bdepositary shares?\b.*\b(?:preferred|preference|fractional interest)\b', re.I)


def _reason(row: dict, symbol: str) -> str | None:
    if row.get('Test Issue','N').upper() != 'N': return 'test_issue'
    if row.get('ETF','N').upper() != 'N': return 'ETF'
    if row.get('NextShares','N').upper() == 'Y': return 'fund'
    if not VALID_SYMBOL.fullmatch(symbol): return 'unsupported_symbol'
    name = row.get('Security Name','').strip()
    if not name: return 'missing_name'
    if NON_EQUITY_NAME.search(name) or PREFERRED_DEPOSIT.search(name): return 'non_common_instrument'
    if UNITS_ISSUE.search(name): return 'units'
    # Structured preferred / warrant exchange suffixes on non-Nasdaq listings.
    if '$' in symbol or symbol.endswith(('.U','.W','.WS','.R')): return 'security_suffix'
    return None


def parse_directory(nasdaq_text: str, other_text: str):
    """Parse raw pipe-delimited symbol directories, returning symbols and audit.

    Reject unexpected formats rather than silently ranking a short list.
    """
    symbols, skipped = {}, Counter()
    sources = [('nasdaq',nasdaq_text,'Symbol'),('other',other_text,'ACT Symbol')]
    raw_counts = {}
    for source, text, symbol_field in sources:
        reader = csv.DictReader(io.StringIO(text), delimiter='|')
        fields = set(reader.fieldnames or [])
        required = {symbol_field, 'Security Name', 'ETF', 'Test Issue'}
        if not required.issubset(fields):
            raise ValueError(f'Invalid {source} directory columns; expected {sorted(required)}')
        count = 0
        for row in reader:
            value = str(row.get(symbol_field) or '').strip().upper()
            if not value or value.startswith('FILE CREATION TIME'): continue
            count += 1
            reason = _reason(row, value)
            if reason: skipped[reason] += 1; continue
            if value in symbols: skipped['duplicate'] += 1; continue
            symbols[value] = {'name':row['Security Name'].strip(), 'exchange':source}
        raw_counts[source] = count
    # A stale or intercepted malformed single-page response should not be
    # mistaken for a complete US universe. Unit tests may use smaller fixtures.
    if not symbols:
        raise ValueError('No valid listed equities in symbol directories')
    return sorted(symbols), {'directory_rows':raw_counts,
                             'excluded_breakdown':dict(skipped),
                             'filtered_equities':len(symbols),
                             'universe_scope':'US-listed equities (Nasdaq Trader directories; excludes ETFs, warrants, rights, units, preferred and debt; no OTC)',
                             'listing_urls':[NASDAQ_URL,OTHER_URL]}


def _read_url(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 Qullamaggie-Research/2.5',
                                                'Accept':'text/plain'})
    with urllib.request.urlopen(req,timeout=25) as result:
        payload=result.read(3_000_000)
    text=payload.decode('utf-8-sig',errors='replace')
    if 'Security Name' not in text[:400]:
        raise ValueError(f'Unexpected directory response from {url}')
    return text


def get_us_equities(cache_dir: Path, now: datetime | None = None, fetch=None):
    """Refresh listing cache daily. Use last cached directory on network failure
    only when no older than seven days; report cache/source age.
    """
    now=now or datetime.now(timezone.utc)
    cache_dir=Path(cache_dir)
    paths=[cache_dir/'nasdaqlisted.txt',cache_dir/'otherlisted.txt']
    fetch=fetch or _read_url
    def cached(older_than=None):
        if not all(p.is_file() for p in paths): return None
        age=max(now-datetime.fromtimestamp(p.stat().st_mtime,timezone.utc) for p in paths)
        if older_than is not None and age>older_than: return None
        raw=[p.read_text(encoding='utf-8') for p in paths]
        symbols,stats=parse_directory(*raw)
        # Enforce minimum expected market breadth on production imports:
        # a tiny corrupted cache could never represent every listed stock.
        if len(symbols)<1000: raise ValueError(f'Listing directory only contains {len(symbols)} stocks; refusing incomplete universe')
        stats.update({'listing_cached':True,'listing_age_hours':round(age.total_seconds()/3600,1)})
        return symbols,stats
    recent=cached(timedelta(hours=24))
    if recent: return recent
    try:
        texts=[fetch(url) for url in (NASDAQ_URL,OTHER_URL)]
        symbols,stats=parse_directory(*texts)
        if len(symbols)<1000: raise ValueError(f'Live listing directory only contains {len(symbols)} stocks; refusing incomplete universe')
        cache_dir.mkdir(parents=True,exist_ok=True)
        for path,body in zip(paths,texts):
            tmp=path.with_suffix('.tmp')
            tmp.write_text(body,encoding='utf-8')
            os.replace(tmp,path)
        stats.update({'listing_cached':False,'listing_age_hours':0})
        return symbols,stats
    except Exception as ex:
        last=cached(timedelta(days=7))
        if last:
            syms,stats=last
            stats['listing_warning']=f'Listings refresh failed; using cached <=7-day directory: {ex}'
            return syms,stats
        raise RuntimeError(f'Cannot retrieve complete US listings from Nasdaq Trader, and no recent complete cache is available: {ex}') from ex