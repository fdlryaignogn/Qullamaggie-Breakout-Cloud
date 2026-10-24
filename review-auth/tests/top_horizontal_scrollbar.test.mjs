import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html=readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
const begin=html.indexOf('function syncTopTableScrollbar(){');
const end=html.indexOf('function render(){',begin);
assert.ok(begin>=0&&end>begin,'synchronized top scrollbar code is present');
const elements={
  stocksTable:{scrollWidth:1788,getBoundingClientRect:()=>({width:1788})},
  tableWrap:{clientWidth:720,scrollLeft:0,events:{},addEventListener(name,fn){this.events[name]=fn;}},
  tableTopScroll:{scrollLeft:0,hidden:true,events:{},addEventListener(name,fn){this.events[name]=fn;}},
  tableTopScrollInner:{style:{}},
};
const callbacks=[];
class Observer{
  constructor(cb){callbacks.push(cb);}
  observe(){}
}
const ctx={byId:id=>elements[id],window:{events:{},addEventListener(name,fn){this.events[name]=fn;}},ResizeObserver:Observer};
const helpers=vm.runInNewContext(html.slice(begin,end)+'\n({syncTopTableScrollbar,wireTopTableScrollbar})',ctx);

test('scrollbar sits beneath panel toolbar and before stock table',()=>{
 const rail=html.indexOf('id="tableTopScroll"');
 const table=html.indexOf('id="tableWrap"');
 const toolbar=html.indexOf('class="toolbar"');
 assert.ok(toolbar<rail&&rail<table);
 assert.ok(html.includes('class="table-top-scroll-inner" id="tableTopScrollInner"'));
});
test('top scrollbar only visible when total table width exceeds viewport',()=>{
 helpers.syncTopTableScrollbar();
 assert.equal(elements.tableTopScrollInner.style.width,'1788px');
 assert.equal(elements.tableTopScroll.hidden,false);
 elements.stocksTable.scrollWidth=690;
 elements.stocksTable.getBoundingClientRect=()=>({width:690});
 helpers.syncTopTableScrollbar();
 assert.equal(elements.tableTopScroll.hidden,true);
 elements.stocksTable.scrollWidth=1788;
 elements.stocksTable.getBoundingClientRect=()=>({width:1788});
});
test('drag top rail, native table scroll and resize remain synchronized',()=>{
 helpers.wireTopTableScrollbar();
 helpers.syncTopTableScrollbar();
 elements.tableTopScroll.scrollLeft=145;
 elements.tableTopScroll.events.scroll();
 assert.equal(elements.tableWrap.scrollLeft,145);
 elements.tableWrap.scrollLeft=460;
 elements.tableWrap.events.scroll();
 assert.equal(elements.tableTopScroll.scrollLeft,460);
 elements.tableWrap.clientWidth=800;
 ctx.window.events.resize();
 assert.equal(elements.tableTopScroll.hidden,false);
 assert.equal(callbacks.length,1);
 callbacks[0]();
});
test('table header and Action column are still frozen',()=>{
 assert.ok(html.includes('position:sticky;top:0;z-index:3;background:#151f33'));
 assert.ok(html.includes('th:first-child,td:first-child{position:sticky;left:0'));
 assert.ok(html.includes('id="tableTopScroll"'));
});
