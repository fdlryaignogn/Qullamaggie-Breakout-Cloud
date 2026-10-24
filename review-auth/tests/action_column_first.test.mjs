import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../../site/index.html', import.meta.url), 'utf8');
const renderStart=html.indexOf('function render(){');
const renderEnd=html.indexOf('\nfunction switchTab(', renderStart);
assert.ok(renderStart>=0 && renderEnd>renderStart);
const render=html.slice(renderStart,renderEnd);

test('all stage tables put Action header before every data column',()=>{
  const header=render.indexOf('innerHTML=\'<tr><th scope="col" title="\'');
  const fields=render.indexOf('config.columns.map(([key,name])');
  assert.ok(header>=0 && fields>header);
  assert.ok(!render.includes(".join('')+'<th>'+t('操作')"));
});
test('all stage tables place action cells first while retaining stock columns and review buttons',()=>{
  const row=render.indexOf('return `<tr><td><div class="cell-actions">');
  const fields=render.indexOf("config.columns.map(([key])",row);
  assert.ok(row>=0 && fields>row);
  // Review button is built into reviewAction before row rendering, then inserted into first cell.
  assert.ok(render.includes('data-act="review"'));
  assert.ok(render.slice(row,fields).includes('${reviewAction}'));
  assert.ok(render.slice(row,fields).includes('data-act="edit"'));
  assert.ok(render.slice(row,fields).includes('data-act="remove"'));
  assert.ok(render.includes("reviewAuthenticated()&&stage===2"));
});
test('the first column remains sticky during horizontal scrolling',()=>{
  assert.ok(html.includes('th:first-child,td:first-child{position:sticky;left:0'));
});

test('table header freezes during vertical scrolling and Action corner stays above it',()=>{
  assert.ok(html.includes('.table-wrap{width:100%;overflow:auto;max-height:min(72vh,760px)'));
  assert.ok(html.includes('thead th{'));
  assert.ok(html.includes('position:sticky;top:0;z-index:3;background:#151f33'));
  assert.ok(html.includes('thead th:first-child{z-index:5}'));
  assert.ok(html.includes('id="tableWrap" tabindex="0" role="region"'));
});
