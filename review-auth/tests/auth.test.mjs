import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import worker from "../src/index.js";

if (!globalThis.crypto) globalThis.crypto = webcrypto;
const env = {
  GITHUB_CLIENT_ID:"Iv1.test123",
  GITHUB_CLIENT_SECRET:"test-only-not-real",
  SESSION_KEY: Buffer.alloc(32, 7).toString("base64url")
};
const host="https://qullamaggie-review-auth.test";
const site="https://fdlryaignogn.github.io";
const n="a".repeat(64);
async function call(path, options={}, scope=env){
  return worker.fetch(new Request(host+path,options),scope);
}
async function stateUrl(){
  const start=await call("/auth/start?state="+n);
  assert.equal(start.status,302);
  const oauth=new URL(start.headers.get("location"));
  assert.equal(oauth.hostname,"github.com");
  assert.equal(oauth.searchParams.get("client_id"),env.GITHUB_CLIENT_ID);
  assert.equal(oauth.searchParams.get("redirect_uri"),host+"/auth/callback");
  return oauth.searchParams.get("state");
}
function mockGitHub({permission=true,dispatch=204}={}){
  const old=globalThis.fetch;
  const calls=[];
  globalThis.fetch=async (u,options={})=>{
    const url=new URL(String(u));calls.push({url:url.href,method:options.method||"GET",body:options.body});
    if(url.pathname==="/login/oauth/access_token")
      return Response.json({access_token:"ghu_test-github-token-secret",expires_in:28800});
    if(url.pathname==="/user")return Response.json({login:"fdlryaignogn",id:145678});
    if(url.pathname==="/repos/fdlryaignogn/Qullamaggie-Breakout-Cloud/collaborators/fdlryaignogn/permission")
      return Response.json({permission:permission?"admin":"read"});
    if(url.pathname.endsWith("/dispatches"))return new Response(null,{status:dispatch});
    return new Response(null,{status:404});
  };
  return {restore:()=>{globalThis.fetch=old;},calls};
}
async function loginAndGetSealed(){
 const state=await stateUrl();
 const callback=await call("/auth/callback?code=xyz123456789&state="+encodeURIComponent(state));
 assert.equal(callback.status,302);
 const destination=new URL(callback.headers.get("Location"));
 assert.equal(destination.origin,site);
 const frag=new URLSearchParams(destination.hash.slice(1));
 return {frag,token:frag.get("ql_auth_token")||"",destination:destination.href};
}
test("health is public but unconfigured login cannot start", async()=>{
 const health=await call("/health",{},{});assert.deepEqual(await health.json(),{status:"ok",configured:false});
 const res=await call("/auth/start?state="+n,{},{});assert.equal(res.status,503);
});
test("signed OAuth state required (including expiry/nonce)",async()=>{
 const state=await stateUrl();
 let callback=await call("/auth/callback?code=xyz123456789&state="+encodeURIComponent(state.slice(0,-2)+"xx"));
 assert.equal(new URL(callback.headers.get("Location")).hash,"#ql_auth_error=INVALID_OAUTH_STATE");
 callback=await call("/auth/start?state=too-short");
 assert.equal(callback.status,400);
});
test("cross-origin callers cannot access reviewer API",async()=>{
 let res=await call("/auth/me",{headers:{Origin:"https://untrusted.example"}});
 assert.equal(res.status,403);
 res=await call("/auth/me",{method:"OPTIONS",headers:{Origin:site}});
 assert.equal(res.status,204);
 assert.equal(res.headers.get("Access-Control-Allow-Origin"),site);
});
test("GitHub App login issues a sealed 6-hour session; dispatch enforces write permission and READY confirmation",async()=>{
 const mock=mockGitHub();
 try{
  const {frag,token,destination}=await loginAndGetSealed();
  assert.ok(token.length>50);
  assert.equal(frag.get("ql_auth_state"),n);
  assert.ok(!destination.includes("ghu_test-github-token-secret"));
  const expires=Number(frag.get("ql_auth_expires"));
  assert.ok(expires>Date.now()/1000&&expires<Date.now()/1000+6*3600+2);
  const headers={Origin:site,Authorization:"Bearer "+token};
  const me=await call("/auth/me",{headers});
  assert.equal(me.status,200);assert.equal((await me.json()).login,"fdlryaignogn");
  const review={symbol:"TEST",setup_id:"TEST-20261023",decision:"READY",
    review_reason:"Manually checked base chart",confirmed_chart_review:true};
  const invalid=await call("/reviews/dispatch",{method:"POST",headers:{...headers,"Content-Type":"application/json"},body:JSON.stringify({...review,confirmed_chart_review:false})});
  assert.equal(invalid.status,400);
  const queued=await call("/reviews/dispatch",{method:"POST",headers:{...headers,"Content-Type":"application/json"},body:JSON.stringify(review)});
  assert.equal(queued.status,202);
  assert.deepEqual((await queued.json()),{accepted:true,actor:"fdlryaignogn",status:"queued"});
  const dispatch=mock.calls.find(x=>x.url.endsWith("/dispatches"));
  assert.ok(dispatch);
  const body=JSON.parse(dispatch.body);
  assert.equal(body.ref,"main");
  assert.equal(body.inputs.confirmed_chart_review,"true");
  assert.equal(body.inputs.review_reason,review.review_reason);
  assert.ok(!JSON.stringify(body).includes("ghu_test-github-token-secret"));
  const tampered=token.slice(0,-4)+"XXXX";
  const refused=await call("/auth/me",{headers:{Origin:site,Authorization:"Bearer "+tampered}});
  assert.equal(refused.status,401);
 }finally{mock.restore();}
});
test("GitHub account without write permission is forbidden",async()=>{
 const mock=mockGitHub({permission:false});
 try{
  const {destination}=await loginAndGetSealed();
  assert.ok(destination.includes("ql_auth_error=NO_REPO_WRITE_ACCESS"));
  assert.ok(!destination.includes("ql_auth_token"));
 }finally{mock.restore();}
});
test("GitHub workflow failures are not reported as success",async()=>{
 const mock=mockGitHub({dispatch:403});
 try{
  const {token}=await loginAndGetSealed();
  const res=await call("/reviews/dispatch",{method:"POST",headers:{
    Origin:site,Authorization:"Bearer "+token,"Content-Type":"application/json"
  },body:JSON.stringify({symbol:"TEST",setup_id:"TEST-20261023",decision:"FORMING",review_reason:"Monitor"})});
  assert.equal(res.status,403);
 }finally{mock.restore();}
});
