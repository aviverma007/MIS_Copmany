// ---------------------------------------------------------------------------
// Data loader.
//
// For each company: find the newest .xlsx/.xls in data/<company>/, parse it,
// map columns via that company's aliases, and normalize every row into one
// canonical record shape. If no Excel exists, fall back to the prebuilt JSON
// test data in data/prebuilt/<company>.json.
//
// Hot reload: the file's mtime is checked on every API request (a cheap
// fs.stat). Replace the Excel in the folder and just refresh the browser -
// no restart, no rebuild. A manual "Reload data" button calls /api/reload
// which forces it regardless.
// ---------------------------------------------------------------------------

const fs = require("fs");
const path = require("path");
const XLSX = require("xlsx");
const { COMPANIES, CLOSED_STATUSES } = require("./companies");

const DATA_ROOT = path.join(__dirname, "..", "data");
const CLOSED_SET = new Set(CLOSED_STATUSES);

// company -> { records, source, loadedAt, fileMtime, filePath, warnings }
const cache = {};

function normHeader(h) {
  return String(h || "")
    .toLowerCase()
    .replace(/[\/_\-\.]+/g, " ")
    .replace(/[^a-z0-9() ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function newestExcel(company) {
  const dir = path.join(DATA_ROOT, COMPANIES[company].dataDir);
  if (!fs.existsSync(dir)) return null;
  const files = fs
    .readdirSync(dir)
    .filter((f) => /\.(xlsx|xls)$/i.test(f) && !f.startsWith("~$"))
    .map((f) => {
      const full = path.join(dir, f);
      return { full, mtime: fs.statSync(full).mtimeMs };
    })
    .sort((a, b) => b.mtime - a.mtime);
  return files[0] || null;
}

// --- date handling: Excel serials, JS Dates, and day-first strings ---------

function parseDate(v, dayFirst) {
  if (v == null || v === "") return null;
  if (v instanceof Date && !isNaN(v)) return v;
  if (typeof v === "number" && v > 20000 && v < 80000) {
    // Excel serial date
    const d = new Date(Math.round((v - 25569) * 86400 * 1000));
    return isNaN(d) ? null : d;
  }
  const s = String(v).trim();
  if (!s) return null;
  // dd/mm/yyyy or dd-mm-yyyy, optional time ("08/09/2026, 11:05 am")
  const m = s.match(
    /^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})(?:[, T]+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)?)?/i
  );
  if (m) {
    let [, a, b, y, hh, mm, ss, ap] = m;
    a = +a; b = +b; y = +y;
    if (y < 100) y += 2000;
    let day = a, mon = b;
    if (!dayFirst) { day = b; mon = a; }
    if (mon > 12 && day <= 12) { const t = day; day = mon; mon = t; } // auto-correct
    let H = hh ? +hh : 0;
    if (ap && /pm/i.test(ap) && H < 12) H += 12;
    if (ap && /am/i.test(ap) && H === 12) H = 0;
    const d = new Date(y, mon - 1, day, H, mm ? +mm : 0, ss ? +ss : 0);
    return isNaN(d) ? null : d;
  }
  const d = new Date(s); // ISO and friends
  return isNaN(d) ? null : d;
}

function iso(d) {
  return d ? d.toISOString().slice(0, 10) : null;
}

function monthKey(d) {
  return d ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}` : null;
}

function ageBucket(days) {
  if (days == null) return "Unknown";
  if (days <= 3) return "0-3 days";
  if (days <= 7) return "4-7 days";
  if (days <= 15) return "8-15 days";
  if (days <= 30) return "16-30 days";
  return "30+ days";
}

// --- normalization ---------------------------------------------------------

function mapColumns(headers, aliases) {
  const normed = headers.map((h) => ({ raw: h, norm: normHeader(h) }));
  const used = new Set();
  const mapping = {}; // canonical -> [raw headers in priority order]
  for (const pass of ["exact", "contains"]) {
    for (const [canon, aliasList] of Object.entries(aliases)) {
      mapping[canon] = mapping[canon] || [];
      for (const alias of aliasList) {
        for (const { raw, norm } of normed) {
          if (used.has(raw) || !norm) continue;
          const hit = pass === "exact" ? norm === alias : norm.includes(alias);
          if (hit) {
            mapping[canon].push(raw);
            used.add(raw);
          }
        }
      }
    }
  }
  return mapping;
}

function firstNonBlank(row, rawHeaders) {
  for (const h of rawHeaders || []) {
    const v = row[h];
    if (v !== undefined && v !== null && String(v).trim() !== "") return v;
  }
  return null;
}

function normalizeRows(rows, company) {
  const cfg = COMPANIES[company];
  if (!rows.length) return { records: [], warnings: ["File has no data rows."] };
  const mapping = mapColumns(Object.keys(rows[0]), cfg.aliases);
  const warnings = [];
  for (const key of ["id", "opened", "status"]) {
    if (!mapping[key] || !mapping[key].length) {
      warnings.push(`Could not find a "${key}" column - check the Excel headers.`);
    }
  }

  const today = new Date();
  const records = rows.map((row, i) => {
    const opened = parseDate(firstNonBlank(row, mapping.opened), cfg.dayFirstDates);
    const statusRaw = String(firstNonBlank(row, mapping.status) ?? "").trim();
    const statusNorm = statusRaw.toLowerCase().replace(/[\s\-]+/g, " ").trim();
    const isClosed = CLOSED_SET.has(statusNorm);
    const closed = isClosed
      ? parseDate(firstNonBlank(row, mapping.closed), cfg.dayFirstDates)
      : null;
    const tatEnd = closed || today;
    const tatDays = opened ? Math.max(0, Math.round((tatEnd - opened) / 86400000)) : null;

    return {
      id: String(firstNonBlank(row, mapping.id) ?? `ROW-${i + 1}`),
      customer: String(firstNonBlank(row, mapping.customer) ?? "").trim(),
      subject: String(firstNonBlank(row, mapping.subject) ?? "").trim(),
      project: String(firstNonBlank(row, mapping.project) ?? "Unassigned").trim() || "Unassigned",
      unit: String(firstNonBlank(row, mapping.unit) ?? "").trim(),
      category: String(firstNonBlank(row, mapping.category) ?? "Uncategorized").trim() || "Uncategorized",
      subCategory: String(firstNonBlank(row, mapping.subCategory) ?? "").trim(),
      priority: String(firstNonBlank(row, mapping.priority) ?? "").trim(),
      owner: String(firstNonBlank(row, mapping.owner) ?? "").trim(),
      source: String(firstNonBlank(row, mapping.source) ?? "").trim(),
      status: statusRaw || "Unknown",
      statusClass: isClosed ? "CLOSED" : "OPEN",
      opened: iso(opened),
      openedMonth: monthKey(opened),
      closed: iso(closed),
      tatDays,
      ageBucket: isClosed ? null : ageBucket(tatDays),
    };
  });

  return { records, warnings };
}

// --- loading + hot reload --------------------------------------------------

function loadPrebuilt(company) {
  const f = path.join(DATA_ROOT, "prebuilt", `${company}.json`);
  if (!fs.existsSync(f)) return null;
  try {
    return JSON.parse(fs.readFileSync(f, "utf8"));
  } catch {
    return null;
  }
}

function load(company, force = false) {
  const entry = cache[company];
  const file = newestExcel(company);

  if (!force && entry) {
    const same =
      (file && entry.filePath === file.full && entry.fileMtime === file.mtime) ||
      (!file && entry.source === "prebuilt");
    if (same) return entry;
  }

  if (file) {
    const wb = XLSX.readFile(file.full, { cellDates: true });
    // Prefer a sheet whose name mentions "data", else the first sheet.
    const sheetName =
      wb.SheetNames.find((n) => /data/i.test(n)) || wb.SheetNames[0];
    const rows = XLSX.utils.sheet_to_json(wb.Sheets[sheetName], { defval: null });
    const { records, warnings } = normalizeRows(rows, company);
    cache[company] = {
      records,
      warnings,
      source: path.basename(file.full) + " · sheet: " + sheetName,
      filePath: file.full,
      fileMtime: file.mtime,
      loadedAt: new Date().toISOString(),
    };
    return cache[company];
  }

  const pre = loadPrebuilt(company);
  cache[company] = {
    records: pre || [],
    warnings: pre
      ? [`No Excel found in data/${COMPANIES[company].dataDir}/ - showing prebuilt test data.`]
      : [`No Excel in data/${COMPANIES[company].dataDir}/ and no prebuilt data.`],
    source: pre ? "prebuilt test data (JSON)" : "no data",
    filePath: null,
    fileMtime: null,
    loadedAt: new Date().toISOString(),
  };
  return cache[company];
}

module.exports = { load };
