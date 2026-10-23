import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chart_cache import save_price_caches,read_price_cache
from server import expected_last_session,scan_cooldown_until,Store


class V2ScannerTests(unittest.TestCase):
    def test_expected_session_handles_new_york_cutoff_weekends_and_dst(self):
        zone=ZoneInfo('America/New_York')
        for instant,expected in [
            ('2026-10-21T18:31:00','2026-10-21'),
            ('2026-10-21T16:01:00','2026-10-20'),
            ('2026-10-19T10:01:00','2026-10-16'),
            ('2026-10-25T20:30:00','2026-10-23'),
            ('2026-11-02T19:00:00','2026-11-02'),
        ]:
            self.assertEqual(expected_last_session(datetime.fromisoformat(instant).replace(tzinfo=zone)),expected)

    def test_cache_round_trip_only_eod_upto_scan(self):
        dates=pd.bdate_range('2026-01-01',periods=140)
        df=pd.DataFrame({'open':[10]*len(dates),'high':[12]*len(dates),
             'low':[9]*len(dates),'close':[11]*len(dates),'volume':[1000]*len(dates)},index=dates)
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            as_of=dates[-3].strftime('%Y-%m-%d')
            save_price_caches({'TEST':df},as_of,folder,'csv')
            data=read_price_cache('TEST',folder)
            self.assertEqual(data['source'],'csv')
            self.assertEqual(data['as_of'],as_of)
            self.assertEqual(data['bars'][-1]['date'],as_of)
            self.assertEqual(len(data['bars']),138)
            self.assertFalse(data['adjusted'])
            self.assertIsNone(read_price_cache('OTHER',folder))

    def test_chart_cache_retains_six_month_window_plus_margin(self):
        dates=pd.bdate_range('2025-01-01',periods=230)
        frame=pd.DataFrame({'open':[10]*len(dates),'high':[12]*len(dates),
             'low':[9]*len(dates),'close':[11]*len(dates),'volume':[1000]*len(dates)},index=dates)
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            save_price_caches({'TEST':frame},dates[-1].strftime('%Y-%m-%d'),folder,'csv')
            rows=read_price_cache('TEST',folder)['bars']
            self.assertEqual(len(rows),180)
            self.assertEqual(rows[-126]['date'],dates[-126].strftime('%Y-%m-%d'))

    def test_scan_cooldown_from_success_uses_exact_24h_and_timezone(self):
        now=datetime(2026,10,21,12,0,tzinfo=timezone.utc)
        # Equivalent source timestamps with different UTC offsets.
        fresh='2026-10-21T19:59:59+08:00'
        self.assertEqual(scan_cooldown_until(fresh,now),
                         datetime(2026,10,22,11,59,59,tzinfo=timezone.utc))
        self.assertIsNone(scan_cooldown_until('2026-10-20T12:00:00Z',now))
        self.assertIsNone(scan_cooldown_until('2026-10-20T11:59:59+00:00',now))
        self.assertIsNone(scan_cooldown_until('2026-10-21T12:00:00',now))  # naive: reject
        self.assertIsNone(scan_cooldown_until('nonsense',now))
        self.assertIsNone(scan_cooldown_until(None,now))
        self.assertIsNone(scan_cooldown_until('2026-11-21T12:00:00Z',now))  # corrupted future timestamp

    def test_startup_24h_skip_even_if_asof_old_and_missing_chart_cache(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            (root/'universe.csv').write_text('symbol\nTEST\n')
            store=Store(root/'universe.csv',provider='csv',auto=True)
            now=datetime.now(timezone.utc)
            # An outdated market bar still must not trigger a new download < 24h.
            store.metadata.update({'as_of_date':'2025-01-01',
                                   'last_success':(now-timedelta(hours=23)).isoformat()})
            with patch.object(store,'launch_scan') as run:
                self.assertFalse(store.startup_scan())
                run.assert_not_called()
            self.assertEqual(store.metadata['startup_action'],'cooldown')
            self.assertIsNotNone(store.snapshot()['metadata']['cooldown_until'])

    def test_startup_uses_cached_success_or_starts_scan_after_24h(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            (root/'universe.csv').write_text('symbol\nTEST\n')
            store=Store(root/'universe.csv',provider='csv',auto=True)
            now=datetime.now(timezone.utc)
            today=expected_last_session(datetime.now(ZoneInfo('America/New_York')))
            store.metadata.update({'as_of_date':today,'last_success':(now-timedelta(hours=25)).isoformat()})
            with patch.object(store,'launch_scan') as run:
                self.assertFalse(store.startup_scan())
                run.assert_not_called()
                self.assertEqual(store.metadata['startup_action'],'cached')
            store.metadata.update({'as_of_date':'2025-01-01','last_success':(now-timedelta(hours=25)).isoformat()})
            with patch.object(store,'launch_scan',return_value=True) as run:
                self.assertTrue(store.startup_scan())
                run.assert_called_once()
                self.assertEqual(store.metadata['startup_action'],'scan')
            store.auto=False
            with patch.object(store,'launch_scan') as run:
                self.assertFalse(store.startup_scan())
                run.assert_not_called()

    def test_manual_launch_respects_cooldown_and_failure_does_not_start_clock(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            (root/'universe.csv').write_text('symbol\nTEST\n')
            store=Store(root/'universe.csv',provider='csv',auto=True)
            store.metadata['last_success']=(datetime.now(timezone.utc)-timedelta(hours=12)).isoformat()
            with patch('server.threading.Thread') as thread:
                self.assertFalse(store.launch_scan())
                thread.assert_not_called()
            self.assertEqual(store.snapshot()['metadata']['scan_skip_reason'],'cooldown')
            self.assertFalse(store.running)
            # A failed scan timestamp, or manual changes to state.updatedAt,
            # does not extend the cooldown. Old success is the only clock.
            store.metadata['last_success']=(datetime.now(timezone.utc)-timedelta(hours=24,minutes=1)).isoformat()
            store.metadata['last_attempt']=datetime.now(timezone.utc).isoformat()
            store.state['updatedAt']=datetime.now(timezone.utc).isoformat()
            with patch('server.threading.Thread') as thread:
                self.assertTrue(store.launch_scan())
                thread.return_value.start.assert_called_once()
            self.assertTrue(store.running)
            self.assertEqual(store.snapshot()['metadata']['scan_skip_reason'],None)

if __name__=='__main__':unittest.main()