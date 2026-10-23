import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scanner import clean_frame,compute_momentum,setup_evidence,merge_scan,fetch_csv,symbols_from_csv
from server import Store


def synthetic(sym, n=250, spike=False):
    dates=pd.bdate_range('2025-09-01', periods=n)
    if spike:
        # Prior advance before a 20-day base and then a tightening base
        prices=[50.0]*n
        for i in range(n):
            if i<150: prices[i]=50 + .04*i
            elif i<228: prices[i]=56+(.8*(i-150))
            else: prices[i]=117.6 + .22*np.sin((i-228)*.5)
    else:
        prices=np.linspace(50,85,n).tolist()
    return pd.DataFrame({
        'open':prices,
        'high':[x*1.008 for x in prices],
        'low':[x*.992 for x in prices],
        'close':prices,
        'volume':[500_000]*n
    },index=dates)


class ScannerTests(unittest.TestCase):
    def test_1_3_6_union_no_intersection(self):
        frames={x:synthetic(x) for x in 'ABCDE'}
        x=frames['A'].copy()
        x.loc[x.index[-19]:,'close']*=1.6
        x.loc[x.index[-19]:,'open']*=1.6;x.loc[x.index[-19]:,'high']*=1.6;x.loc[x.index[-19]:,'low']*=1.6
        frames['A']=x
        rows,meta=compute_momentum(frames,.2)
        self.assertEqual(meta['eligible'],5)
        self.assertEqual(meta['per_window_top_count'],1)
        self.assertTrue(all(row['selected_windows'] for row in rows))
        self.assertIn('A',[r['symbol'] for r in rows])
        self.assertGreaterEqual(len(rows),1)

    def test_missing_history_exclusion(self):
        frames={'A':synthetic('A'),'B':synthetic('B').iloc[-80:]}
        rows,meta=compute_momentum(frames)
        self.assertEqual(meta['eligible'],1)
        self.assertEqual(meta['excluded_incomplete_or_stale'],1)
        self.assertEqual([r['symbol'] for r in rows],['A'])

    def test_csv_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp);(t/'universe.csv').write_text('symbol\nABC\nABC\nXYZ\n')
            self.assertEqual(symbols_from_csv(t/'universe.csv'),['ABC','XYZ'])
            frame=synthetic('ABC')
            frame.to_csv(t/'ABC.csv',index_label='Date')
            frames,errs=fetch_csv(['ABC','XYZ'],t)
            self.assertIn('ABC',frames)
            self.assertIn('XYZ',errs)
            self.assertEqual(len(frames['ABC']),250)
            self.assertEqual(len(clean_frame(frame)),250)

    def test_advance_heuristic_proposes_forming(self):
        frame=synthetic('A',spike=True)
        evidence=setup_evidence(frame)
        self.assertIsNotNone(evidence)
        self.assertGreater(evidence['prior_advance_pct'],30)
        self.assertIn(evidence['volatility_contraction'],['YES','NO'])

    def test_readiness_persists_when_momentum_drops(self):
        frames={'A':synthetic('A',spike=True), 'B':synthetic('B')}
        rows,meta=compute_momentum(frames,.2)
        baseline={'1':[{'symbol':'A','market':'US','status':'ACTIVE'}],
          '2':[{'symbol':'A','setup_id':'A-20250000','setup_status':'READY',
                 'base_high':110,'base_low':100,'_updated_at':'2025-10-01T00:00:00Z'}],
          '3':[], 'history':[]}
        updated=merge_scan(baseline,frames, [r for r in rows if r['symbol']=='B'],meta)
        self.assertEqual(updated['2'][0]['setup_status'],'READY')
        self.assertEqual(updated['3'][0]['status'],'WATCH')
        self.assertNotIn('trigger_time',updated['3'][0])
        self.assertEqual(updated['1'][0]['status'],'ARCHIVED')

    def test_existing_trigger_preserved(self):
        frames={'A':synthetic('A',spike=True)}
        rows,meta=compute_momentum(frames)
        baseline={'1':[],'2':[{'symbol':'A','setup_id':'AAA','setup_status':'READY','base_high':110}],
                  '3':[{'symbol':'A','setup_id':'AAA','status':'TRIGGERED','trigger_price':111}], 'history':[]}
        new=merge_scan(baseline,frames,rows,meta)
        self.assertEqual(new['3'][0]['trigger_price'],111)
        self.assertEqual(new['3'][0]['status'],'TRIGGERED')

if __name__=='__main__':unittest.main()