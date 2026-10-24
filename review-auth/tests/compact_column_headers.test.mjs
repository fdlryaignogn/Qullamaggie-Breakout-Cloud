import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
const configStart=html.indexOf('const stages={');
const configEnd=html.indexOf('const esc=',configStart);
assert.ok(configStart>=0&&configEnd>configStart,'Stage definitions and column abbreviations are present');
const definitions=html.slice(configStart,configEnd);
const {stages,COLUMN_ABBREVIATIONS,columnFullTitle}=vm.runInNewContext(
  `const t=value=>value;const tl=(zh,en)=>zh;\n${definitions}\n({stages,COLUMN_ABBREVIATIONS,columnFullTitle})`
);

test('all 3 stages use a short heading for every listed stock column',()=>{
  for(const stage of [1,2,3]){
    for(const [key,name] of stages[stage].columns){
      assert.equal(typeof COLUMN_ABBREVIATIONS[key],'string',`Stage ${stage}: ${key}`);
      assert.ok(COLUMN_ABBREVIATIONS[key].length<=11,`Long abbreviation: ${key}`);
      assert.ok(columnFullTitle(stage,key,name).length>=name.length,`Stage ${stage}: ${key} loses full label`);
    }
  }
});
test('financial indicators have unambiguous separate short labels',()=>{
  assert.notEqual(COLUMN_ABBREVIATIONS.return_1m,COLUMN_ABBREVIATIONS.rank_pct_1m);
  assert.notEqual(COLUMN_ABBREVIATIONS.return_3m,COLUMN_ABBREVIATIONS.rank_pct_3m);
  assert.notEqual(COLUMN_ABBREVIATIONS.return_6m,COLUMN_ABBREVIATIONS.rank_pct_6m);
  assert.ok(columnFullTitle(1,'rank_pct_1m','1M 百分位').includes('越小'));
  assert.equal(COLUMN_ABBREVIATIONS.symbol,'Ticker');
});
test('full field names are shown on mouse hover with accessible keyboard sorting',()=>{
  assert.ok(html.includes('title="${esc(columnFullTitle(stage,key,name))}"'));
  assert.ok(html.includes('aria-label="${esc(columnFullTitle(stage,key,name))}" tabindex="0"'));
  assert.ok(html.includes("byId('thead').addEventListener('keydown'"));
  assert.ok(html.includes('data-sort="${esc(key)}"'));
  assert.ok(html.includes("scope=\"col\""));
});
test('table width is content-driven with smaller spacing; sticky frozen headline preserved',()=>{
  assert.ok(html.includes('width:max-content;min-width:100%'));
  assert.ok(!html.includes('min-width:1090px'));
  assert.ok(html.includes('thead th{padding:10px 7px'));
  assert.ok(html.includes('tbody td{padding:10px 7px'));
  assert.ok(html.includes('.cell-actions{max-width:126px;gap:3px 7px'));
  assert.ok(html.includes('position:sticky;top:0;z-index:3;background:#151f33'));
  assert.ok(html.includes('th:first-child,td:first-child{position:sticky;left:0'));
});
test('data field keys and status authorization flows stay separate from display labels',()=>{
  assert.ok(html.includes('config.columns.map(([key])=>`<td>${cellValue(row,key,stage)}</td>`)'));
  assert.ok(html.includes('CLOUD_MODE&&reviewAuthenticated()&&stage===2'));
  assert.ok(html.includes("ui.sortBy=th.dataset.sort"));
});
