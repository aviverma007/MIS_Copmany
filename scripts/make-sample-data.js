// Generates realistic TEST data:
//   data/m3m/M3M_Test_Data.xlsx          (M3M SFDC-style headers)
//   data/smartworld/SW_Test_Data.xlsx    (Smartworld-style headers)
//   data/nbh/NBH_Test_Data.xlsx          (NBH-style headers)
//   data/prebuilt/<company>.json         (normalized fallback JSON)
//
// Run:  npm run sample-data
// Replace these excels with the real ones later - same folders, any filename.

const fs = require("fs");
const path = require("path");
const XLSX = require("xlsx");
const { load } = require("../server/loader");

const DATA = path.join(__dirname, "..", "data");

let seed = 42;
function rnd() {
  seed = (seed * 1103515245 + 12345) % 2147483648;
  return seed / 2147483648;
}
const pick = (a) => a[Math.floor(rnd() * a.length)];
const int = (lo, hi) => lo + Math.floor(rnd() * (hi - lo + 1));

function dmy(d) {
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

function dates() {
  const now = new Date(2026, 8, 14);
  const opened = new Date(now - int(0, 330) * 86400000);
  const closedFlag = rnd() < 0.72;
  const closed = closedFlag ? new Date(Math.min(+now, +opened + int(0, 45) * 86400000)) : null;
  return { opened, closed };
}

const FIRST = ["Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Rohan", "Kavita", "Suresh", "Neha", "Arjun", "Pooja"];
const LAST = ["Sharma", "Verma", "Gupta", "Singh", "Mehta", "Jain", "Agarwal", "Kapoor", "Malhotra", "Reddy"];
const name = () => `${pick(FIRST)} ${pick(LAST)}`;

const CATS = ["Plumbing", "Electrical", "Civil Works", "Housekeeping", "Billing", "Possession", "Club & Amenities", "Security"];
const SUBS = ["Leakage", "Wiring Fault", "Wall Crack", "Cleaning", "Invoice Query", "Handover Delay", "Gym Equipment", "Access Card"];
const PRIO = ["High", "Medium", "Low"];
const OWNERS = ["Ramesh Kumar", "Sunita Devi", "Manoj Tiwari", "Deepak Yadav", "Ritu Chauhan", "Ajay Bansal"];
const SOURCES = ["Phone", "Email", "Web", "Walk-in", "App"];

// ---- M3M ------------------------------------------------------------------
function m3mRows(n) {
  const projects = ["M3M Golf Estate", "M3M Merlin", "M3M Sierra", "M3M Heights", "M3M Skywalk", "M3M Latitude"];
  const rows = [];
  for (let i = 1; i <= n; i++) {
    const { opened, closed } = dates();
    rows.push({
      "Case Number": `M3M-${String(10000 + i)}`,
      "Account Name": name(),
      "Subject": `${pick(SUBS)} issue reported`,
      "Priority": pick(PRIO),
      "M_Category": pick(CATS),
      "Sub Category": pick(SUBS),
      "Opened Date": dmy(opened),
      "Closed Date": closed ? dmy(closed) : "",
      "Case Owner": pick(OWNERS),
      "Case Status": closed ? pick(["Closed", "Resolved"]) : pick(["Open", "In Progress", "Pending Customer"]),
      "Case Source": pick(SOURCES),
      "Project Name": pick(projects),
      "Project Unit": `${pick(["A", "B", "C", "T"])}-${int(101, 2404)}`,
    });
  }
  return rows;
}

// ---- Smartworld -----------------------------------------------------------
function swRows(n) {
  const projects = ["Smartworld Orchard", "Smartworld Gems", "Smartworld One DXP", "Smartworld The Edition", "Smartworld Sky Arc"];
  const rows = [];
  for (let i = 1; i <= n; i++) {
    const { opened, closed } = dates();
    rows.push({
      "Case Number": `SW-${String(50000 + i)}`,
      "Account Name": name(),
      "Subject": `${pick(SUBS)} complaint`,
      "Priority": pick(PRIO),
      "M_Category": pick(CATS),
      "Sub Category": pick(SUBS),
      "Date/Time Opened": `${dmy(opened)}, ${int(9, 18)}:${String(int(0, 59)).padStart(2, "0")}`,
      "Closed Date": closed ? dmy(closed) : "",
      "Case Owner": pick(OWNERS),
      "Status": closed ? pick(["Closed", "Resolved"]) : pick(["Open", "In Progress", "Escalated"]),
      "Case Source": pick(SOURCES),
      "Project": pick(projects),
      "Property": `${pick(["N", "S", "E", "W"])}-${int(1, 99)}${pick(["A", "B", "C", "D"])}`,
      "Age": int(0, 90),
    });
  }
  return rows;
}

// ---- NBH ------------------------------------------------------------------
function nbhRows(n) {
  const societies = ["M3M Woodshire", "M3M Escala", "M3M Marina", "M3M Duo High", "M3M Sierra 68"];
  const rows = [];
  for (let i = 1; i <= n; i++) {
    const { opened, closed } = dates();
    rows.push({
      "Ticket Id": `NBH-${String(900000 + i)}`,
      "Society Name": pick(societies),
      "Created On": dmy(opened),
      "Created By": name(),
      "Priority": pick(PRIO),
      "Category": pick(CATS),
      "Sub Category": pick(SUBS),
      "Description": `${pick(SUBS)} in ${pick(["tower", "flat", "common area", "basement"])}`,
      "Status": closed ? pick(["Closed", "Resolved"]) : pick(["Open", "Assigned", "In Progress"]),
      "Current Assignee": pick(OWNERS),
      "Source": pick(["App", "Helpdesk", "Call"]),
      "Reported_From(Apartment)": `${pick(["T1", "T2", "T3", "T4"])}-${int(101, 1804)}`,
      "Closed Time": closed ? dmy(closed) : "",
      "Rating": closed && rnd() < 0.6 ? int(1, 5) : "",
    });
  }
  return rows;
}

// ---- write ----------------------------------------------------------------
function writeExcel(rows, dir, filename, sheet) {
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(rows), sheet);
  const out = path.join(DATA, dir, filename);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  XLSX.writeFile(wb, out);
  console.log(`  wrote ${path.relative(process.cwd(), out)}  (${rows.length} rows)`);
}

writeExcel(m3mRows(320), "m3m", "M3M_Test_Data.xlsx", "Compile M3M Data");
writeExcel(swRows(280), "smartworld", "SW_Test_Data.xlsx", "Compile SW Data");
writeExcel(nbhRows(400), "nbh", "NBH_Test_Data.xlsx", "Compile NBH Data");

// Prebuilt JSON fallback = the normalized version of the same test data.
fs.mkdirSync(path.join(DATA, "prebuilt"), { recursive: true });
for (const c of ["m3m", "smartworld", "nbh"]) {
  const store = load(c, true);
  fs.writeFileSync(
    path.join(DATA, "prebuilt", `${c}.json`),
    JSON.stringify(store.records)
  );
  console.log(`  wrote data/prebuilt/${c}.json  (${store.records.length} records)`);
}
console.log("Done.");
