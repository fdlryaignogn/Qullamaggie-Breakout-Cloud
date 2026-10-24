import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const source=readFileSync(new URL('../src/index.js',import.meta.url),'utf8');
const start=source.indexOf('async function dispatchStage3(');
const end=source.indexOf('export default {',start);
assert.ok(start>0&&end>start);

function harness(){
 const requests=[];
 const ctx={
  authenticate:async()=>({t:'sealed-github-token'}),
  checkReviewer:async()=> 'trusted-reviewer',
  githubApi:async (url,token,opts)=>{requests.push({url,token,opts});return {status:204};},
  json:(body,status)=>({body,status}),
  httpError:(status,message)=>Object.assign(new Error(message),{status}),
  REPO:'example/project'
 };
 const dispatch=vm.runInNewContext(source.slice(start,end)+'\ndispatchStage3',ctx);
 function req(data){
  return {
   headers:{get:(key)=>key==='Content-Type'?'application/json':null},
   text:async()=>JSON.stringify(data)
  };
 }
 return {dispatch,req,requests};
}
const base={symbol:'NIQ',setup_id:'NIQ-20261023',action:'KEEP_WATCH',
 review_reason:'EOD remains under observation',confirmed:false,
 expected_revision:'1792797151',expected_as_of_date:'2026-10-23'};

test('Stage 3 EOD action dispatch only approved workflow on main',async()=>{
 const {dispatch,req,requests}=harness();
 const reply=await dispatch(req(base),{});
 assert.equal(reply.status,202);
 assert.equal(reply.body.accepted,true);
 assert.equal(requests.length,1);
 assert.equal(requests[0].url,'/repos/example/project/actions/workflows/review-stage3.yml/dispatches');
 const body=JSON.parse(requests[0].opts.body);
 assert.equal(body.ref,'main');
 assert.equal(body.inputs.action,'KEEP_WATCH');
 assert.equal(body.inputs.expected_revision,'1792797151');
 assert.equal(body.inputs.expected_as_of_date,'2026-10-23');
 assert.equal(body.inputs.confirmed,'false');
});
test('Terminal Stage 3 actions require reviewer confirmation',async()=>{
 const {dispatch,req,requests}=harness();
 for(const action of ['NO_TRADE','ARCHIVE']){
  await assert.rejects(dispatch(req({...base,action,confirmed:false}),{}),
    e=>e.status===400);
  const ok=await dispatch(req({...base,action,confirmed:true}),{});
  assert.equal(ok.status,202);
 }
 assert.equal(requests.length,2);
});
test('reject unsupported triggered, trade or malformed EOD requests',async()=>{
 const {dispatch,req,requests}=harness();
 for(const changed of [
  {action:'TRIGGERED'}, {action:'BUY'}, {action:'INVALIDATED'},
  {expected_revision:'-1'}, {expected_revision:'NaN'},
  {expected_as_of_date:'tomorrow'}, {review_reason:'bad\nline'},
  {review_reason:''}, {setup_id:'WRONG-20261023'}, {symbol:'X/../'}]){
  await assert.rejects(dispatch(req({...base,...changed}),{}),e=>e.status===400);
 }
 assert.equal(requests.length,0);
});
test('cloud dashboard exposes read-only EOD details and authenticated review only',()=>{
 const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
 assert.ok(html.includes('function openStage3Details(row)'));
 assert.ok(html.includes('function openStage3Action(row)'));
 assert.ok(html.includes("if(!reviewAuthenticated()||row?.status!=='WATCH')return"));
 assert.ok(html.includes("STAGE3_REVIEW_WORKFLOW='review-stage3.yml'"));
 assert.ok(html.includes("oauthRequest('/stage3/dispatch'"));
 assert.ok(!source.slice(start,end).includes('TRIGGERED","'));
});

test('human EOD trigger dispatch demands confirmation and pinned snapshot',async()=>{
 const {dispatch,req,requests}=harness();
 await assert.rejects(
  dispatch(req({...base,action:'CONFIRM_TRIGGER',confirmed:false}),{}),
  e=>e.status===400
 );
 const response=await dispatch(
  req({...base,action:'CONFIRM_TRIGGER',confirmed:true}),{}
 );
 assert.equal(response.status,202);
 assert.equal(requests.length,1);
 const body=JSON.parse(requests[0].opts.body);
 assert.equal(body.inputs.action,'CONFIRM_TRIGGER');
 assert.equal(body.inputs.confirmed,'true');
 assert.equal(body.inputs.expected_as_of_date,'2026-10-23');
});
test('Stage3 Action shows required pass/fail evidence and blocks unqualified triggers',()=>{
 const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
 assert.ok(html.includes('function stage3TriggerChecklist(row,mode='));
 assert.ok(html.includes('function stage3TriggerChecklistHtml(summary)'));
 assert.ok(html.includes("data?.eod_event==='EOD_CROSS'"));
 assert.ok(html.includes("function stage3ActionAvailability("));
 assert.ok(html.includes("!stage3ActionAvailability(action,checks,lateChecks,currentEodEvent()).canSubmit"));
 assert.ok(html.includes("submit.disabled=true"));
 assert.ok(html.includes("stage3DecisionStatus"));
 assert.ok(html.includes('成交量比率 RVOL20（不設硬門檻）'));
 assert.ok(html.includes("['CONFIRM_TRIGGER',tl('確認 TRIGGERED（自動判斷突破類型）'"));
 const start=html.indexOf('function openStage3Action(row){');
 const modal=html.slice(start,html.indexOf('function openReviewForm(',start));
 assert.equal((modal.match(/\['CONFIRM_TRIGGER',tl\(/g)||[]).length,1);
 assert.ok(!modal.includes("['CONFIRM_EOD_TRIGGER',tl("));
 assert.ok(!modal.includes("['CONFIRM_POST_APPROVAL',tl("));
});

test('Stage 3 browser checklist computes pass/fail and does not gate on volume multiplier',()=>{
 const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
 const start=html.indexOf('function stage3TriggerChecklist(row,mode=');
 const end=html.indexOf('function openStage3Action(row){',start);
 assert.ok(start>=0&&end>start);
 const parent={symbol:'ABC',setup_id:'ABC-1',setup_status:'READY',
  manual_reviewer:'human',manual_reviewed_at:'2026-10-23T19:00:00+00:00'};
 const row={symbol:'ABC',setup_id:'ABC-1',status:'WATCH',breakout_level:100,
  eod_data_status:'FRESH',eod_as_of:'2026-10-23'};
 const metric={eod_as_of:'2026-10-23',eod_event:'EOD_CROSS',
  eod_prev_close:99.5,eod_close:100.5,eod_volume_ratio:null,
  eod_atr14:2,eod_adr20_pct:4,eod_ref_risk_atr:null};
 const ctx={serverMeta:{phase:'success',last_success:'2026-10-23T23:00:00Z',
  as_of_date:'2026-10-23'},state:{'2':[parent]},stage3CurrentEod:()=>metric,
  tl:(a)=>a,fmtNum:String,pct:String};
 const decide=vm.runInNewContext(html.slice(start,end)+'\nstage3TriggerChecklist',ctx);
 const ok=decide(row);
 assert.equal(ok.requiredOK,true);
 assert.equal(ok.checks.every(c=>c.pass),true);
 assert.equal(ok.context[0][1],'—');
 parent.manual_reviewed_at='2026-10-24T05:56:07+00:00';
 const late=decide(row);
 assert.equal(late.requiredOK,false);
 assert.equal(late.checks.some(c=>!c.pass&&c.label.includes('核准時間')),true);
 parent.manual_reviewed_at='2026-10-23T19:00:00';
 assert.equal(decide(row).requiredOK,false); // time zone missing
 parent.manual_reviewed_at='2026-10-23T19:00:00+00:00';
 metric.eod_event='ABOVE_PIVOT';
 assert.equal(decide(row).requiredOK,false);
});

test('only canonical CONFIRM_TRIGGER is dispatched; prior aliases are not public options',async()=>{
 const {dispatch,req,requests}=harness();
 for(const action of ['CONFIRM_EOD_TRIGGER','CONFIRM_POST_APPROVAL']){
  await assert.rejects(dispatch(req({...base,action,confirmed:true}),{}),e=>e.status===400);
 }
 const response=await dispatch(req({...base,action:'CONFIRM_TRIGGER',confirmed:true}),{});
 assert.equal(response.status,202);
 assert.equal(JSON.parse(requests[0].opts.body).inputs.action,'CONFIRM_TRIGGER');
 assert.equal(requests.length,1);
});

test('Saturday READY approval allows Monday above-pivot, but not older Friday observation',()=>{
 const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
 const start=html.indexOf('function stage3TriggerChecklist(row,mode=');
 const end=html.indexOf('function openStage3Action(row){',start);
 assert.ok(start>0&&end>start);
 const parent={symbol:'ABC',setup_id:'ABC-1',setup_status:'READY',
  manual_reviewer:'human',manual_reviewed_at:'2026-10-24T05:56:07+00:00'};
 const row={symbol:'ABC',setup_id:'ABC-1',status:'WATCH',
  breakout_level:100,eod_as_of:'2026-10-26',eod_data_status:'FRESH'};
 const observation={eod_as_of:'2026-10-26',eod_event:'ABOVE_PIVOT',
  eod_prev_close:101,eod_close:102,eod_volume_ratio:.8};
 const meta={phase:'success',last_success:'2026-10-26T23:00:00Z',as_of_date:'2026-10-26'};
 const ctx={serverMeta:meta,state:{'2':[parent]},stage3CurrentEod:()=>observation,
  tl:v=>v,fmtNum:String,pct:String};
 const check=vm.runInNewContext(html.slice(start,end)+'\nstage3TriggerChecklist',ctx);
 assert.equal(check(row,'CONFIRM_POST_APPROVAL').requiredOK,true);
 assert.equal(check(row,'CONFIRM_EOD_TRIGGER').requiredOK,false);
 meta.as_of_date='2026-10-23';
 row.eod_as_of='2026-10-23';
 observation.eod_as_of='2026-10-23';
 assert.equal(check(row,'CONFIRM_POST_APPROVAL').requiredOK,false);
 meta.as_of_date='2026-10-26';
 row.eod_as_of='2026-10-26';
 observation.eod_as_of='2026-10-26';
 parent.manual_reviewed_at='2026-10-26T21:00:00+00:00';
 assert.equal(check(row,'CONFIRM_POST_APPROVAL').requiredOK,false);
});

test('single Trigger action automatically shows only matching first/hold checklist',()=>{
 const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
 const start=html.indexOf('function stage3ActionAvailability(');
 const end=html.indexOf('function openStage3Action(row){',start);
 assert.ok(start>=0&&end>start);
 const decide=vm.runInNewContext(html.slice(start,end)+'\nstage3ActionAvailability',{tl:z=>z});
 const first={requiredOK:true,mode:'CONFIRM_EOD_TRIGGER',checks:[
  {label:'First EOD close-cross',pass:true,required:true}]};
 const hold={requiredOK:true,mode:'CONFIRM_POST_APPROVAL',checks:[
  {label:'Post approval hold',pass:true,required:true}]};
 let result=decide('CONFIRM_TRIGGER',first,hold,'EOD_CROSS');
 assert.equal(result.canSubmit,true);
 assert.equal(result.pattern,'FIRST_EOD_CROSS');
 assert.equal(result.report.mode,'CONFIRM_EOD_TRIGGER');
 result=decide('CONFIRM_TRIGGER',first,hold,'ABOVE_PIVOT');
 assert.equal(result.canSubmit,true);
 assert.equal(result.pattern,'POST_APPROVAL_HOLD');
 assert.equal(result.report.mode,'CONFIRM_POST_APPROVAL');
 result=decide('CONFIRM_TRIGGER',first,hold,'BELOW_PIVOT');
 assert.equal(result.canSubmit,false);
 assert.equal(result.pattern,null);
 assert.equal(result.failed.length,1);
 const block={requiredOK:false,mode:'CONFIRM_POST_APPROVAL',checks:[
  {label:'READY approval too late',pass:false,required:true}]};
 result=decide('CONFIRM_TRIGGER',first,block,'ABOVE_PIVOT');
 assert.equal(result.canSubmit,false);
 assert.equal(result.failed[0].label,'READY approval too late');
 assert.equal(decide('KEEP_WATCH',first,block,'BELOW_PIVOT').canSubmit,true);
 const modalStart=html.indexOf('function openStage3Action(row){');
 const modal=html.slice(modalStart,html.indexOf('function openReviewForm(',modalStart));
 assert.ok(modal.includes("['CONFIRM_TRIGGER',tl("));
 assert.ok(!modal.includes("['CONFIRM_EOD_TRIGGER',tl("));
 assert.ok(!modal.includes("['CONFIRM_POST_APPROVAL',tl("));
 assert.ok(modal.includes('submit.disabled=true'));
 assert.ok(modal.includes('stage3DecisionStatus'));
 assert.ok(modal.includes('currentEodEvent()'));
});
test('browser cutoff matches backend exact 16:00:00 New York rule',()=>{
 const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
 const start=html.indexOf('function stage3TriggerChecklist(row,mode=');
 const end=html.indexOf('function stage3TriggerChecklistHtml(',start);
 const parent={symbol:'ABC',setup_id:'ABC-1',setup_status:'READY',
  manual_reviewer:'human',manual_reviewed_at:'2026-10-23T20:00:00+00:00'};
 const row={symbol:'ABC',setup_id:'ABC-1',breakout_level:100,
  eod_data_status:'FRESH',eod_as_of:'2026-10-23'};
 const event={eod_as_of:'2026-10-23',eod_event:'EOD_CROSS',
  eod_prev_close:99,eod_close:101};
 const c={serverMeta:{phase:'success',last_success:'2026-10-23T23:00:00Z',
  as_of_date:'2026-10-23'},state:{'2':[parent]},
  stage3CurrentEod:()=>event,tl:a=>a,fmtNum:String,pct:String,Intl,Date,Number};
 const check=vm.runInNewContext(html.slice(start,end)+'\nstage3TriggerChecklist',c);
 assert.equal(check(row).requiredOK,true);
 parent.manual_reviewed_at='2026-10-23T20:00:01+00:00';
 assert.equal(check(row).requiredOK,false);
});
