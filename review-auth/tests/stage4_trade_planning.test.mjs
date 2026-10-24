import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const main=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
const page=readFileSync(new URL('../../site/stage4.html',import.meta.url),'utf8');
const script=page.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script,'Stage4 browser script must exist');
const start=script.indexOf('function stage4SizePlan(i){');
const stop=script.indexOf('function riskInputs(){',start);
assert.ok(start>=0&&stop>start);
const size=vm.runInNewContext(script.slice(start,stop)+'\nstage4SizePlan');

function scenario(other={}){
 return {equity:10000,riskPct:1,cash:1000,entry:100,stop:95,
  slippage:0,fees:10,lot:1,target:110,...other};
}
test('stage4 page JavaScript compiles without browser side effects',()=>{
 assert.doesNotThrow(()=>new vm.Script(script));
});
test('fourth stage is an actual tab linked from the dashboard; previous 3 remain',()=>{
 assert.ok(main.includes('href="./stage4.html"'));
 assert.ok(main.includes('id="count4"'));
 assert.ok(main.includes("state['3'].filter(r=>r.status==='TRIGGERED').length"));
 assert.ok(main.includes("document.querySelectorAll('.tab[data-stage]')"));
 assert.ok(page.includes('aria-current="page"'));
 assert.ok(page.includes('href="./index.html#stage-3"'));
});
test('stage4 only displays actual TRIGGERED status from published snapshot',()=>{
 assert.ok(script.includes("r.status==='TRIGGERED'"));
 assert.ok(script.includes("state.metadata?.phase!=='success'"));
 assert.ok(script.includes("fetch('./data/latest.json?v='"));
 assert.ok(!script.includes("r.eod_event==='EOD_CROSS'&&r.status!=='TRIGGERED'"));
});
test('risk calculator obeys both cash cap and per-trade risk and fixed fees',()=>{
 const p=size(scenario());
 assert.equal(p.ok,true);
 assert.equal(p.budget,100);
 assert.equal(p.assumedEntry,100);
 assert.equal(p.perShare,5);
 assert.equal(p.byRisk,18);
 assert.equal(p.byCash,9);
 assert.equal(p.shares,9);
 assert.equal(p.totalRisk,55);
 assert.equal(p.cashUsed,910);
 assert.equal(p.targetR,2);
 assert.ok(p.totalRisk<=p.budget&&p.cashUsed<=1000);
});
test('risk cap, lot rounding and slippage alter shares properly',()=>{
 const p=size(scenario({cash:10000,riskPct:.5,fees:0,entry:100,stop:90,lot:3,target:120}));
 assert.equal(p.shares,3); // risk cap 5 shares rounded to multiples of 3
 const withSlip=size(scenario({entry:100,stop:99,slippage:1,fees:0,cash:10000}));
 assert.equal(withSlip.assumedEntry,101);
 assert.equal(withSlip.perShare,2);
 assert.equal(withSlip.shares,50);
});
test('missing, erroneous, oversized fees, reverse stops and cash limits fail closed',()=>{
 assert.equal(size(scenario({equity:NaN})).error,'MISSING_INPUT');
 assert.equal(size(scenario({cash:0})).error,'INVALID_INPUT');
 assert.equal(size(scenario({riskPct:0})).error,'INVALID_INPUT');
 assert.equal(size(scenario({stop:101})).error,'ENTRY_NOT_ABOVE_STOP');
 assert.equal(size(scenario({fees:100})).error,'FEES_EXCEED_BUDGET');
 assert.equal(size(scenario({lot:1.5})).error,'INVALID_INPUT');
 assert.equal(size(scenario({slippage:-1})).error,'INVALID_INPUT');
 assert.equal(size(scenario({riskPct:120})).error,'INVALID_INPUT');
});
test('budget too small yields zero shares not synthetic holdings',()=>{
 const p=size(scenario({equity:1000,riskPct:.1,cash:1000,entry:100,stop:90,fees:0}));
 assert.equal(p.ok,true);
 assert.equal(p.shares,0);
 assert.equal(p.totalRisk,0);
});
test('no SEC information is represented as unknown and 13F/Form4 are not inferred buys',()=>{
 assert.ok(page.includes('institutionStatus'));
 assert.ok(page.includes('insiderStatus'));
 assert.ok(script.includes("byId('institutionStatus').textContent=tr('未核實','Not verified')"));
 assert.ok(script.includes("byId('insiderStatus').textContent=tr('未核實','Not verified')"));
 assert.ok(page.includes('data/stage4_fundamentals.json'));
 assert.ok(page.includes('資料可能延遲或缺失'));
 assert.ok(page.includes('Form 4 有申報不代表買入'));
});
test('private account equity and risk figures are not saved into public state or localStorage',()=>{
 assert.ok(!script.includes('localStorage.setItem('+"'risk'"));
 assert.ok(!script.includes('localStorage.setItem('+"'equity'"));
 assert.ok(script.includes('const evidenceKey='));
 assert.ok(script.includes('not independently verified')||page.includes('未由系統核實'));
 assert.ok(!script.includes("fetch('/api/order'"));
});
test('reject malicious evidence source URLs',()=>{
 const begin=script.indexOf('function evidenceSource(url){'),end=script.indexOf('function renderEvidence(){',begin);
 const judge=vm.runInNewContext(script.slice(begin,end)+'\nevidenceSource',{URL});
 assert.equal(judge('javascript:alert(1)'),null);
 assert.equal(judge('http://www.sec.gov/x'),null);
 assert.equal(judge('https://user:pass@sec.gov/'),null);
 assert.equal(judge('https://www.sec.gov/search-filings'),'https://www.sec.gov/search-filings');
});
