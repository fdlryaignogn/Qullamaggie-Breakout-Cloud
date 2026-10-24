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
  dispatch(req({...base,action:'CONFIRM_EOD_TRIGGER',confirmed:false}),{}),
  e=>e.status===400
 );
 const response=await dispatch(
  req({...base,action:'CONFIRM_EOD_TRIGGER',confirmed:true}),{}
 );
 assert.equal(response.status,202);
 assert.equal(requests.length,1);
 const body=JSON.parse(requests[0].opts.body);
 assert.equal(body.inputs.action,'CONFIRM_EOD_TRIGGER');
 assert.equal(body.inputs.confirmed,'true');
 assert.equal(body.inputs.expected_as_of_date,'2026-10-23');
});
test('Stage3 Action shows required pass/fail evidence and blocks unqualified triggers',()=>{
 const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
 assert.ok(html.includes('function stage3TriggerChecklist(row)'));
 assert.ok(html.includes('function stage3TriggerChecklistHtml(summary)'));
 assert.ok(html.includes("data?.eod_event==='EOD_CROSS'"));
 assert.ok(html.includes("!checks.requiredOK"));
 assert.ok(html.includes("k==='CONFIRM_EOD_TRIGGER'&&!checks.requiredOK?' disabled'"));
 assert.ok(html.includes('成交量比率 RVOL20（不設硬門檻）'));
 assert.ok(html.includes('人工確認 EOD 突破'));
});
