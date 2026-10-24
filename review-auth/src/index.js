/**
 * Qullamaggie reviewer OAuth gateway for a GitHub App (Cloudflare Worker).
 * Secret bindings: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, SESSION_KEY.
 * Never expose a GitHub access token to GitHub Pages or commit any secret.
 */
const SITE = "https://fdlryaignogn.github.io";
const HOME = SITE + "/Qullamaggie-Breakout-Cloud/";
const REPO = "fdlryaignogn/Qullamaggie-Breakout-Cloud";
const WORKFLOW = "review-stage2.yml";
const MAX_SESSION_SECONDS = 6 * 60 * 60;
const encoder = new TextEncoder();
const decoder = new TextDecoder();
function base64url(bytes) {
  let binary = "";
  for (const n of bytes) binary += String.fromCharCode(n);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}
function unbase64url(value) {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) throw Error("Invalid encoded data");
  const binary = atob(value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - value.length % 4) % 4));
  return Uint8Array.from(binary, c => c.charCodeAt(0));
}
function json(body, status = 200, cors = true) {
  return new Response(JSON.stringify(body), { status, headers: {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    ...(cors ? { "Access-Control-Allow-Origin": SITE, Vary: "Origin" } : {})
  } });
}
function redirect(location) {
  return new Response(null, { status: 302, headers: {
    Location: location, "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff"
  } });
}
function errorRedirect(code) {
  return redirect(HOME + "#ql_auth_error=" + encodeURIComponent(code));
}
function httpError(status, code) { const e = new Error(code); e.status = status; return e; }
function configValid(env) {
  return !!(env.GITHUB_CLIENT_ID && env.GITHUB_CLIENT_SECRET && env.SESSION_KEY);
}
async function hmac(env, data) {
  const key = await crypto.subtle.importKey("raw", unbase64url(env.SESSION_KEY), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return base64url(new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(data))));
}
async function seal(env, payload) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await crypto.subtle.importKey("raw", unbase64url(env.SESSION_KEY), "AES-GCM", false, ["encrypt"]);
  const cipher = await crypto.subtle.encrypt({name:"AES-GCM",iv}, key, encoder.encode(JSON.stringify(payload)));
  return base64url(iv) + "." + base64url(new Uint8Array(cipher));
}
async function openSeal(env, sealed) {
  if (!sealed || sealed.length > 5500) throw httpError(401, "SESSION_INVALID");
  const parts = sealed.split(".");
  if (parts.length !== 2) throw httpError(401, "SESSION_INVALID");
  try {
    const key = await crypto.subtle.importKey("raw", unbase64url(env.SESSION_KEY), "AES-GCM", false, ["decrypt"]);
    const plain = await crypto.subtle.decrypt({name:"AES-GCM",iv:unbase64url(parts[0])}, key, unbase64url(parts[1]));
    const payload = JSON.parse(decoder.decode(plain));
    if (payload.v !== 1 || !payload.t || !payload.login || !payload.id ||
        !Number.isFinite(payload.exp) || payload.exp <= Math.floor(Date.now()/1000)) {
      throw Error("expired");
    }
    return payload;
  } catch (_) { throw httpError(401, "SESSION_EXPIRED_OR_INVALID"); }
}
async function githubApi(path, token, options = {}) {
  const res = await fetch("https://api.github.com" + path, {
    ...options, headers: {
      Accept: "application/vnd.github+json",
      Authorization: "Bearer " + token,
      "X-GitHub-Api-Version": "2022-11-28",
      ...(options.headers || {})
    }, redirect: "manual", cf: {cacheTtl:0}
  });
  return res;
}
async function checkReviewer(session) {
  // Re-check identity AND write access on every request, not only at login.
  const who = await githubApi("/user", session.t);
  if (!who.ok) throw httpError(401, "GITHUB_SESSION_INVALID");
  const actor = await who.json();
  if (String(actor.id) !== String(session.id) || actor.login.toLowerCase() !== session.login.toLowerCase())
    throw httpError(403, "IDENTITY_MISMATCH");
  // The collaborator-permission endpoint exposes the *person's* real role,
  // independent of the App's limited OAuth token capability. Metadata:read.
  const permissionsRes = await githubApi("/repos/" + REPO +
    "/collaborators/" + encodeURIComponent(actor.login) + "/permission", session.t);
  if (!permissionsRes.ok) throw httpError(403, "REPOSITORY_NOT_AUTHORIZED");
  const permissions = await permissionsRes.json();
  if (!["write","admin"].includes(String(permissions.permission || "").toLowerCase()))
    throw httpError(403, "REVIEWER_WRITE_PERMISSION_REQUIRED");
  return actor.login;
}
async function beginLogin(request, env) {
  const nonce = new URL(request.url).searchParams.get("state") || "";
  if (!/^[a-f0-9]{64}$/.test(nonce)) throw httpError(400, "INVALID_LOGIN_NONCE");
  const expires = Math.floor(Date.now() / 1000) + 600;
  const data = nonce + "." + expires;
  const state = data + "." + await hmac(env, data);
  const authorize = new URL("https://github.com/login/oauth/authorize");
  authorize.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  authorize.searchParams.set("redirect_uri", new URL("/auth/callback", request.url).href);
  authorize.searchParams.set("state", state);
  return redirect(authorize.href);
}
async function callback(request, env) {
  const params = new URL(request.url).searchParams;
  if (params.get("error")) return errorRedirect("GITHUB_DENIED");
  const raw = params.get("state") || "";
  const parts = raw.split(".");
  if (parts.length !== 3 || !/^[a-f0-9]{64}$/.test(parts[0]) || !/^\d{10}$/.test(parts[1]))
    return errorRedirect("INVALID_OAUTH_STATE");
  const data = parts[0] + "." + parts[1];
  const expected = await hmac(env, data);
  // Constant-time signature comparison avoids leaking valid signed states.
  const a = encoder.encode(parts[2]), b = encoder.encode(expected);
  if (a.length !== b.length) return errorRedirect("INVALID_OAUTH_STATE");
  let mismatch=0;for(let i=0;i<a.length;i++) mismatch |= a[i]^b[i];
  if (mismatch || Number(parts[1]) < Date.now()/1000) return errorRedirect("INVALID_OAUTH_STATE");
  const code = params.get("code") || "";
  if (!/^[a-zA-Z0-9_-]{10,200}$/.test(code)) return errorRedirect("INVALID_OAUTH_CODE");
  const exchange = await fetch("https://github.com/login/oauth/access_token", {
    method:"POST", headers:{ Accept:"application/json", "Content-Type":"application/x-www-form-urlencoded" },
    body:new URLSearchParams({
      client_id:env.GITHUB_CLIENT_ID, client_secret:env.GITHUB_CLIENT_SECRET,
      code, redirect_uri:new URL("/auth/callback",request.url).href
    }).toString(), redirect:"manual"
  });
  if (!exchange.ok) return errorRedirect("GITHUB_TOKEN_EXCHANGE_FAILED");
  const tokenData = await exchange.json();
  if (!tokenData.access_token || tokenData.error) return errorRedirect("GITHUB_TOKEN_EXCHANGE_FAILED");
  const now = Math.floor(Date.now()/1000);
  // A short encrypted *gateway session* is returned; never return GitHub token.
  const expires = now + Math.min(MAX_SESSION_SECONDS, Math.max(1,(Number(tokenData.expires_in)||MAX_SESSION_SECONDS)-120));
  let login;
  try {
    const who = await githubApi("/user", tokenData.access_token);
    if(!who.ok) return errorRedirect("GITHUB_IDENTITY_FAILED");
    const account=await who.json();
    const session={v:1,login:account.login,id:account.id,t:tokenData.access_token,exp:expires};
    login=await checkReviewer(session);
    const sealed=await seal(env,session);
    // A fragment is not sent to GitHub Pages servers, logs or HTTP Referer.
    const hash=new URLSearchParams({ql_auth_token:sealed,ql_auth_state:parts[0],ql_auth_expires:String(expires)});
    return redirect(HOME+"#"+hash.toString());
  } catch(e) { return errorRedirect(e.status===403?"NO_REPO_WRITE_ACCESS":"LOGIN_VERIFICATION_FAILED"); }
}
async function authenticate(request, env) {
  const header = request.headers.get("Authorization") || "";
  if (!/^Bearer [A-Za-z0-9_.-]+$/.test(header)) throw httpError(401,"AUTH_REQUIRED");
  return openSeal(env,header.substring(7));
}
async function dispatchReview(request, env) {
  const session=await authenticate(request,env);
  const actor=await checkReviewer(session);
  if ((request.headers.get("Content-Type")||"").split(";")[0].trim()!=="application/json")
    throw httpError(415,"JSON_REQUIRED");
  const size=Number(request.headers.get("Content-Length") || 0);
  if (size>4096) throw httpError(413,"REQUEST_TOO_LARGE");
  const raw=await request.text();
  if (raw.length>4096) throw httpError(413,"REQUEST_TOO_LARGE");
  let data;try{data=JSON.parse(raw);}catch(_){throw httpError(400,"INVALID_JSON");}
  const symbol=String(data.symbol||"").trim().toUpperCase();
  const setup=String(data.setup_id||"").trim();
  const decision=String(data.decision||"");
  const reason=String(data.review_reason||"").trim();
  const confirmed=data.confirmed_chart_review===true;
  if (!/^[A-Z0-9.\-]{1,16}$/.test(symbol) ||
      !/^[A-Z0-9.\-]{1,16}-[0-9]{8}$/.test(setup) ||
      !setup.startsWith(symbol+"-") ||
      !["READY","FORMING","INVALIDATED"].includes(decision) ||
      reason.length<1 || reason.length>500 || /[\u0000-\u001f\u007f]/.test(reason) ||
      (decision==="READY" && !confirmed))
    throw httpError(400,"INVALID_REVIEW_INPUT");
  const result=await githubApi("/repos/"+REPO+"/actions/workflows/"+WORKFLOW+"/dispatches",
    session.t, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      ref:"main",inputs:{
        symbol,setup_id:setup,decision,
        confirmed_chart_review:String(confirmed),review_reason:reason
      }
    })});
  if (result.status!==204) {
    if ([401,403,404].includes(result.status)) throw httpError(403,"GITHUB_ACTIONS_ACCESS_DENIED");
    throw httpError(502,"WORKFLOW_DISPATCH_FAILED");
  }
  return json({accepted:true,actor,status:"queued"},202);
}
export default {
  async fetch(request,env) {
    try {
      const url=new URL(request.url),path=url.pathname;
      if(path==="/health" && request.method==="GET")
        return json({status:"ok",configured:configValid(env)},200,false);
      if(!configValid(env)) return json({error:"AUTH_BACKEND_NOT_CONFIGURED"},503,false);
      if(path==="/auth/start" && request.method==="GET") return beginLogin(request,env);
      if(path==="/auth/callback" && request.method==="GET") return callback(request,env);
      // Cross-origin API calls must originate from the one approved Pages site.
      if (!["/auth/me","/reviews/dispatch"].includes(path))
        return json({error:"NOT_FOUND"},404,false);
      if(request.headers.get("Origin")!==SITE)
        return json({error:"ORIGIN_NOT_ALLOWED"},403,false);
      if(request.method==="OPTIONS")
        return new Response(null,{status:204,headers:{
          "Access-Control-Allow-Origin":SITE, "Access-Control-Allow-Methods":"GET, POST, OPTIONS",
          "Access-Control-Allow-Headers":"Authorization, Content-Type", "Access-Control-Max-Age":"600",
          "Cache-Control":"no-store",Vary:"Origin"
        }});
      if(path==="/auth/me" && request.method==="GET") {
        const session=await authenticate(request,env);
        const login=await checkReviewer(session);
        return json({login,expires:session.exp,can_review:true});
      }
      if(path==="/reviews/dispatch" && request.method==="POST") return dispatchReview(request,env);
      return json({error:"METHOD_NOT_ALLOWED"},405);
    } catch(e) {
      const status=[400,401,403,405,413,415,502].includes(e.status)?e.status:500;
      // Never log or expose raw access tokens, secrets, or upstream response bodies.
      return json({error:status===500?"BACKEND_ERROR":e.message},status);
    }
  }
};
