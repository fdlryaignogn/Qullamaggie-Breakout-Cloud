import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from us_universe import parse_directory,get_us_equities
from scanner import compute_momentum
from server import Store

NASDAQ = '''Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N
ABCD|Example LLC - Units|Q|N|N|100|N|N
ALPHW|Alpha Inc. - Warrant|Q|N|N|100|N|N
TETF|Test ETF|Q|N|N|100|Y|N
TSTT|Testing Issue|Q|Y|N|100|N|N
ADRX|Abivax - American Depositary Shares|G|N|N|100|N|N
File Creation Time: 1021202622:01|||||||
'''
OTHER = '''ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
A|Agilent Technologies, Inc. Common Stock|N|A|N|100|N|A
BRK.B|Berkshire Hathaway Inc. Class B Common Stock|N|BRK.B|N|100|N|BRK/B
ABC.U|Example Acquisition Corp Units, each consisting of warrant|N|ABC.U|N|100|N|ABC=
ABR$D|Arbor Realty Trust Preferred Shares|N|ABRpD|N|100|N|ABR-D
'''

class UniverseTests(unittest.TestCase):
    def test_combines_major_us_exchanges_excludes_non_common(self):
        symbols,meta=parse_directory(NASDAQ,OTHER)
        self.assertEqual(symbols,['A','AAPL','ADRX','BRK.B'])
        self.assertEqual(meta['directory_rows']['nasdaq'],6)
        self.assertEqual(meta['directory_rows']['other'],4)
        self.assertEqual(meta['excluded_breakdown']['ETF'],1)
        self.assertEqual(meta['filtered_equities'],4)
    def test_bad_directory_headers_rejected(self):
        with self.assertRaises(ValueError): parse_directory('symbol,name\nA,Hello',OTHER)
    def test_directory_cache_network_fetch_one_day_and_fallback(self):
        n='Symbol|Security Name|ETF|Test Issue\n'+''.join(f'Q{i:04}|Company {i} Common Stock|N|N\n' for i in range(1100))
        o=OTHER
        with tempfile.TemporaryDirectory() as td:
            now=datetime.now(timezone.utc)
            with patch('us_universe._read_url', side_effect=[n,o]) as read:
                syms,info=get_us_equities(Path(td),now=now)
                self.assertEqual(len(syms),1102)
                self.assertFalse(info['listing_cached'])
                self.assertEqual(read.call_count,2)
            with patch('us_universe._read_url') as read:
                again,meta=get_us_equities(Path(td),now=now)
                read.assert_not_called()
                self.assertEqual(again,syms)
                self.assertTrue(meta['listing_cached'])
    def test_all_horizons_rank_on_their_own_history(self):
        dates=pd.bdate_range('2026-01-01',periods=200)
        def mk(prices):
            return pd.DataFrame({'open':prices,'high':[x*1.02 for x in prices],
               'low':[x*.98 for x in prices],'close':prices,'volume':[1000]*len(prices)},
               index=dates[-len(prices):])
        frames={'LONG':mk(np.linspace(20,25,200)),'IPO':mk(np.linspace(10,40,32)),
                'MED':mk(np.linspace(12,20,99))}
        rows,meta=compute_momentum(frames,top_fraction=.2)
        self.assertEqual(meta['eligible_by_window'],{'1m':3,'3m':2,'6m':1})
        recent=next(r for r in rows if r['symbol']=='IPO')
        self.assertIn('1M',recent['selected_windows'])
        self.assertNotIn('return_6m',recent)
        self.assertIn('data_warnings',recent)
    def test_us_universe_change_rescans_when_cooldown_expires(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'universe.csv';path.write_text('symbol\nAAPL\n')
            store=Store(path,provider='csv',auto=True,universe_mode='us')
            store.metadata.update({'as_of_date':'2099-01-01','last_success':'2025-01-01T00:00:00+00:00',
                                   'last_scan_universe_mode':'file'})
            with patch.object(store,'launch_scan',return_value=True) as call:
                self.assertTrue(store.startup_scan())
                call.assert_called_once()

if __name__=='__main__': unittest.main()

class ScanIntegrationTests(unittest.TestCase):
    def frames(self):
        dates=pd.bdate_range('2025-01-01',periods=180)
        out={}
        for i,sym in enumerate(['AAPL','AMD','BRK.B','MSFT','PLTR']):
            prices=np.linspace(50,60+i*10,180)
            out[sym]=pd.DataFrame({'open':prices,'high':prices*1.01,
                 'low':prices*.99,'close':prices,'volume':[10000]*180},index=dates)
        return out

    def test_full_us_mode_success_and_coverage_metadata(self):
        import server
        frames=self.frames()
        with tempfile.TemporaryDirectory() as td, patch.object(server,'DATA',Path(td)),\
            patch.object(server,'STATE_PATH',Path(td)/'tracking_state.json'),\
            patch.object(server,'METADATA_PATH',Path(td)/'scan_metadata.json'),\
            patch('server.get_us_equities',return_value=(sorted(frames),{'universe_scope':'US-listed equities'})),\
            patch('server.fetch_yahoo',return_value=(frames,{})):
            st=Store(Path(td)/'missing_custom.csv',provider='yahoo',universe_mode='us')
            st._scan_worker()
            m=st.snapshot()['metadata']
            self.assertEqual(m['phase'],'success')
            self.assertEqual(m['market_coverage_pct'],100)
            self.assertEqual(m['last_scan_universe_mode'],'us')
            self.assertEqual(m['eligible_by_window'],{'1m':5,'3m':5,'6m':5})
            self.assertTrue(st.state['1'])
            self.assertTrue((Path(td)/'tracking_state.json').exists())
            self.assertEqual(len(list((Path(td)/'price_cache').glob('*.json'))),len(st.state['1']))
    def test_incomplete_quotes_preserve_previous_state(self):
        import server
        frames=self.frames()
        with tempfile.TemporaryDirectory() as td, patch.object(server,'DATA',Path(td)),\
            patch.object(server,'STATE_PATH',Path(td)/'tracking_state.json'),\
            patch.object(server,'METADATA_PATH',Path(td)/'scan_metadata.json'),\
            patch('server.get_us_equities',return_value=(sorted(frames),{})),\
            patch('server.fetch_yahoo',return_value=({'AAPL':frames['AAPL']},
                                                     {'MSFT':'rate limited'})):
            st=Store(Path(td)/'missing_custom.csv',provider='yahoo',universe_mode='us')
            st.state['2']=[{'symbol':'AAPL','setup_id':'keep-me','setup_status':'READY'}]
            st._scan_worker()
            self.assertEqual(st.snapshot()['metadata']['phase'],'error')
            self.assertIsNone(st.snapshot()['metadata']['last_success'])
            self.assertEqual(st.state['2'][0]['setup_status'],'READY')
            self.assertEqual(st.state['1'],[])