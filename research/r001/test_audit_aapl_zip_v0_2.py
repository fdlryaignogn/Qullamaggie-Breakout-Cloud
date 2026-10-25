"""Offline R-001 QA: run with: python -m unittest -v test_audit_aapl_zip_v0_2.py"""
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
import hashlib
from audit_aapl_zip_v0_2 import analyze

class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(__file__).resolve().parent.parent / 'r001_aapl_audit.zip'
        if not cls.source.is_file():
            raise unittest.SkipTest('Keep input ZIP one directory above test suite')

    def corrupted(self, modification, refresh_sha=False):
        with zipfile.ZipFile(self.source) as z:
            files = {n: z.read(n) for n in z.namelist()}
        modification(files)
        if refresh_sha:
            manifest=json.loads(files['manifest.json'])
            manifest['sha256_csv']=hashlib.sha256(files['aapl_fmp_2005_2009_ohlcv.csv']).hexdigest()
            files['manifest.json']=json.dumps(manifest).encode()
        fp=tempfile.NamedTemporaryFile(suffix='.zip',delete=False)
        fp.close()
        with zipfile.ZipFile(fp.name,'w') as z:
            for name,b in files.items(): z.writestr(name,b)
        self.addCleanup(Path(fp.name).unlink,missing_ok=True)
        return fp.name

    def test_recompute_first_event(self):
        result=analyze(self.source)
        self.assertEqual(result['row_count'],1259)
        self.assertEqual(result['candidate_count'],75)
        self.assertEqual(result['candidate_label_counts'],{'true':11,'false':37,'censored':27})
        self.assertEqual(result['first_event']['date'],'2006-01-06')
        self.assertFalse(result['first_event']['future_252_label'])
        self.assertEqual(result['first_event']['forward_252_observations'],252)

    def test_checksum_tamper_detected(self):
        def change(files):
            files['aapl_fmp_2005_2009_ohlcv.csv']=files['aapl_fmp_2005_2009_ohlcv.csv'].replace(b'2005-01-03',b'2005-01-04',1)
        with self.assertRaisesRegex(ValueError,'SHA256'):
            analyze(self.corrupted(change))

    def test_invalid_ohlc_detected_even_when_hash_updated(self):
        def change(files):
            blob=files['aapl_fmp_2005_2009_ohlcv.csv']
            files['aapl_fmp_2005_2009_ohlcv.csv']=blob.replace(b'2005-01-03,1.16,1.16,1.12,1.13',b'2005-01-03,1.16,0.01,1.12,1.13',1)
        with self.assertRaisesRegex(ValueError,'OHLC'):
            analyze(self.corrupted(change,refresh_sha=True))

    def test_candidate_tamper_detected(self):
        def change(files):
            b=files['aapl_breakout_candidates_UNVERIFIED.csv'];files['aapl_breakout_candidates_UNVERIFIED.csv']=b.replace(b'2006-01-06',b'2006-01-05',1)
        with self.assertRaisesRegex(ValueError,'Candidate date mismatch'):
            analyze(self.corrupted(change))

    def test_invalid_forward_label_detected(self):
        def change(files):
            b=files['aapl_breakout_candidates_UNVERIFIED.csv'];files['aapl_breakout_candidates_UNVERIFIED.csv']=b.replace(b'False',b'True',1)
        with self.assertRaisesRegex(ValueError,'Forward label mismatch'):
            analyze(self.corrupted(change))

if __name__=='__main__': unittest.main()
