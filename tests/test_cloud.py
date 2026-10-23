import json
from pathlib import Path
import pytest
import cloud_scan


def snapshot(asof='2026-10-22', coverage=.98,mode='us'):
    return {'metadata':{'phase':'success','last_success':'2026-10-23T06:31:00+00:00',
                        'last_scan_universe_mode':mode,'universe_size':6000,
                        'coverage':coverage,'as_of_date':asof,'market_coverage_pct':coverage*100},
            'state':{'1':[{'symbol':'ABCD','status':'ACTIVE'}],'2':[],'3':[],
                     'history':[],'updatedAt':None}}


def test_cloud_publishing_success_and_no_stale_prices(tmp_path,monkeypatch):
    site=tmp_path/'site'; data=tmp_path/'data'; (data/'price_cache').mkdir(parents=True)
    cloud_scan.SITE=site
    cloud_scan.LATEST=site/'data'/'latest.json'
    cloud_scan.DATA=data
    monkeypatch.setattr(cloud_scan,'last_complete_session',lambda:'2026-10-22')
    (data/'price_cache'/'ABCD.json').write_text(json.dumps({'symbol':'ABCD','as_of':'2026-10-22','bars':[]}),encoding='utf-8')
    cloud_scan.publish(snapshot())
    payload=json.loads(cloud_scan.LATEST.read_text())
    assert payload['state']['1'][0]['symbol']=='ABCD'
    assert payload['metadata']['public_chart_count']==1
    assert (site/'data'/'charts'/'ABCD.json').exists()
    before=cloud_scan.LATEST.read_bytes()
    with pytest.raises(RuntimeError,match='coverage'):
        cloud_scan.publish(snapshot(coverage=.88))
    assert cloud_scan.LATEST.read_bytes()==before
    with pytest.raises(RuntimeError,match='stale'):
        cloud_scan.publish(snapshot(asof='2026-10-20'))
    assert cloud_scan.LATEST.read_bytes()==before


def test_small_or_wrong_universe_refused(tmp_path,monkeypatch):
    monkeypatch.setattr(cloud_scan,'last_complete_session',lambda:'2026-10-22')
    with pytest.raises(RuntimeError,match='full-US'):
        cloud_scan.publish(snapshot(mode='file'))
    obj=snapshot();obj['metadata']['universe_size']=57
    with pytest.raises(RuntimeError,match='Suspiciously small'):
        cloud_scan.publish(obj)