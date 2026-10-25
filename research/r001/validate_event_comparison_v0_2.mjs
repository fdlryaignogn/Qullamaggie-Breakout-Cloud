/**
 * Validate the public metadata-only R-001 schema, event matrix, and as-of fundamental series.
 * Intended for Node, browsers and CI. No market prices or API credentials downloaded here.
 * ESM usage: import {validateEventComparison} from './validate_event_comparison_v0_2.mjs'
 */
export function validateEventComparison(d) {
  const issues=[];
  const check=(condition,reason)=>{if(!condition)issues.push(reason)};
  check(d&&d.schema_version==="0.2.0","schema_version must be 0.2.0");
  if(!d||!Array.isArray(d.field_definitions)||!Array.isArray(d.events)||!Array.isArray(d.financial_quarters_pit))return ["Bad document shape"];
  const defs=d.field_definitions,events=d.events,quarters=d.financial_quarters_pit;
  check(new Set(defs.map(f=>f.key)).size===defs.length,"duplicate field keys");
  check(defs.every(f=>["INPUT","OUTPUT","META"].includes(f.io_role)),"invalid IO role");
  check(defs.every(f=>f.role==="label"?f.io_role==="OUTPUT":f.role==="input"?f.io_role==="INPUT":f.io_role==="META"),"IO role does not match semantic role");
  check(events.length===2&&events[0].event_date==="2006-01-06"&&events[1].event_date==="2007-01-10","two known AAPL research events expected");
  check(d.price_series_included===false,"raw historical OHLCV must not be redistributed");
  const qmap=new Map(quarters.map(q=>[q.q,q]));
  check(qmap.size===quarters.length,"duplicate fiscal quarter");
  const rank=(a,b)=>a>b;
  const approx=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<1e-4;
  for(const event of events) {
    for(const f of defs)check(Object.prototype.hasOwnProperty.call(event,f.key),"missing "+f.key+" in "+event.event_id);
    const latest=qmap.get(event.latest_fiscal_quarter);
    check(Boolean(latest),"missing latest fiscal quarter "+event.latest_fiscal_quarter);
    if(!latest)continue;
    const known=quarters.filter(q=>q.release_date<event.event_date).sort((a,b)=>b.release_date.localeCompare(a.release_date)).slice(0,4);
    check(known.length===4,"insufficient as-of quarter history: "+event.event_id);
    check(known[0].q===latest.q,"latest release mismatch: "+event.event_id);
    check(event.earnings_release_date===latest.release_date,"earnings_release_date mismatch");
    check(event.financial_quarter_end===latest.period_end,"financial_quarter_end mismatch");
    check(event.revenue_release_date===latest.release_date,"legacy release_date mismatch");
    check(approx(event.revenue_yoy_asof_pct,latest.reported_revenue_yoy_pct),"q0 revenue YoY mismatch");
    check(approx(event.diluted_eps_yoy_q0_pct,latest.eps_yoy_pct),"q0 EPS YoY mismatch");
    if(known.length===4){
      check(approx(event.revenue_yoy_accel_q0_pp,known[0].reported_revenue_yoy_pct-known[1].reported_revenue_yoy_pct),"sales acceleration mismatch");
      check(approx(event.diluted_eps_yoy_accel_q0_pp,known[0].eps_yoy_pct-known[1].eps_yoy_pct),"EPS acceleration mismatch");
      check(event.revenue_absolute_up_last3_bool===(rank(known[0].revenue_usd_m,known[1].revenue_usd_m)&&rank(known[1].revenue_usd_m,known[2].revenue_usd_m)),"sales absolute streak wrong");
      check(event.diluted_eps_absolute_up_last3_bool===(rank(known[0].eps_usd_as_reported,known[1].eps_usd_as_reported)&&rank(known[1].eps_usd_as_reported,known[2].eps_usd_as_reported)),"EPS absolute streak wrong");
      check(event.revenue_yoy_accel_last3_bool===(rank(known[0].reported_revenue_yoy_pct,known[1].reported_revenue_yoy_pct)&&rank(known[1].reported_revenue_yoy_pct,known[2].reported_revenue_yoy_pct)),"sales 3-quarter acceleration wrong");
      check(event.diluted_eps_yoy_accel_last3_bool===(rank(known[0].eps_yoy_pct,known[1].eps_yoy_pct)&&rank(known[1].eps_yoy_pct,known[2].eps_yoy_pct)),"EPS 3-quarter acceleration wrong");
    }
    check(["roic_ttm_pct","roe_ttm_pct","roa_ttm_pct"].every(k=>event[k]===null),"historical ROI measures unverified, must stay null");
    check(event.ml_training_ready===false&&event.case_quality==="PROVISIONAL","research events cannot be marked model-ready");
  }
  const first=events[0],later=events[1];
  check(first.research_role==="SELECTED_FIRST_IN_WINDOW"&&first.winner_252===false,"original selected event must not be replaced");
  check(later.research_role==="NON_SELECTED_SENSITIVITY"&&later.winner_252===true,"later winner is not selected event");
  const q2006=qmap.get("FY2006-Q1");
  if(q2006)check(q2006.release_date>first.event_date,"January 2006 earnings must postdate first event");
  check(quarters.every(q=>typeof q.source_url==="string"&&q.source_url.startsWith("https://www.apple.com/")&&/^\d{4}-\d{2}-\d{2}$/.test(q.release_date)),"undated/nonofficial quarterly source");
  return issues;
}
