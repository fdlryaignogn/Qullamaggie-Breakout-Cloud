"""Stage-3 EOD annotations: descriptive only, no fills or intraday assumptions."""
import pandas as pd
from stage3_eod import eod_observation,enrich_stage3_eod


def bars(last_close=100.5,prior_close=99.5,last_high=102,last_low=98,volume=200):
    ix=pd.bdate_range('2026-09-01',periods=40)
    df=pd.DataFrame({'open':[99.5]*40,'high':[101.0]*40,
      'low':[98.0]*40,'close':[99.5]*40,'volume':[100]*40},index=ix)
    df.loc[ix[-2],'close']=prior_close
    df.loc[ix[-1],['close','high','low','volume']]=[last_close,last_high,last_low,volume]
    return df,ix[-1].strftime('%Y-%m-%d')


def test_cross_above_pivot_is_observation_not_trigger():
    df,asof=bars()
    x=eod_observation(df,100,asof)
    assert x['eod_event']=='EOD_CROSS'
    assert x['eod_distance_pct']==.5
    assert x['eod_volume_ratio']==2
    assert x['eod_atr14'] is not None
    assert x['eod_adr20_pct'] is not None
    assert x['eod_ref_stop']==98
    assert x['eod_ref_risk_per_share']==2
    assert x['eod_ref_risk_atr']>0
    assert not set(x)&{'trigger_price','trigger_time','initial_stop','risk_per_share','suggested_max_shares','status'}


def test_other_eod_states_are_descriptive_only():
    df,asof=bars(last_close=101,prior_close=100.2)
    assert eod_observation(df,100,asof)['eod_event']=='ABOVE_PIVOT'
    df,asof=bars(last_close=99.5,prior_close=99.0)
    assert eod_observation(df,100,asof)['eod_event']=='TOUCH_ONLY'
    df,asof=bars(last_close=99.5,prior_close=99.0,last_high=99.8)
    assert eod_observation(df,100,asof)['eod_event']=='BELOW_PIVOT'


def test_maturity_and_data_limits_no_fill_no_future():
    df,asof=bars()
    assert eod_observation(df.iloc[:5],100,asof) is None
    assert eod_observation(df,100,'2026-09-01') is None
    assert eod_observation(df,0,asof) is None
    df.loc[df.index[-1],'volume']=0
    assert eod_observation(df,100,asof)['eod_volume_ratio'] is None
    # Missing long windows are unavailable, not zero.
    partial=eod_observation(df.tail(10),100,asof)
    assert partial['eod_volume_ratio'] is None and partial['eod_atr14'] is None
    assert partial['eod_adr20_pct'] is None


def test_enrichment_preserves_human_ready_pivot_and_manual_trade_fields():
    df,asof=bars()
    state={'2':[{'symbol':'ABC','setup_id':'ABC-20261023','setup_status':'READY','base_high':100}],
      '3':[{'symbol':'ABC','setup_id':'ABC-20261023','status':'WATCH',
            'breakout_level':100,'initial_stop':96,'risk_per_share':4,
            'trigger_rule':'requires independent 5-min bars'}]}
    enrich_stage3_eod(state,{'ABC':df},asof)
    watch=state['3'][0]
    assert watch['status']=='WATCH'
    assert watch['breakout_level']==100
    assert watch['initial_stop']==96 and watch['risk_per_share']==4
    assert watch['trigger_rule']=='requires independent 5-min bars'
    assert watch['eod_as_of']==asof
    stale=(pd.bdate_range('2026-09-01',periods=41)[-1]).strftime('%Y-%m-%d')
    enrich_stage3_eod(state,{'ABC':df},stale)
    assert watch['eod_data_status']=='STALE_OR_INSUFFICIENT'
    assert watch['eod_as_of']==asof
    state['2'][0]['setup_status']='FORMING'
    enrich_stage3_eod(state,{'ABC':df},asof)
    assert watch['eod_data_status']=='PAUSED'
    assert watch['status']=='WATCH'
    state['2'][0]['setup_status']='READY'
    watch['status']='TRIGGERED'
    before=dict(watch)
    enrich_stage3_eod(state,{'ABC':df},asof)
    assert watch==before


def test_no_invalid_last_day_stop_when_low_exceeds_pivot():
    df,asof=bars(last_close=108,prior_close=106,last_low=104,last_high=110)
    result=eod_observation(df,100,asof)
    assert result['eod_ref_stop'] is None
    assert result['eod_ref_risk_per_share'] is None
