"""Prior advance must precede the base; 30% is a user-editable reference, not a READY decision."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scanner import prior_advance_before_base, setup_evidence, merge_scan


def sample():
    dates=pd.bdate_range('2025-01-01', periods=240)
    closes=np.ones(240)*50.0
    closes[:160]=np.linspace(50,80,160)
    closes[160:224]=np.linspace(80,145,64)
    closes[224:]=np.linspace(145,145.1,16)
    return pd.DataFrame({
        'open':closes, 'high':closes*1.008,'low':closes*.992,
        'close':closes,'volume':np.ones(240)*100_000}, index=dates)


class PriorAdvanceTests(unittest.TestCase):
    def test_before_base_and_not_trailing_today(self):
        df=sample()
        base_start=df.index[224].strftime('%Y-%m-%d')
        r=prior_advance_before_base(df,base_start)
        self.assertEqual(r['prior_advance_start'],df.index[160].strftime('%Y-%m-%d'))
        self.assertEqual(r['prior_advance_end'],df.index[223].strftime('%Y-%m-%d'))
        self.assertEqual(r['prior_advance_days'],63)
        self.assertAlmostEqual(r['prior_advance_pct'],round((145/80-1)*100,2))
        df.loc[df.index[-1],'close']=2500  # big breakout today must NOT alter pre-base gain
        self.assertEqual(prior_advance_before_base(df,base_start),r)

    def test_insufficient_before_base_returns_none(self):
        df=sample()
        self.assertIsNone(prior_advance_before_base(df,df.index[30].strftime('%Y-%m-%d')))
        self.assertIsNone(prior_advance_before_base(df,'not-date'))

    def test_setup_evidence_uses_window_just_before_base(self):
        df=sample()
        evidence=setup_evidence(df)
        self.assertIsNotNone(evidence)
        base_start=pd.Timestamp(evidence['base_start'])
        self.assertLess(pd.Timestamp(evidence['prior_advance_end']),base_start)
        self.assertEqual(prior_advance_before_base(df,base_start)['prior_advance_pct'], evidence['prior_advance_pct'])
        self.assertEqual(evidence['prior_advance_min_pct'],30)

    def test_ready_kept_and_missing_measurement_backfilled(self):
        df=sample(); date=df.index[-1].strftime('%Y-%m-%d')
        start=df.index[224].strftime('%Y-%m-%d')
        s={'1':[],'2':[{'symbol':'ABC','setup_id':'ABC-1','setup_status':'READY',
          'base_start':start,'base_high':180,'prior_advance_min_pct':50}],
          '3':[],'history':[]}
        result=merge_scan(s,{'ABC':df}, [], {'as_of_date':date})
        row=result['2'][0]
        self.assertEqual(row['setup_status'],'READY')
        self.assertEqual(row['prior_advance_min_pct'],50)
        self.assertEqual(row['prior_advance_pct'],prior_advance_before_base(df,start)['prior_advance_pct'])

    def test_manual_advance_and_minimum_not_overwritten(self):
        df=sample();date=df.index[-1].strftime('%Y-%m-%d')
        s={'1':[],'2':[{'symbol':'ABC','setup_id':'ABC-2','setup_status':'READY',
          'base_start':date,'base_high':180,'prior_advance_pct':25,'prior_advance_min_pct':42}],
          '3':[],'history':[]}
        result=merge_scan(s,{'ABC':df},[],{'as_of_date':date})
        row=result['2'][0]
        self.assertEqual(row['prior_advance_pct'],25)
        self.assertEqual(row['prior_advance_min_pct'],42)
        self.assertEqual(row['setup_status'],'READY')

if __name__=='__main__':unittest.main()