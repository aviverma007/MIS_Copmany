"""
MIS Company - single Python application.

    pip install -r requirements.txt
    python app.py            ->  http://<this-machine>:8000

ONE link, ONE screen for everything:

  1. Login page
  2. Home page - pick one of the three applications
  3. The ORIGINAL M3M / Smartworld / NBH application, unchanged,
     with its data auto-loaded from an Excel folder.

The three original apps run as internal engines on 127.0.0.1 (ports
9101-9103, not reachable from the network). This gateway is the only
front door: it signs users in, shows the home page, and reverse-proxies
the selected application.

EXCEL DATA (replaces the upload feature):
  Drop each company's Excel into its folder -

      data/m3m/           data/smartworld/        data/nbh/

  The newest .xlsx in each folder is auto-loaded into that company's
  engine at startup and again whenever the file changes. Replace the
  Excel, wait a few seconds, refresh the browser. No restart needed.
  The in-app Upload buttons/screens are hidden by the gateway; the
  application code itself is completely untouched.

Account (change in ACCOUNTS below):
      admin / admin
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse


def page(html: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(html, status_code=status, headers={"Cache-Control": "no-store"})

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PORT = int(os.environ.get("PORT", 8000))
PY = sys.executable

# ------------------------------------------------------------ configuration

ACCOUNTS = {
    "admin": {"password": "admin"},
}

APPS = {
    "m3m": {
        "name": "M3M MIS",
        "title": "M3M Customer Complaint MIS",
        "desc": "Customer complaint dashboard for M3M SFDC exports.",
        "accent": "#C9A648",
        "port": 9101,
        "data_dir": "m3m",
        "cwd": ROOT / "apps" / "m3m-mis" / "backend",
        "cmd": [PY, "-c",
                "import sys, uvicorn; sys.path.insert(0, '.'); import api_app; "
                "api_app.mount_frontend('../frontend'); "
                "uvicorn.run(api_app.app, host='127.0.0.1', port=9101, log_level='warning')"],
    },
    "smartworld": {
        "name": "Smartworld MIS",
        "title": "Smartworld Customer Complaint MIS",
        "desc": "Same engine on the Compile SW Data schema.",
        "accent": "#2BAE8E",
        "port": 9102,
        "data_dir": "smartworld",
        "cwd": ROOT / "apps" / "sw-mis" / "backend",
        "cmd": [PY, "-c",
                "import sys, uvicorn; sys.path.insert(0, '.'); import api_app; "
                "api_app.mount_frontend('../frontend'); "
                "uvicorn.run(api_app.app, host='127.0.0.1', port=9102, log_level='warning')"],
    },
    "nbh": {
        "name": "NBH MIS",
        "title": "NBH Complaint Management Dashboard",
        "desc": "NoBrokerHood facility-management complaint data.",
        "accent": "#E4572E",
        "port": 9103,
        "data_dir": "nbh",
        "cwd": ROOT / "apps" / "nbh-mis" / "backend",
        "cmd": [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                "--port", "9103", "--log-level", "warning"],
        "root_redirect": "/dashboard",   # NBH's "/" route is its upload page
    },
}

SESSION_TTL = 12 * 3600                                   # absolute cap
INACTIVITY_TTL = int(float(os.environ.get("INACTIVITY_MINUTES", "30")) * 60)
COOKIE = "mis_session"

# ------------------------------------------------------------------ session

_secret_file = ROOT / ".session_secret"
if _secret_file.exists():
    SECRET = _secret_file.read_bytes()
else:
    SECRET = secrets.token_bytes(32)
    _secret_file.write_bytes(SECRET)


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_session(username: str, app_id: str | None, t0: int | None = None) -> str:
    now = int(time.time())
    payload = _b64e(json.dumps(
        {"u": username, "a": app_id, "t": now, "t0": t0 or now}).encode())
    sig = _b64e(hmac.new(SECRET, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_session(token: str | None):
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    good = _b64e(hmac.new(SECRET, payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, good):
        return None
    try:
        data = json.loads(_b64d(payload))
    except Exception:
        return None
    now = int(time.time())
    t = int(data.get("t", 0))
    t0 = int(data.get("t0", t))
    if now - t > INACTIVITY_TTL:      # 30 min without any request
        return None
    if now - t0 > SESSION_TTL:        # absolute 12 h cap since login
        return None
    if data.get("a") is not None and data["a"] not in APPS:
        return None
    return data


def set_session_cookie(resp: Response, username: str, app_id: str | None,
                       t0: int | None = None):
    # No max_age/expires: a browser-session cookie. Closing the browser
    # discards it, so reopening the page requires signing in again.
    # Each request re-issues the cookie with a fresh activity timestamp
    # (sliding 30-minute inactivity window); t0 preserves the login time
    # for the absolute 12-hour cap.
    resp.set_cookie(COOKIE, make_session(username, app_id, t0),
                    httponly=True, samesite="lax", path="/")


# ---------------------------------------------------------- HTML: login/home

_BASE_CSS = """
:root{--navy-900:#0F1F3D;--navy-700:#1F3864;--teal-500:#0F9B8E;--teal-600:#0C7F74;
--teal-100:#E3F5F3;--red-600:#C62828;--border:#E3E8F0;--text-900:#131A2A;
--text-600:#4A5568;--text-400:#8892A3;
--font:-apple-system,BlinkMacSystemFont,"Segoe UI","Inter",Roboto,Helvetica,Arial,sans-serif}
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{font-family:var(--font);font-size:14px;color:var(--text-900);background:#F1F4F9}
"""

LOGIN_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>MIS Company — Sign in</title>
<style>{_BASE_CSS}
.page{{min-height:100%;display:grid;grid-template-columns:1fr 1fr}}
.hero{{background:linear-gradient(150deg,var(--navy-900),var(--navy-700));color:#fff;
padding:56px;display:flex;flex-direction:column;justify-content:space-between}}
.wordmark{{font-weight:800;font-size:16px}}.wordmark span{{font-weight:400;opacity:.65}}
.hero h1{{font-size:32px;line-height:1.2;margin:0 0 10px;max-width:16ch}}
.lede{{opacity:.75;max-width:44ch;margin:0 0 32px;line-height:1.55}}
.list{{border-top:1px solid rgba(255,255,255,.18)}}
.row{{display:grid;grid-template-columns:4px 150px 1fr;gap:18px;padding:15px 0;
border-bottom:1px solid rgba(255,255,255,.18);align-items:baseline}}
.rail{{align-self:stretch;border-radius:2px}}.cname{{font-weight:700;white-space:nowrap}}
.cdesc{{opacity:.7;font-size:13px}}.foot{{font-size:12px;opacity:.55}}
.side{{display:flex;align-items:center;justify-content:center;padding:40px 28px}}
.card{{width:100%;max-width:360px;background:#fff;border:1px solid var(--border);
border-radius:10px;box-shadow:0 4px 16px rgba(15,31,61,.08);padding:30px}}
.card h2{{margin:0 0 4px;font-size:20px}}.hint{{color:var(--text-600);font-size:13px;margin:0 0 22px}}
.field{{margin-bottom:15px}}
label{{display:block;font-size:12.5px;color:var(--text-600);margin-bottom:5px;font-weight:600}}
input{{width:100%;border:1px solid var(--border);border-radius:6px;padding:10px 12px;font:inherit;outline:none}}
input:focus-visible{{border-color:var(--teal-500);box-shadow:0 0 0 3px var(--teal-100)}}
.err{{color:var(--red-600);font-size:13px;margin:0 0 12px;min-height:16px}}
button{{width:100%;background:var(--teal-500);color:#fff;border:0;border-radius:6px;
padding:11px;font:inherit;font-weight:700;cursor:pointer}}
button:hover{{background:var(--teal-600)}}button:disabled{{opacity:.6;cursor:default}}
.note{{margin-top:20px;padding-top:14px;border-top:1px solid var(--border);font-size:12px;color:var(--text-400)}}
.note code{{color:var(--text-600);font-size:11.5px}}
@media(max-width:860px){{.page{{grid-template-columns:1fr}}.hero{{padding:32px 24px;gap:24px}}}}
</style></head><body>
<div class="page">
  <div class="hero">
    <div class="wordmark">MIS Company <span>/ complaint management suite</span></div>
    <div>
      <h1>One link, three dashboards.</h1>
      <p class="lede">Sign in, then pick your application from the home screen.
      Data loads automatically from each company's Excel folder on the server.</p>
      <div class="list">
        <div class="row"><span class="rail" style="background:#C9A648"></span>
          <span class="cname">M3M MIS</span><span class="cdesc">Customer complaint dashboard for M3M SFDC exports.</span></div>
        <div class="row"><span class="rail" style="background:#2BAE8E"></span>
          <span class="cname">Smartworld MIS</span><span class="cdesc">Same engine on the Compile SW Data schema.</span></div>
        <div class="row"><span class="rail" style="background:#E4572E"></span>
          <span class="cname">NBH MIS</span><span class="cdesc">NoBrokerHood facility-management complaint data.</span></div>
      </div>
    </div>
    <div class="foot">Internal tool · to change the data, replace the Excel in the server's data folder</div>
  </div>
  <div class="side"><div class="card">
    <h2>Sign in</h2>
    <p class="hint">Sign in, then choose an application.</p>
    <div class="field"><label for="u">Username</label><input id="u" autocomplete="username" autofocus/></div>
    <div class="field"><label for="p">Password</label><input id="p" type="password" autocomplete="current-password"/></div>
    <p class="err" id="err"></p>
    <button id="go">Sign in</button>
    <div class="note">Default account — change in <code>app.py</code>:<br/>
      <code>admin / admin</code></div>
  </div></div>
</div>
<script>
const $=(i)=>document.getElementById(i);
async function go(){{
  $("go").disabled=true;$("err").textContent="";
  try{{
    const r=await fetch("/__gate/login",{{method:"POST",headers:{{"Content-Type":"application/json"}},
      body:JSON.stringify({{username:$("u").value,password:$("p").value}})}});
    if(r.ok){{location.replace("/");return}}
    const d=await r.json().catch(()=>({{}}));$("err").textContent=d.error||"Sign-in failed.";
  }}catch{{$("err").textContent="Could not reach the server."}}
  $("go").disabled=false;
}}
$("go").addEventListener("click",go);
for(const i of ["u","p"])$(i).addEventListener("keydown",(e)=>e.key==="Enter"&&go());
</script></body></html>"""


def home_html(username: str) -> str:
    cards = "".join(
        f"""<a class="app-card" href="/__gate/select/{aid}">
              <div class="mark" style="background:{a['accent']}">{a['name'].split()[0]}</div>
              <div class="body">
                <div class="t">{a['name']}</div>
                <div class="d">{a['desc']}</div>
              </div>
              <div class="arrow">→</div>
            </a>"""
        for aid, a in APPS.items()
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>MIS Company — Home</title>
<style>{_BASE_CSS}
.top{{background:linear-gradient(135deg,var(--navy-900),var(--navy-700));color:#fff;
padding:14px 24px;display:flex;justify-content:space-between;align-items:center}}
.top .wm{{font-weight:800}}.top .wm span{{font-weight:400;opacity:.65}}
.top a{{color:#fff;font-size:13px;border:1px solid rgba(255,255,255,.35);
border-radius:6px;padding:6px 12px;text-decoration:none}}
.top a:hover{{background:rgba(255,255,255,.15)}}
.wrap{{max-width:760px;margin:0 auto;padding:48px 24px}}
h1{{font-size:24px;margin:0 0 6px}}
.sub{{color:var(--text-600);margin:0 0 28px}}
.app-card{{display:flex;align-items:center;gap:18px;background:#fff;
border:1px solid var(--border);border-radius:10px;box-shadow:0 1px 2px rgba(15,31,61,.06);
padding:18px 20px;margin-bottom:14px;text-decoration:none;color:inherit;transition:box-shadow .12s}}
.app-card:hover{{box-shadow:0 4px 16px rgba(15,31,61,.12)}}
.mark{{width:46px;height:46px;border-radius:10px;display:flex;align-items:center;
justify-content:center;color:#fff;font-weight:800;font-size:13px;flex:0 0 auto}}
.body{{flex:1}}.t{{font-weight:700;font-size:15px}}.d{{color:var(--text-600);font-size:13px;margin-top:2px}}
.arrow{{color:var(--text-400);font-size:20px}}
.note{{margin-top:24px;font-size:12.5px;color:var(--text-400)}}
</style></head><body>
<div class="top">
  <div class="wm">MIS Company <span>/ home</span></div>
  <div><span style="opacity:.7;font-size:13px;margin-right:12px">{username}</span>
  <a href="/__gate/logout">Sign out</a></div>
</div>
<div class="wrap">
  <h1>Choose an application</h1>
  <p class="sub">Each application loads its data from its own Excel folder on the server.</p>
  {cards}
  <p class="note">To update the numbers: replace the Excel in
  <b>data/m3m</b>, <b>data/smartworld</b> or <b>data/nbh</b> on the server,
  wait a few seconds, then refresh inside the application.</p>
</div></body></html>"""


def loading_html(title: str, error: str | None) -> str:
    if error:
        body = f"""<h1>Data problem</h1>
        <p class="msg err">{error}</p>
        <p class="msg">Fix or replace the Excel in the data folder on the server -
        this page will continue checking automatically.</p>"""
    else:
        body = f"""<div class="spin"></div><h1>Loading data…</h1>
        <p class="msg">Reading the Excel for <b>{title}</b>.
        You'll be taken in automatically.</p>"""
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta http-equiv="refresh" content="2"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title}</title><style>{_BASE_CSS}
.wrap{{min-height:100%;display:flex;flex-direction:column;align-items:center;
justify-content:center;text-align:center;padding:24px}}
h1{{font-size:24px;margin:18px 0 6px}}
.msg{{color:var(--text-600);max-width:52ch;line-height:1.55;margin:6px 0}}
.msg.err{{color:var(--red-600);font-weight:600}}
.spin{{width:42px;height:42px;border:4px solid var(--border);
border-top-color:var(--teal-500);border-radius:50%;animation:r 1s linear infinite}}
@keyframes r{{to{{transform:rotate(360deg)}}}}
a{{color:var(--teal-600)}}
</style></head><body><div class="wrap">{body}
<p class="msg" style="font-size:12.5px">
<a href="/__gate/home">← Back to home</a></p></div></body></html>"""


# ------------------------------------------ injected into every proxied page

# Hides the original apps' upload UI without changing a single app file:
#  - M3M/SW: removes the "Upload New File" header button; if the upload
#    landing screen ever shows (empty data folder), replaces it with a note.
#  - NBH: hides the "Upload" nav tab (NavLink to "/").
INJECT = """
<style>
  /* --- MIS Company gateway bar --- */
  #mis-gate-bar {
    position: fixed; top: 0; left: 0; right: 0; height: 40px; z-index: 2147483647;
    display: flex; align-items: center; gap: 10px; padding: 0 14px;
    background: linear-gradient(135deg, #0F1F3D, #1F3864); color: #fff;
    font: 13px/1 'Segoe UI', Arial, sans-serif; box-shadow: 0 2px 8px rgba(15,31,61,.25);
    box-sizing: border-box;
  }
  #mis-gate-bar .gb-brand { font-weight: 800; letter-spacing: .2px; }
  #mis-gate-bar .gb-user { opacity: .7; font-size: 12px; }
  #mis-gate-bar .gb-spacer { flex: 1; }
  #mis-gate-bar a {
    color: #fff; text-decoration: none; font-weight: 600; font-size: 12.5px;
    border: 1px solid rgba(255,255,255,.4); border-radius: 6px; padding: 6px 14px;
  }
  #mis-gate-bar a:hover { background: rgba(255,255,255,.15); }
  /* Offset the whole app by the banner height WITHOUT changing body/#root
     height (the apps rely on html,body,#root{height:100%}; adding a body
     margin would make #root taller than the viewport and break their
     flex layout). padding-top on <html> plus box-sizing keeps 100% intact. */
  html { padding-top: 40px !important; box-sizing: border-box; }
  /* re-anchor the apps' own sticky bars below our banner */
  .app-header { top: 40px !important; }
  .active-filters-bar { top: 102px !important; }
  /* hide original upload UI + viewer/admin toggle */
  nav a[href="/"] { display: none !important; }
  .role-badge { display: none !important; }
</style>
<div id="mis-gate-bar">
  <span class="gb-brand">MIS Company</span>
  <span class="gb-user">__USER__</span>
  <span class="gb-spacer"></span>
  <a href="/__gate/home">Home</a>
  <a href="/__gate/logout">Sign out</a>
</div>
<script>
(function () {
  function sweep() {
    document.querySelectorAll("button").forEach(function (b) {
      if (/upload new file/i.test(b.textContent || "")) b.remove();
    });
    var up = document.querySelector(".upload-screen .upload-card");
    if (up && !up.dataset.misPatched) {
      up.dataset.misPatched = "1";
      up.innerHTML =
        "<h1 style='margin:0 0 8px'>Data loads automatically</h1>" +
        "<p style='color:#4A5568'>This application reads its Excel from the server's " +
        "data folder. Ask the administrator to place the file there.</p>";
    }
  }
  var pending = null;
  function schedule() {           // debounced: at most one sweep per 400ms
    if (pending) return;
    pending = setTimeout(function () { pending = null; sweep(); }, 400);
  }
  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", sweep);
  else sweep();
  new MutationObserver(schedule).observe(document.documentElement, { childList: true, subtree: true });
})();
</script>
"""
# ------------------------------------------------------------------ gateway

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))

HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
       "te", "trailers", "transfer-encoding", "upgrade", "host",
       "content-length", "accept-encoding", "content-encoding"}


@app.post("/__gate/login")
async def login(request: Request):
    try:
        body = await request.json()
        username = str(body.get("username", "")).strip().lower()
        password = str(body.get("password", ""))
    except Exception:
        return JSONResponse({"error": "Bad request."}, status_code=400)
    acct = ACCOUNTS.get(username)
    if not acct or not hmac.compare_digest(acct["password"], password):
        return JSONResponse({"error": "Incorrect username or password."}, status_code=401)
    resp = JSONResponse({"ok": True})
    set_session_cookie(resp, username, None)
    return resp


@app.get("/__gate/status")
async def gate_status(request: Request):
    if not read_session(request.cookies.get(COOKIE)):
        return JSONResponse({"error": "Not signed in."}, status_code=401)
    out = {}
    for aid, a in APPS.items():
        p = _engine_procs.get(aid)
        st = _ingest_state.get(aid) or {}
        f = _newest_excel(DATA / a["data_dir"])
        out[aid] = {
            "engine_running": bool(p and p.poll() is None),
            "data_loaded": bool(st.get("ok")),
            "error": st.get("error"),
            "newest_excel": f.name if f else None,
            "excel_size_mb": round(f.stat().st_size / 1048576, 1) if f else None,
        }
    return JSONResponse(out, headers={"Cache-Control": "no-store"})


@app.get("/__gate/logout")
async def logout():
    # Serve the login page directly - no redirect hop, instant.
    resp = page(LOGIN_HTML)
    resp.delete_cookie(COOKIE, path="/")
    return resp


@app.get("/__gate/home")
async def go_home(request: Request):
    s = read_session(request.cookies.get(COOKIE))
    if not s:
        resp = page(LOGIN_HTML)
        resp.delete_cookie(COOKIE, path="/")
        return resp
    # Serve the home page directly - no redirect hop, instant.
    resp = page(home_html(s["u"]))
    set_session_cookie(resp, s["u"], None, s.get("t0"))
    return resp


@app.get("/__gate/select/{app_id}")
async def select_app(app_id: str, request: Request):
    s = read_session(request.cookies.get(COOKIE))
    if not s or app_id not in APPS:
        return RedirectResponse("/", status_code=302)
    target = APPS[app_id].get("root_redirect", "/")
    resp = RedirectResponse(target, status_code=302)
    set_session_cookie(resp, s["u"], app_id, s.get("t0"))
    return resp


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def route_all(request: Request, path: str):
    session = read_session(request.cookies.get(COOKIE))

    if session is None:
        if request.method in ("GET", "HEAD"):
            return page(LOGIN_HTML)
        return JSONResponse({"error": "Not signed in."}, status_code=401)

    if session.get("a") is None:
        if request.method in ("GET", "HEAD"):
            resp = page(home_html(session["u"]))
            set_session_cookie(resp, session["u"], None, session.get("t0"))
            return resp
        return JSONResponse({"error": "No application selected."}, status_code=400)

    target = APPS[session["a"]]

    # Until this app's Excel is loaded, page navigations get a friendly
    # auto-refreshing "loading" screen instead of an empty application.
    ready, err = data_ready(session["a"])
    if not ready and request.method == "GET" and \
            "text/html" in request.headers.get("accept", ""):
        resp = page(loading_html(target["title"], err))
        set_session_cookie(resp, session["u"], session["a"], session.get("t0"))
        return resp

    # NBH's "/" route is its upload page - send people to the dashboard.
    if path == "" and "root_redirect" in target:
        return RedirectResponse(target["root_redirect"], status_code=302)

    url = f"http://127.0.0.1:{target['port']}/{path}"
    if request.url.query:
        url += "?" + request.url.query
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP}
    body = await request.body()

    try:
        upstream = await client.request(request.method, url, headers=headers, content=body)
    except httpx.ConnectError:
        return Response(
            f"{target['title']} engine is not running yet - give it a few seconds and refresh.\n"
            f"If this persists, check the console where app.py is running.",
            status_code=502, media_type="text/plain")

    out_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP}
    ctype = upstream.headers.get("content-type", "")

    # The NBH frontend build has "http://localhost:8000" baked in as its API
    # base, which breaks when the page is opened via the LAN IP or any other
    # host (cross-origin: the session cookie isn't sent). Rewrite it to a
    # relative base in any JS the proxy serves, so API calls always target
    # the address the user actually opened. App files stay untouched.
    if ("javascript" in ctype or "ecmascript" in ctype) and \
            b"http://localhost:8000" in upstream.content:
        patched = upstream.content.replace(b"http://localhost:8000", b"")
        out_headers["cache-control"] = "no-store"
        out_headers.pop("etag", None)
        out_headers.pop("last-modified", None)
        resp = Response(patched, status_code=upstream.status_code,
                        headers=out_headers, media_type=ctype)
        set_session_cookie(resp, session["u"], session["a"], session.get("t0"))
        return resp

    if "text/html" in ctype:
        html = upstream.text
        inject = INJECT.replace("__USER__", session["u"])
        html = html.replace("http://localhost:8000", "")
        i = html.lower().rfind("</body>")
        html = (html[:i] + inject + html[i:]) if i != -1 else html + inject
        out_headers["cache-control"] = "no-store"
        out_headers.pop("etag", None)
        out_headers.pop("last-modified", None)
        resp = Response(html, status_code=upstream.status_code, headers=out_headers, media_type=ctype)
        set_session_cookie(resp, session["u"], session["a"], session.get("t0"))
        return resp

    resp = Response(upstream.content, status_code=upstream.status_code, headers=out_headers)
    set_session_cookie(resp, session["u"], session["a"], session.get("t0"))
    return resp


# ----------------------------------------------------------- engine startup

def start_engines():
    for aid, a in APPS.items():
        p = subprocess.Popen(a["cmd"], cwd=str(a["cwd"]))
        _engine_procs[aid] = p
        print(f"  [{p.pid:>6}] {a['title']}  (internal :{a['port']})")


def stop_engines(*_):
    for p in _engine_procs.values():
        if p.poll() is None:
            p.terminate()
    for p in _engine_procs.values():
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()


# ------------------------------------------------- Excel folder auto-ingest

# aid -> {"key": (path, mtime), "ok": bool, "error": str|None}
_ingest_state: dict[str, dict] = {}
_engine_procs: dict[str, subprocess.Popen] = {}


def _newest_excel(folder: Path):
    if not folder.exists():
        return None
    files = [f for f in folder.iterdir()
             if f.suffix.lower() in (".xlsx", ".xls") and not f.name.startswith("~$")]
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


def data_ready(aid: str):
    """(ready, error_message) for the gateway's loading interstitial."""
    st = _ingest_state.get(aid)
    if st and st.get("ok"):
        return True, None
    return False, (st or {}).get("error")


def _ingest(aid: str, file: Path):
    a = APPS[aid]
    key = (str(file), file.stat().st_mtime)
    size_mb = file.stat().st_size / 1048576
    print(f"  [data {aid}] uploading {file.name} ({size_mb:.1f} MB) - "
          f"large files can take a few minutes...")
    t_start = time.time()
    try:
        with open(file, "rb") as fh:
            r = httpx.post(f"http://127.0.0.1:{a['port']}/api/upload",
                           files={"file": (file.name, fh,
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                           timeout=600)
        if r.status_code == 200:
            _ingest_state[aid] = {"key": key, "ok": True, "error": None}
            print(f"  [data {aid}] loaded {file.name} into {a['title']} "
                  f"in {time.time() - t_start:.0f}s")
        else:
            detail = r.text[:400]
            _ingest_state[aid] = {"key": key, "ok": False,
                                  "error": f"{file.name} was rejected: {detail}"}
            print(f"  [data {aid}] engine REJECTED {file.name} ({r.status_code}): {detail}")
    except Exception as e:
        # Engine not reachable yet (still importing pandas etc.) - leave state
        # unset so the watcher retries on its next pass.
        _ingest_state.pop(aid, None)
        print(f"  [data {aid}] engine not ready yet ({type(e).__name__}) - will retry")


def _watch_loop():
    time.sleep(3)
    while True:
        for aid, a in APPS.items():
            # --- supervise the engine: restart it if it died ---
            p = _engine_procs.get(aid)
            if p is not None and p.poll() is not None:
                print(f"  [engine {aid}] exited with code {p.returncode} - restarting. "
                      f"(If this repeats: pip install -r requirements.txt)")
                _ingest_state.pop(aid, None)  # fresh engine has no data
                np = subprocess.Popen(a["cmd"], cwd=str(a["cwd"]))
                _engine_procs[aid] = np
                continue  # give it a cycle to boot before uploading

            # --- (re)load the newest Excel when it changes ---
            file = _newest_excel(DATA / a["data_dir"])
            if file is None:
                _ingest_state.setdefault(aid, {"key": None, "ok": False,
                    "error": f"No Excel file found in data/{a['data_dir']}/ - "
                             f"place the file there."})
                continue
            key = (str(file), file.stat().st_mtime)
            st = _ingest_state.get(aid)
            if st is None or st.get("key") != key:
                _ingest(aid, file)
        time.sleep(4)


# -------------------------------------------------------------------- start

def lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def main():
    print("\nStarting MIS Company (single application)...\n")
    start_engines()
    threading.Thread(target=_watch_loop, daemon=True).start()

    print(f"\n  Share this link:   http://{lan_ip()}:{PORT}")
    print(f"  On this machine:   http://localhost:{PORT}\n")
    print("  Account:  admin / admin")
    print("  Excel folders (auto-loaded, newest file wins):")
    print("      data/m3m/    data/smartworld/    data/nbh/")
    print("  Ctrl+C stops everything.\n")

    signal.signal(signal.SIGINT, lambda *_: (stop_engines(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda *_: (stop_engines(), sys.exit(0)))

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
    stop_engines()


if __name__ == "__main__":
    main()
