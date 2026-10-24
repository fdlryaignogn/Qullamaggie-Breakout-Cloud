import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
const begin=html.indexOf('function stage2ReviewClose(row){');
const end=html.indexOf('function renderStage2ReviewGroups(){',begin);
assert.ok(begin>0 && end>begin,'Stage 2 grouping helpers must be present in dashboard');
const helpers=vm.runInNewContext(
  html.slice(begin,end)+'\n({ stage2ReviewGroup, stage2ReviewDistance, stage2ReviewClose })'
);
const row=(close,high,status='FORMING',recommendation='READY_CANDIDATE')=>({
  setup_status:status,readiness_recommendation:recommendation,
  base_high:high,moving_average_context:'close='+close+', SMA20=18.34, SMA50=16.41'
});
test('above base high is review only, not auto-approved breakout',()=>{
 assert.equal(helpers.stage2ReviewGroup(row(102,100)),'above');
 assert.ok(helpers.stage2ReviewDistance(row(102,100))<0);
});
test('strictly at ceiling and <=3% below is near',()=>{
 assert.equal(helpers.stage2ReviewGroup(row(100,100)),'near');
 assert.equal(helpers.stage2ReviewGroup(row(100,103)),'near');
 assert.equal(helpers.stage2ReviewGroup(row(100,103.01)),'observe');
});
test('further-away setups and missing prices need observation',()=>{
 assert.equal(helpers.stage2ReviewGroup(row(90,100)),'observe');
 assert.equal(helpers.stage2ReviewGroup({setup_status:'FORMING',readiness_recommendation:'READY_CANDIDATE',base_high:10}),'observe');
 assert.equal(helpers.stage2ReviewDistance({base_high:10,moving_average_context:'SMA20=8'}),null);
 assert.equal(helpers.stage2ReviewGroup(row(10,0)),'observe');
});
test('never place ordinary FORMING, approved READY, rejected or invalidated setups in review queue',()=>{
 assert.equal(helpers.stage2ReviewGroup(row(101,100,'FORMING','FORMING')),'');
 assert.equal(helpers.stage2ReviewGroup(row(101,100,'READY')),'');
 assert.equal(helpers.stage2ReviewGroup(row(101,100,'INVALIDATED')),'');
 assert.equal(helpers.stage2ReviewGroup(row(101,100,'DEVELOPING')),'above');
});
test('published candidate snapshot is partitioned without duplicates',()=>{
 const published=JSON.parse(readFileSync(new URL('../../site/data/latest.json',import.meta.url),'utf8'));
 const groups={above:0,near:0,observe:0};
 let candidates=0;
 for(const setup of published.state['2']){
   const group=helpers.stage2ReviewGroup(setup);
   if(group){assert.ok(Object.hasOwn(groups,group));groups[group]++;candidates++;}
 }
 assert.equal(groups.above+groups.near+groups.observe,candidates);
 if(published.metadata.as_of_date==='2026-10-23'){
   assert.deepEqual(groups,{above:4,near:8,observe:6});
   assert.equal(candidates,18);
 }
});
test('interactive groups keep the dashboard read-only and human review protected',()=>{
 assert.ok(html.includes('id="reviewQueuesCards"'));
 assert.ok(html.includes("stage2ReviewGroup(r)!==ui.reviewGroup"));
 assert.ok(html.includes("reviewAuthenticated()&&stage===2"));
 assert.ok(html.includes('READY_CANDIDATE'));
 assert.ok(html.includes("reviewQueuesReset"));
});
