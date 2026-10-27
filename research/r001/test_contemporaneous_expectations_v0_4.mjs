/** Run with: node --test research/r001/test_contemporaneous_expectations_v0_4.mjs */
import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {validatePreReleaseEvidence} from "./validate_contemporaneous_expectations_v0_4.mjs";
const data=JSON.parse(readFileSync(new URL("../../site/data/r001_event_comparison_v0_4.json",import.meta.url),"utf8"));
const copy=()=>JSON.parse(JSON.stringify(data));
test("v0.4 archived-news evidence passes QA without normalizing a score",()=>{
 assert.deepEqual(validatePreReleaseEvidence(data),[]);
 assert.equal(data.field_definitions.length,122);
 assert.deepEqual(data.events.map(e=>e.sales_surprise_pct),[0,3.64025696]);
 assert.deepEqual(data.events.map(e=>e.eps_surprise_pct),[null,null]);
 assert.deepEqual(data.events.map(e=>e.normalization_status),["UNCALIBRATED_NO_FROZEN_COHORT","UNCALIBRATED_NO_FROZEN_COHORT"]);
});
test("pre-report quote is genuinely dated before earnings",()=>{
 const d=copy(),q=d.expectation_quote_observations.find(q=>q.selected_for_event&&q.fiscal_quarter==="FY2005-Q4");
 q.publication_date="2006-01-07";
 assert.ok(validatePreReleaseEvidence(d).length>0);
});
test("cannot retrospectively pick an after-earnings quote",()=>{
 const d=copy();
 d.expectation_quote_observations.find(q=>q.quote_id.endsWith("MDN-POST")&&q.fiscal_quarter==="FY2006-Q4").selected_for_event=true;
 assert.ok(validatePreReleaseEvidence(d).length>0);
});
test("consensus estimated by public article is not an authentic vendor UTC timestamp",()=>{
 const d=copy();d.events[1].consensus_snapshot_utc="2006-10-13T12:49:00Z";
 assert.ok(validatePreReleaseEvidence(d).some(x=>x.includes("vendor UTC")));
});
test("sales surprise recalculated from dated forecast and Apple original revenue",()=>{
 const d=copy();d.events[1].sales_surprise_pct=24;
 assert.ok(validatePreReleaseEvidence(d).some(x=>x.includes("sales surprise")));
});
test("mismatched GAAP / tax-adjusted EPS cannot get a modeled surprise",()=>{
 const d=copy();d.events[0].eps_surprise_pct=5.5555;
 assert.ok(validatePreReleaseEvidence(d).some(x=>x.includes("EPS surprise")));
});
test("no invented normalized Price-In feature even when a raw sales surprise exists",()=>{
 const d=copy();d.events[1].norm_sales_surprise=0;
 assert.ok(validatePreReleaseEvidence(d).some(x=>x.includes("invented score")));
});
test("private owner CSV daily-close reaction arithmetic and as-of end must match",()=>{
 const d=copy();d.events[1].prior_earnings_next_session_raw_close_return_pct=8;
 assert.ok(validatePreReleaseEvidence(d).some(x=>x.includes("reaction arithmetic")));
 const later=copy();later.events[0].prior_earnings_next_session_date="2007-10-19";
 assert.ok(validatePreReleaseEvidence(later).some(x=>x.includes("post-event")));
});
