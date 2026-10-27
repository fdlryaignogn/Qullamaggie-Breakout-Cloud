/**
 * R-001 Price In v0.4: validate publicly dated historical *news quotes*, not
 * privately licensed analyst database snapshots. No vendor vintages are invented.
 * No normalized Price-In or matched-basis EPS surprise is calibrated here.
 */
export function validatePreReleaseEvidence(doc) {
 const errs=[];const test=(ok,msg)=>{if(!ok)errs.push(msg)};
 test(doc?.schema_version==="0.4.0","version must equal v0.4.0");
 if(!doc||!Array.isArray(doc.events)||!Array.isArray(doc.field_definitions)||!Array.isArray(doc.expectation_quote_observations))return ["missing top-level schema"];
 const fields=doc.field_definitions,keys=new Set(fields.map(f=>f.key)),quotes=doc.expectation_quote_observations,actuals=doc.expectation_actuals;
 const finite=x=>typeof x==="number"&&Number.isFinite(x);
 const numEqual=(a,b)=>finite(a)&&finite(b)&&Math.abs(a-b)<=1e-5;
 test(fields.length===122&&keys.size===fields.length,"field count or duplicate key");
 test(fields.filter(f=>f.io_role==="INPUT").length===75&&fields.filter(f=>f.io_role==="OUTPUT").length===7&&fields.filter(f=>f.io_role==="META").length===40,"role counts changed");
 test(doc.events.length===2,"two original AAPL cases expected");
 test(doc.price_series_included===false,"do not redistribute historical FMP price series");
 const expectedDates=["2006-01-06","2007-01-10"];
 const seenQuotes=new Set();
 for(const q of quotes){
  test(typeof q.quote_id==="string"&&!seenQuotes.has(q.quote_id),"quote id missing/duplicate");
  seenQuotes.add(q.quote_id);
  const a=actuals?.[q.fiscal_quarter];
  test(Boolean(a),"actual fiscal quarter unavailable "+q.fiscal_quarter);
  if(!a)continue;
  test(q.report_release_date===a.report_release,"release date mismatch "+q.quote_id);
  test(/^\d{4}-\d{2}-\d{2}$/.test(q.publication_date),"missing article publication date "+q.quote_id);
  const pre=q.publication_date<q.report_release_date;
  test(pre===(q.timing==="BEFORE_REPORT"),"pre/post release classification mismatch "+q.quote_id);
  if(q.selected_for_event){
   test(pre,"post-report article must not be selected "+q.quote_id);
   test(q.grade==="CONTEMPORANEOUS_ARTICLE_PRE_RELEASE_VENDOR_UNVERIFIED","selected quote has wrong evidence grade "+q.quote_id);
  }
  test(q.direct_vendor_vintage===false,"unverified vendor vintage must remain false "+q.quote_id);
  test(finite(q.consensus_revenue_usd_m)&&q.consensus_revenue_usd_m>0,"invalid quote revenue");
  test(finite(q.consensus_eps_reported_usd),"invalid literal EPS quote");
  test(typeof q.source_url==="string"&&q.source_url.startsWith("https://"),"missing URL "+q.quote_id);
 }
 for(const [i,e] of doc.events.entries()){
  test(e.event_date===expectedDates[i],"original event date changed");
  test(e.ml_training_ready===false,"cannot approve model training");
  const a=actuals?.[e.latest_fiscal_quarter];
  const q=quotes.filter(q=>q.fiscal_quarter===e.latest_fiscal_quarter&&q.selected_for_event);
  test(q.length===1,"one selected pre-report dated quote per event");
  if(q.length!==1||!a)continue;
  const chosen=q[0];
  test(chosen.publication_date<a.report_release&&a.report_release<e.event_date,"release/lookahead gate failed");
  test(e.consensus_quote_public_date===chosen.publication_date,"quote date mismatch");
  test(e.consensus_quote_source_url===chosen.source_url,"quote URL mismatch");
  test(e.consensus_quote_qa_status===chosen.grade,"quote quality mismatch");
  test(e.consensus_quote_vendor_vintage_confirmed===false,"cannot claim original vendor vintage");
  test(e.consensus_snapshot_utc===null,"cannot invent vendor UTC clock");
  test(e.consensus_quote_time_precision==="PUBLICATION_DATE_ONLY_NO_VENDOR_UTC_SNAPSHOT","date-only disclosure required");
  test(numEqual(e.consensus_revenue_usd_m,chosen.consensus_revenue_usd_m),"consensus revenue mismatch");
  test(numEqual(e.sales_surprise_pct,100*(a.revenue-chosen.consensus_revenue_usd_m)/chosen.consensus_revenue_usd_m),"derived sales surprise mismatch");
  test(e.sales_surprise_evidence_grade==="DERIVED_FROM_SECONDARY_PRE_RELEASE_ARTICLE_AND_DATED_APPLE_RELEASE","provisional numeric evidence label missing");
  test(numEqual(e.reported_consensus_eps_usd_unmatched,chosen.consensus_eps_reported_usd),"quoted EPS mismatch");
  test(e.consensus_eps_matched_usd===null&&e.actual_eps_consensus_basis_usd===null&&e.eps_surprise_pct===null,"unverified EPS surprise must remain NULL");
  test(e.expectation_data_status==="PARTIAL_CONTEMPORANEOUS_PUBLIC_QUOTE_VENDOR_VINTAGE_UNVERIFIED","must preserve quote limitation");
  test(e.normalization_status==="UNCALIBRATED_NO_FROZEN_COHORT"&&e.normalization_calibration_id===null,"calibration cannot exist");
  test(e.priced_in_identification_status==="NOT_DIRECTLY_OBSERVABLE","price in not directly observed");
  for(const field of fields.filter(f=>["normalized","composite"].includes(f.group)))test(e[field.key]===null,"invented score "+field.key);
  for(const field of fields)test(Object.hasOwn(e,field.key),"missing feature "+field.key);
  const reaction=doc.price_reaction_derivation?.event_windows?.[i];
  test(Boolean(reaction),"missing raw reaction audit "+i);
  if(reaction){
   test(e.prior_earnings_next_session_date===reaction.reaction_day,"reaction end date mismatch");
   test(e.prior_earnings_next_session_date<e.event_date,"post-event reaction used as input");
   test(numEqual(e.prior_earnings_next_session_raw_close_return_pct,100*(reaction.next_session_close_split_adjusted/reaction.report_close_split_adjusted-1)),"raw reaction arithmetic mismatch");
   test(e.prior_earnings_abnormal_reaction_pct===null,"benchmark abnormal return must not be invented");
  }
 }
 return errs;
}