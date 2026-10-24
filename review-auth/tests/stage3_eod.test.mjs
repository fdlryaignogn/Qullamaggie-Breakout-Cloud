import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
const from=html.indexOf('function eodFromPublishedBars(');
const to=html.indexOf('function scheduleStage3Eod(',from);
assert.ok(from>=0&&to>from);
const helpers=vm.runInNewContext(html.slice(from,to)+'\n({calc:eodFromPublishedBars,verified:eodFromVerifiedChart})');
const {calc,verified}=helpers;
function chart({lastClose=100.5,priorClose=99.5,lastHigh=102,lastLow=98,lastVol=200}={}){
 const bars=[];
 for(let i=0;i<41;i++){
   const date=new Date(Date.UTC(2026,8,1+i));
   if(date.getUTCDay()===0||date.getUTCDay()===6)continue;
   bars.push({date:date.toISOString().slice(0,10),open:99.5,high:101,low:98,close:99.5,volume:100});
 }
 bars[bars.length-2].close=priorClose;
 Object.assign(bars[bars.length-1],{close:lastClose,high:lastHigh,low:lastLow,volume:lastVol});
 return bars;
}
test('cross above saved pivot is descriptive only, not auto trigger',()=>{
 const bars=chart();const asOf=bars.at(-1).date;
 const r=calc(bars,100,asOf);
 assert.equal(r.eod_event,'EOD_CROSS');
 assert.equal(r.eod_distance_pct,.5);
 assert.equal(r.eod_volume_ratio,2);
 assert.ok(r.eod_atr14>0&&r.eod_adr20_pct>0);
 assert.equal(r.eod_ref_stop,98);
 assert.equal(r.eod_ref_risk_per_share,2);
 assert.ok(r.eod_ref_risk_atr>0);
 assert.ok(!('status' in r) && !('trigger_time' in r));
});
test('multiple EOD observations and data limits',()=>{
 let b=chart({lastClose:101,priorClose:100.5});
 assert.equal(calc(b,100,b.at(-1).date).eod_event,'ABOVE_PIVOT');
 b=chart({lastClose:99.5,priorClose:99.5});
 assert.equal(calc(b,100,b.at(-1).date).eod_event,'TOUCH_ONLY');
 b=chart({lastClose:99.5,priorClose:99.5,lastHigh:99.8});
 assert.equal(calc(b,100,b.at(-1).date).eod_event,'BELOW_PIVOT');
 assert.equal(calc(b,100,'2026-09-01'),null);
 assert.equal(calc(b,0,b.at(-1).date),null);
 b=chart({lastVol:0});
 assert.equal(calc(b,100,b.at(-1).date).eod_volume_ratio,null);
 assert.equal(calc(b.slice(-8),100,b.at(-1).date).eod_atr14,null);
});
test('approved stage3 UI shows compact EOD columns, no invented intraday action',()=>{
 assert.ok(html.includes("['eod_event','日線觀察結果']"));
 assert.ok(html.includes("['eod_atr14','ATR 14 日']"));
 assert.ok(html.includes("['eod_ref_risk_atr','參考風險 / ATR']"));
 assert.ok(html.includes('function scheduleStage3Eod()'));
 assert.ok(html.includes("if(stage===3)scheduleStage3Eod()"));
 assert.ok(html.includes("if(watch.status!=='WATCH')continue"));
 assert.ok(html.includes("if(serverMeta?.as_of_date!==asOf)return"));
 assert.ok(html.includes("eodFromVerifiedChart(chart,watch,asOf)"));
 assert.ok(html.includes('CLOUD_MODE&&reviewAuthenticated()&&stage===2'));
});

test('published chart provenance is enforced before deriving WATCH values',()=>{
 const bars=chart(),asOf=bars.at(-1).date;
 const watch={symbol:'ABC',setup_id:'ABC-1',breakout_level:100,status:'WATCH'};
 const payload={symbol:'ABC',as_of:asOf,interval:'1d',adjusted:true,bars};
 assert.equal(verified(payload,watch,asOf).eod_event,'EOD_CROSS');
 for(const changed of [
   {symbol:'OTHER'}, {as_of:'2026-09-01'}, {interval:'5m'}, {adjusted:false},
   {adjusted:null}, {bars:[]}
 ]){
   assert.equal(verified({...payload,...changed},watch,asOf),null);
 }
 assert.equal(verified(payload,{...watch,symbol:'OTHER'},asOf),null);
});
test('cached EOD columns are displayed only for current published session',()=>{
 assert.ok(html.includes("cached?.eod_as_of===serverMeta?.as_of_date"));
 assert.ok(html.includes("if(serverMeta?.as_of_date!==asOf)return"));
});
