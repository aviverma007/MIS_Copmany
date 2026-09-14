// ---------------------------------------------------------------------------
// MIS Company - single fullstack server.
//
//   npm install
//   npm start          ->  http://<this-machine>:8000
//
// One link for everyone. Your login decides which company's dashboard and
// which company's Excel data you see:
//
//   m3m / M3M@123          -> data/m3m/
//   smartworld / SW@123    -> data/smartworld/
//   nbh / NBH@123          -> data/nbh/
//
// Replace an Excel in its folder and refresh the browser (or press the
// Reload button in the header) - the new data is picked up automatically,
// no restart or rebuild needed.
// ---------------------------------------------------------------------------

const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const express = require("express");
const XLSX = require("xlsx");

const { ACCOUNTS, COMPANIES } = require("./companies");
const { load } = require("./loader");
const { applyFilters, summary, filterOptions, page } = require("./analytics");

const PORT = parseInt(process.env.PORT || "8000", 10);
const CLIENT_DIST = path.join(__dirname, "..", "client", "dist");
const SESSION_TTL = 12 * 3600 * 1000;
const COOKIE = "mis_session";

// Signing secret persisted so sessions survive restarts.
const secretFile = path.join(__dirname, "..", ".session_secret");
const SECRET = fs.existsSync(secretFile)
  ? fs.readFileSync(secretFile)
  : (() => {
      const s = crypto.randomBytes(32);
      fs.writeFileSync(secretFile, s);
      return s;
    })();

// --- session cookie helpers -----------------------------------------------

const b64e = (b) => Buffer.from(b).toString("base64url");
const b64d = (s) => Buffer.from(s, "base64url").toString();

function makeSession(username, company) {
  const payload = b64e(JSON.stringify({ u: username, c: company, t: Date.now() }));
  const sig = crypto.createHmac("sha256", SECRET).update(payload).digest("base64url");
  return `${payload}.${sig}`;
}

function readSession(req) {
  const raw = (req.headers.cookie || "")
    .split(";")
    .map((s) => s.trim())
    .find((s) => s.startsWith(COOKIE + "="));
  if (!raw) return null;
  const token = raw.slice(COOKIE.length + 1);
  const dot = token.lastIndexOf(".");
  if (dot < 0) return null;
  const payload = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  const good = crypto.createHmac("sha256", SECRET).update(payload).digest("base64url");
  if (sig.length !== good.length || !crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(good)))
    return null;
  try {
    const data = JSON.parse(b64d(payload));
    if (!COMPANIES[data.c] || Date.now() - data.t > SESSION_TTL) return null;
    return data;
  } catch {
    return null;
  }
}

// --- app -------------------------------------------------------------------

const app = express();
app.use(express.json());

function requireAuth(req, res, next) {
  const s = readSession(req);
  if (!s) return res.status(401).json({ error: "Not signed in." });
  req.session = s;
  next();
}

app.post("/api/login", (req, res) => {
  const username = String(req.body?.username || "").trim().toLowerCase();
  const password = String(req.body?.password || "");
  const acct = ACCOUNTS[username];
  const ok =
    acct &&
    acct.password.length === password.length &&
    crypto.timingSafeEqual(Buffer.from(acct.password), Buffer.from(password));
  if (!ok) return res.status(401).json({ error: "Incorrect username or password." });

  res.setHeader(
    "Set-Cookie",
    `${COOKIE}=${makeSession(username, acct.company)}; Max-Age=${SESSION_TTL / 1000}; Path=/; HttpOnly; SameSite=Lax`
  );
  const c = COMPANIES[acct.company];
  res.json({ ok: true, company: acct.company, title: c.title, accent: c.accent });
});

app.post("/api/logout", (_req, res) => {
  res.setHeader("Set-Cookie", `${COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax`);
  res.json({ ok: true });
});

app.get("/api/me", (req, res) => {
  const s = readSession(req);
  if (!s) return res.json({ signedIn: false });
  const c = COMPANIES[s.c];
  res.json({
    signedIn: true,
    username: s.u,
    company: s.c,
    title: c.title,
    short: c.short,
    accent: c.accent,
  });
});

app.get("/api/data", requireAuth, (req, res) => {
  const store = load(req.session.c);
  const filtered = applyFilters(store.records, req.query);
  res.json({
    meta: {
      source: store.source,
      loadedAt: store.loadedAt,
      warnings: store.warnings,
      totalRecords: store.records.length,
    },
    filters: filterOptions(store.records),
    summary: summary(filtered),
    table: page(filtered, parseInt(req.query.page || "1", 10), parseInt(req.query.pageSize || "25", 10)),
  });
});

app.post("/api/reload", requireAuth, (req, res) => {
  const store = load(req.session.c, true);
  res.json({ ok: true, source: store.source, records: store.records.length, warnings: store.warnings });
});

app.get("/api/export", requireAuth, (req, res) => {
  const store = load(req.session.c);
  const filtered = applyFilters(store.records, req.query);
  const rows = filtered.map((r) => ({
    "Case/Ticket": r.id, Customer: r.customer, Subject: r.subject,
    Project: r.project, Unit: r.unit, Category: r.category,
    "Sub Category": r.subCategory, Priority: r.priority, Owner: r.owner,
    Source: r.source, Status: r.status, "Open/Closed": r.statusClass,
    "Opened Date": r.opened, "Closed Date": r.closed,
    "TAT Days": r.tatDays, "Ageing Bucket": r.ageBucket,
  }));
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), "Complaints");
  const buf = XLSX.write(wb, { type: "buffer", bookType: "xlsx" });
  const name = `${COMPANIES[req.session.c].short}_MIS_Export_${new Date().toISOString().slice(0, 10)}.xlsx`;
  res.setHeader("Content-Disposition", `attachment; filename="${name}"`);
  res.setHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
  res.send(buf);
});

// --- static client ---------------------------------------------------------

app.use(express.static(CLIENT_DIST));
app.get("*", (_req, res) => res.sendFile(path.join(CLIENT_DIST, "index.html")));

// --- start -----------------------------------------------------------------

function lanIp() {
  for (const ifaces of Object.values(os.networkInterfaces())) {
    for (const i of ifaces || []) {
      if (i.family === "IPv4" && !i.internal) return i.address;
    }
  }
  return "localhost";
}

app.listen(PORT, "0.0.0.0", () => {
  console.log("\nMIS Company is running.\n");
  console.log(`  Share this link:   http://${lanIp()}:${PORT}`);
  console.log(`  On this machine:   http://localhost:${PORT}\n`);
  console.log("  Logins:  m3m / M3M@123   smartworld / SW@123   nbh / NBH@123");
  console.log("  Excel folders:  data/m3m/  data/smartworld/  data/nbh/");
  console.log("  Replace an Excel and refresh the browser - data reloads automatically.\n");
});
