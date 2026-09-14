// ---------------------------------------------------------------------------
// MIS Company - Node/Express gateway.
//
//   npm install
//   npm start            ->  http://<this-machine>:8000
//
// ONE link for everyone. Sign in and the gateway routes ALL your traffic to
// YOUR company's application - which is the ORIGINAL M3M / Smartworld / NBH
// app running unchanged as an internal engine (127.0.0.1 only), so the look,
// feel and functionality are exactly the ones from the source projects.
//
//   m3m / M3M@123          -> M3M MIS        (engine on 127.0.0.1:9101)
//   smartworld / SW@123    -> Smartworld MIS (engine on 127.0.0.1:9102)
//   nbh / NBH@123          -> NBH MIS        (engine on 127.0.0.1:9103)
//
// EXCEL FOLDERS: drop each company's Excel into data/<company>/. The gateway
// watches the folders and auto-uploads the newest .xlsx into that company's
// engine - at startup and whenever the file changes. Replace the Excel,
// wait a moment, refresh the browser. No restart, no rebuild.
//
// Requirements on the machine: Node 18+, Python 3.10+ with
// requirements-all.txt installed (the engines are Python). Set the PYTHON
// env var if your python isn't on PATH.
// ---------------------------------------------------------------------------

const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");
const express = require("express");

const ROOT = path.join(__dirname, "..");
const DATA = path.join(ROOT, "data");
const PORT = parseInt(process.env.PORT || "8000", 10);
const PYTHON = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");

// ------------------------------------------------------------ configuration

const ACCOUNTS = {
  m3m:        { password: "M3M@123", company: "m3m" },
  smartworld: { password: "SW@123",  company: "smartworld" },
  nbh:        { password: "NBH@123", company: "nbh" },
};

const COMPANIES = {
  m3m: {
    title: "M3M Customer Complaint MIS",
    port: 9101,
    dataDir: "m3m",
    cwd: path.join(ROOT, "apps", "m3m-mis", "backend"),
    args: ["-c",
      "import sys, uvicorn; sys.path.insert(0, '.'); import api_app; " +
      "api_app.mount_frontend('../frontend'); " +
      "uvicorn.run(api_app.app, host='127.0.0.1', port=9101, log_level='warning')"],
  },
  smartworld: {
    title: "Smartworld Customer Complaint MIS",
    port: 9102,
    dataDir: "smartworld",
    cwd: path.join(ROOT, "apps", "sw-mis", "backend"),
    args: ["-c",
      "import sys, uvicorn; sys.path.insert(0, '.'); import api_app; " +
      "api_app.mount_frontend('../frontend'); " +
      "uvicorn.run(api_app.app, host='127.0.0.1', port=9102, log_level='warning')"],
  },
  nbh: {
    title: "NBH Complaint Management Dashboard",
    port: 9103,
    dataDir: "nbh",
    cwd: path.join(ROOT, "apps", "nbh-mis", "backend"),
    args: ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
      "--port", "9103", "--log-level", "warning"],
  },
};

const SESSION_TTL = 12 * 3600 * 1000;
const COOKIE = "mis_session";

// ---------------------------------------------------------- session cookies

const secretFile = path.join(ROOT, ".session_secret");
const SECRET = fs.existsSync(secretFile)
  ? fs.readFileSync(secretFile)
  : (() => { const s = crypto.randomBytes(32); fs.writeFileSync(secretFile, s); return s; })();

function makeSession(username, company) {
  const payload = Buffer.from(JSON.stringify({ u: username, c: company, t: Date.now() })).toString("base64url");
  const sig = crypto.createHmac("sha256", SECRET).update(payload).digest("base64url");
  return `${payload}.${sig}`;
}

function readSession(req) {
  const raw = (req.headers.cookie || "").split(";").map((s) => s.trim())
    .find((s) => s.startsWith(COOKIE + "="));
  if (!raw) return null;
  const token = raw.slice(COOKIE.length + 1);
  const dot = token.lastIndexOf(".");
  if (dot < 0) return null;
  const payload = token.slice(0, dot);
  const good = crypto.createHmac("sha256", SECRET).update(payload).digest("base64url");
  const sig = token.slice(dot + 1);
  if (sig.length !== good.length ||
      !crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(good))) return null;
  try {
    const data = JSON.parse(Buffer.from(payload, "base64url").toString());
    if (!COMPANIES[data.c] || Date.now() - data.t > SESSION_TTL) return null;
    return data;
  } catch { return null; }
}

// ------------------------------------------------------- engine supervision

function startEngines() {
  for (const [id, c] of Object.entries(COMPANIES)) {
    const child = spawn(PYTHON, c.args, { cwd: c.cwd, stdio: ["ignore", "inherit", "inherit"] });
    child.on("exit", (code) => {
      console.error(`[engine ${id}] exited with code ${code}. ` +
        `Usual cause: Python deps missing -> pip install -r requirements-all.txt ` +
        `(python used: ${PYTHON}; override with the PYTHON env var).`);
    });
    c.proc = child;
  }
}

function stopEngines() {
  for (const c of Object.values(COMPANIES)) {
    if (c.proc && c.proc.exitCode === null) c.proc.kill();
  }
}

// ------------------------------------------------ Excel folder auto-ingest

function newestExcel(dir) {
  if (!fs.existsSync(dir)) return null;
  const files = fs.readdirSync(dir)
    .filter((f) => /\.(xlsx|xls)$/i.test(f) && !f.startsWith("~$"))
    .map((f) => ({ full: path.join(dir, f), name: f, mtime: fs.statSync(path.join(dir, f)).mtimeMs }))
    .sort((a, b) => b.mtime - a.mtime);
  return files[0] || null;
}

async function ingest(id, file, attempt = 1) {
  const c = COMPANIES[id];
  // Mark as claimed immediately so the poller doesn't start a second
  // upload of the same file while this one is in flight / retrying.
  c.ingested = { path: file.full, mtime: file.mtime, pending: true };
  try {
    const buf = fs.readFileSync(file.full);
    const form = new FormData();
    form.append("file", new Blob([buf]), file.name);
    const res = await fetch(`http://127.0.0.1:${c.port}/api/upload`, { method: "POST", body: form });
    if (res.ok) {
      c.ingested = { path: file.full, mtime: file.mtime };
      console.log(`[data ${id}] loaded ${file.name} into ${c.title}`);
    } else {
      const detail = await res.text().catch(() => "");
      console.error(`[data ${id}] engine rejected ${file.name} (${res.status}): ${detail.slice(0, 300)}`);
      c.ingested = { path: file.full, mtime: file.mtime, failed: true }; // don't retry same file forever
    }
  } catch (e) {
    // Engine probably not up yet - retry with backoff for ~60s.
    if (attempt < 15) setTimeout(() => ingest(id, file, attempt + 1), 4000);
    else console.error(`[data ${id}] could not reach engine to load ${file.name}: ${e.message}`);
  }
}

function watchDataFolders() {
  const check = () => {
    for (const [id, c] of Object.entries(COMPANIES)) {
      const file = newestExcel(path.join(DATA, c.dataDir));
      if (!file) continue;
      const cur = c.ingested;
      if (!cur || cur.path !== file.full || cur.mtime !== file.mtime) ingest(id, file);
    }
  };
  setTimeout(check, 3000); // initial load once engines are (probably) up
  setInterval(check, 5000);
}

// ------------------------------------------------------------------ gateway

const app = express();

const LOGOUT_CHIP = (user) =>
  `<div style="position:fixed;right:14px;bottom:14px;z-index:2147483647;` +
  `font:12px/1 Segoe UI,Arial,sans-serif;background:#0F1F3D;color:#fff;` +
  `border:1px solid #2C4A7C;border-radius:6px;padding:7px 10px;opacity:.92">` +
  `${user} &nbsp;·&nbsp; <a href="/__gate/logout" style="color:#fff">Sign out</a></div>`;

app.post("/__gate/login", express.json(), (req, res) => {
  const username = String(req.body?.username || "").trim().toLowerCase();
  const password = String(req.body?.password || "");
  const acct = ACCOUNTS[username];
  const ok = acct && acct.password.length === password.length &&
    crypto.timingSafeEqual(Buffer.from(acct.password), Buffer.from(password));
  if (!ok) return res.status(401).json({ error: "Incorrect username or password." });
  res.setHeader("Set-Cookie",
    `${COOKIE}=${makeSession(username, acct.company)}; Max-Age=${SESSION_TTL / 1000}; Path=/; HttpOnly; SameSite=Lax`);
  res.json({ ok: true, title: COMPANIES[acct.company].title });
});

app.get("/__gate/logout", (_req, res) => {
  res.setHeader("Set-Cookie", `${COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax`);
  res.redirect("/");
});

// Everything else: login page if signed out, transparent proxy if signed in.
app.use((req, res) => {
  const session = readSession(req);

  if (!session) {
    if (req.method === "GET" || req.method === "HEAD") {
      return res.sendFile(path.join(__dirname, "login.html"));
    }
    return res.status(401).json({ error: "Not signed in." });
  }

  const target = COMPANIES[session.c];
  const headers = { ...req.headers };
  delete headers.host;
  delete headers["accept-encoding"]; // keep upstream responses uncompressed so we can inject the chip

  const upstream = http.request(
    { host: "127.0.0.1", port: target.port, path: req.originalUrl, method: req.method, headers },
    (ur) => {
      const ctype = ur.headers["content-type"] || "";
      const outHeaders = { ...ur.headers };
      if (ctype.includes("text/html")) {
        const chunks = [];
        ur.on("data", (d) => chunks.push(d));
        ur.on("end", () => {
          let html = Buffer.concat(chunks).toString("utf8");
          const i = html.toLowerCase().lastIndexOf("</body>");
          const chip = LOGOUT_CHIP(session.u);
          html = i !== -1 ? html.slice(0, i) + chip + html.slice(i) : html + chip;
          delete outHeaders["content-length"];
          res.writeHead(ur.statusCode, outHeaders);
          res.end(html);
        });
      } else {
        res.writeHead(ur.statusCode, outHeaders);
        ur.pipe(res);
      }
    }
  );

  upstream.on("error", () => {
    res.status(502).type("text/plain").send(
      `${target.title} engine is not running yet - give it a few seconds and refresh.\n` +
      `If this persists, install the Python dependencies:  pip install -r requirements-all.txt`
    );
  });

  req.pipe(upstream);
});

// -------------------------------------------------------------------- start

function lanIp() {
  for (const ifaces of Object.values(os.networkInterfaces()))
    for (const i of ifaces || [])
      if (i.family === "IPv4" && !i.internal) return i.address;
  return "localhost";
}

startEngines();
watchDataFolders();

const server = app.listen(PORT, "0.0.0.0", () => {
  console.log("\nMIS Company gateway is running.\n");
  console.log(`  Share this link:   http://${lanIp()}:${PORT}`);
  console.log(`  On this machine:   http://localhost:${PORT}\n`);
  console.log("  Logins:  m3m / M3M@123   smartworld / SW@123   nbh / NBH@123");
  console.log("  Excel folders (auto-loaded, newest file wins):");
  console.log("      data/m3m/    data/smartworld/    data/nbh/\n");
});

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => {
    console.log("\nStopping gateway and engines...");
    stopEngines();
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 3000);
  });
}
