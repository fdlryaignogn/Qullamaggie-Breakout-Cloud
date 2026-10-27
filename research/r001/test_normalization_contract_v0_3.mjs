/** Run: node --test research/r001/test_normalization_contract_v0_3.mjs */
import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {normalizeSigned,calculatePriorSurprise,normalizeEventInput,validatePriceInSchema} from "./normalization_contract_v0_3.mjs";

const document=JSON.parse(readFileSync(new URL("../../site/data/r001_event_comparison_v0_3.json",import.meta.url),"utf8"));
const goodReference=Object.freeze({
  median:10,mad:2,sample_count:180,distinct_symbols:40,calendar_quarters:12,
  dataset_role:"TRAIN",locked:true,direction:1,train_end_date:"2004-12-31",
  reference_vintage_date:"2004-12-31",direction_locked_date:"2004-12-30",
  polarity_evidence_id:"MOCK_TRAIN_POLARITY_2004"
});
const clone=o=>JSON.parse(JSON.stringify(o));
test("schema v0.3 remains complete, untrained and null",()=>{
  assert.deepEqual(validatePriceInSchema(document),[]);
  assert.equal(document.field_definitions.length,111);
  assert.equal(document.events.length,2);
  assert.equal(document.events.every(e=>e.norm_revenue_yoy===null&&e.consensus_revenue_usd_m===null),true);
});
test("normalized values bounded with documented polarity",()=>{
 const pos=normalizeSigned(16,goodReference,"2006-01-06");
 const neg=normalizeSigned(16,{...goodReference,direction:-1},"2006-01-06");
 assert.ok(pos>0&&pos<1);assert.ok(Math.abs(pos+neg)<1e-12);
 assert.equal(normalizeSigned(1e200,goodReference,"2006-01-06"),1);
});
test("never replace missing values or missing calibration with zero",()=>{
 assert.equal(normalizeSigned(null,goodReference,"2006-01-06"),null);
 assert.equal(normalizeSigned(16,null,"2006-01-06"),null);
 assert.equal(normalizeSigned(16,{...goodReference,mad:0},"2006-01-06"),null);
});
test("future reference and unlocked direction cannot be used",()=>{
 assert.equal(normalizeSigned(16,{...goodReference,train_end_date:"2006-12-31"},"2006-01-06"),null);
 assert.equal(normalizeSigned(16,{...goodReference,reference_vintage_date:"2006-01-06"},"2006-01-06"),null);
 assert.equal(normalizeSigned(16,{...goodReference,locked:false},"2006-01-06"),null);
 assert.equal(normalizeSigned(16,{...goodReference,sample_count:2},"2006-01-06"),null);
});
test("outcome, derived raw values and mismatched calibration cannot be used as predictors",()=>{
 assert.equal(normalizeEventInput(document.events[0],document.field_definitions,"winner_252",goodReference),null);
 assert.equal(normalizeEventInput(document.events[0],document.field_definitions,"norm_revenue_yoy",goodReference),null);
 const ref={...goodReference,source_field:"revenue_yoy_asof_pct",calibration_id:"MOCK_FROZEN_REFERENCE_2004"};
 assert.ok(Number.isFinite(normalizeEventInput(document.events[0],document.field_definitions,"revenue_yoy_asof_pct",ref)));
 assert.equal(normalizeEventInput(document.events[0],document.field_definitions,"revenue_yoy_asof_pct",{...ref,source_field:"event_close_usd"}),null);
 assert.equal(normalizeEventInput(document.events[0],document.field_definitions,"revenue_yoy_asof_pct",{...ref,calibration_id:""}),null);
});
test("hypothetical announcement surprise, with pre-event release, is calculable",()=>{
 const example={actual:3680,consensus:3500,consensusSnapshotDate:"2005-10-10",reportReleaseDate:"2005-10-11",eventDate:"2006-01-06",kind:"sales",comparableBasis:true};
 assert.ok(Math.abs(calculatePriorSurprise(example)-100*(3680/3500-1))<1e-12);
 assert.equal(calculatePriorSurprise({...example,reportReleaseDate:"2006-01-18"}),null);
 assert.equal(calculatePriorSurprise({...example,consensusSnapshotDate:"2005-10-12"}),null);
 assert.equal(calculatePriorSurprise({...example,reportReleaseDate:"2006-01-06"}),null);
 assert.equal(calculatePriorSurprise({...example,comparableBasis:false}),null);
});
test("tampering with future-label role or filling false historical score must fail",()=>{
 const role=clone(document);role.field_definitions.find(f=>f.key==="winner_252").io_role="INPUT";
 assert.ok(validatePriceInSchema(role).some(s=>s.includes("role")));
 const score=clone(document);score.events[0].norm_eps_yoy=.55;
 assert.ok(validatePriceInSchema(score).some(s=>s.includes("invented a score")));
});
