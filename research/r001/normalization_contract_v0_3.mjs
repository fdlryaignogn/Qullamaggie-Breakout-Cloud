/**
 * R-001 / normalizer v0.3.0 - price-in feature contract (research only).
 * Missing calibrations never yield 0 or invented scores.
 * Median/MAD must be computed solely from a frozen, historical training cohort.
 */
const MIN_SAMPLES = 100;
const MIN_SYMBOLS = 30;
const MIN_CALENDAR_QUARTERS = 8;
const MAD_SIGMA_FACTOR = 1.4826;

function dateOnly(v) {
 if(typeof v !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return null;
 const ms=Date.parse(v+"T00:00:00Z");
 return Number.isFinite(ms) && new Date(ms).toISOString().slice(0,10)===v ? v : null;
}
const finite = v => typeof v==="number"&&Number.isFinite(v);
const nullOrIssue = v => v===null||v===undefined;

export function normalizeSigned(raw, reference, eventDate) {
 if(nullOrIssue(raw)||nullOrIssue(reference))return null;
 if(!finite(raw)||!dateOnly(eventDate))return null;
 if(!finite(reference.median)||!finite(reference.mad)||reference.mad<=0)return null;
 if(!Number.isInteger(reference.sample_count)||reference.sample_count<MIN_SAMPLES)return null;
 if(!Number.isInteger(reference.distinct_symbols)||reference.distinct_symbols<MIN_SYMBOLS)return null;
 if(!Number.isInteger(reference.calendar_quarters)||reference.calendar_quarters<MIN_CALENDAR_QUARTERS)return null;
 if(reference.dataset_role!=="TRAIN"||reference.locked!==true)return null;
 if(reference.direction!==1&&reference.direction!==-1)return null;
 if(!dateOnly(reference.train_end_date)||!dateOnly(reference.reference_vintage_date)||!dateOnly(reference.direction_locked_date))return null;
 if(reference.train_end_date>=eventDate||reference.reference_vintage_date>=eventDate||reference.direction_locked_date>=eventDate)return null;
 if(typeof reference.polarity_evidence_id!=="string"||!reference.polarity_evidence_id.trim())return null;
 return reference.direction * Math.tanh((raw-reference.median)/(2*MAD_SIGMA_FACTOR*reference.mad));
}

/**
 * Prior-known EPS/sales surprise; does NOT query any data or estimate hidden consensus.
 * EPS needs a frozen currency/period denominator floor and matched accounting basis.
 */
export function calculatePriorSurprise({
 actual, consensus, consensusSnapshotDate, reportReleaseDate,
 eventDate, kind, comparableBasis, epsFloor
}){
 if(!finite(actual)||!finite(consensus)||!dateOnly(consensusSnapshotDate)||!dateOnly(reportReleaseDate)||!dateOnly(eventDate))return null;
 if(!(consensusSnapshotDate<reportReleaseDate&&reportReleaseDate<eventDate))return null;
 if(comparableBasis!==true)return null;
 if(kind==="sales"){
  if(actual<=0||consensus<=0)return null;
  return 100*(actual-consensus)/consensus;
 }
 if(kind==="eps"){
  if(!finite(epsFloor)||epsFloor<=0)return null;
  return 100*(actual-consensus)/Math.max(Math.abs(consensus),epsFloor);
 }
 return null;
}

/**
 * Event outcome labels cannot be normalized into predictor columns.
 * A normalized *raw price momentum* signal is not automatically "bullish" or "priced in":
 * that polarity must be independently justified and frozen in reference.
 */
export function normalizeEventInput(event, schema, key, reference) {
 const field=schema?.find(f=>f.key===key);
 if(!field||field.io_role!=="INPUT"||field.role!=="input")return null;
 if(/^(norm_|fundamental_strength_norm$|expectation_surprise_norm$|priced_in_headwind_norm$)/.test(key))return null;
 // Do not apply another feature's median/MAD reference or an unversioned calibration.
 if(reference?.source_field!==key||typeof reference?.calibration_id!=="string"||!reference.calibration_id.trim())return null;
 return normalizeSigned(event?.[key], reference, event?.event_date);
}

export function validatePriceInSchema(document){
 const errors=[];
 const fail=(ok,message)=>{if(!ok)errors.push(message)};
 fail(document?.schema_version==="0.3.0","v0.3.0 expected");
 if(!document||!Array.isArray(document.field_definitions)||!Array.isArray(document.events))return ["missing event or schema arrays"];
 const defs=document.field_definitions,keys=new Set(defs.map(f=>f.key));
 fail(keys.size===defs.length,"duplicate schema keys");
 fail(defs.every(f=>["INPUT","OUTPUT","META"].includes(f.io_role)),"invalid IO roles");
 fail(defs.every(f=>(f.role==="input"&&f.io_role==="INPUT")||(f.role==="label"&&f.io_role==="OUTPUT")||(!["input","label"].includes(f.role)&&f.io_role==="META")),"IO role conflict");
 const required=["consensus_revenue_usd_m","eps_surprise_pct","norm_revenue_yoy","norm_pre_breakout_excess_return","expectation_data_status","normalization_calibration_id","normalization_status","priced_in_identification_status"];
 for(const key of required)fail(keys.has(key),"required key missing: "+key);
 const blocked=defs.filter(f=>f.io_role==="OUTPUT").map(f=>f.key);
 for(const event of document.events){
  for(const key of keys)fail(Object.hasOwn(event,key),event.event_id+": missing "+key);
  for(const f of defs.filter(x=>x.group==="normalized"||x.group==="composite")){
   const v=event[f.key];
   fail(v===null||(finite(v)&&v>=-1&&v<=1),"invalid normalized score: "+f.key);
   fail(v===null,f.key+" invented a score despite no frozen calibrations");
  }
  for(const key of ["consensus_revenue_usd_m","consensus_eps_matched_usd","eps_surprise_pct","sales_surprise_pct","pre_earnings_abnormal_return_20d_pct","prior_earnings_abnormal_reaction_pct"]){
    fail(event[key]===null,"unverified historical consensus/market series must be null: "+key);
  }
  fail(event.normalization_calibration_id===null,"no historic calibration ID exists");
  fail(event.normalization_status==="UNCALIBRATED_NO_FROZEN_COHORT","invalid normalization status");
  fail(event.expectation_data_status==="MISSING_PIT_ANALYST_CONSENSUS","expectation data status invalid");
  fail(event.ml_training_ready===false,"research case cannot be model ready");
  fail(event.priced_in_identification_status==="NOT_DIRECTLY_OBSERVABLE","must not claim directly observed priced-in ratio");
  fail(event.event_id?.startsWith("R001-AAPL-"),"event identity changed");
 }
 fail(blocked.includes("winner_252"),"future label role changed");
 fail(document.price_series_included===false,"no public FMP price history permitted");
 return errors;
}
