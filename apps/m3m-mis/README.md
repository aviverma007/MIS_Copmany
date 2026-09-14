# M3M Customer Complaint MIS — Source Project

This is the full source code behind `m3m_mis_app.py` — a Customer Complaint
Management MIS / Dashboard for M3M, built as a Python (FastAPI) backend and
a plain-JS React frontend, shipped to end users as a single runnable file.

If you just want to **run the app**, you don't need anything in this folder —
use the standalone `m3m_mis_app.py` instead. This project is for **developing
or modifying** the application in an editor like VS Code.

```
m3m-mis-source/
├── backend/                 FastAPI app + all data-processing logic
│   ├── engine.py            Column detection, cleaning, derived fields,
│   │                        SFDC date normalization, business-rule formulas,
│   │                        LIST parsing/defaults
│   ├── analytics.py         Filters, KPIs, reports, trend, attention, data quality
│   ├── export_excel.py      Formatted multi-sheet Excel export
│   ├── export_pdf.py        Full PDF report + executive one-pager (ReportLab)
│   ├── api_app.py           FastAPI routes, in-memory session state, admin auth
│   └── dev_server.py        Run backend + frontend together for local dev
├── frontend/                 Plain-JS React app (no build step)
│   ├── index.html            Entry point, loads vendor + src scripts in order
│   └── static/
│       ├── vendor/           Self-hosted UMD bundles: React, ReactDOM, htm, Chart.js
│       ├── src/               utils.js, components.js, sections.js, tabs.js,
│       │                      manage_lists.js, app.js
│       └── styles.css         Design system (CSS custom properties)
├── build/
│   └── build_launcher.py     Assembles backend/ + frontend/ into one m3m_mis_app.py
├── docs-generator/
│   └── build_doc.js          Generates the Word field-mapping reference doc
├── tests/
│   ├── test_backend.py       Fast smoke test of engine/analytics/exports (no server)
│   ├── test_e2e.py           Full browser test via Playwright (upload → export)
│   └── test_manage_lists.py  Browser test of the admin/Manage Lists screen
├── requirements.txt          Python dependencies
├── package.json               Reference manifest for the frontend vendor bundles
└── README.md                  This file
```

## What's new in this version

**1. SFDC date-format fix.** Salesforce report exports commonly deliver date
fields as plain text in day-first format — `"08/09/2026"` or
`"08/09/2026, 11:05 am"` — rather than real Excel dates, and often mix both
shapes in the same column. `engine._parse_dates()` now normalizes these
correctly (day-first, with a fast vectorized pass plus a targeted fallback
for mixed date/date-time values) before anything else touches them, and all
dates display as `DD-MMM-YYYY` (e.g. `08-Sep-2026`) throughout the app,
exports included.

**2. Business-rule formulas, computed fresh instead of trusted from the
file.** The original Excel template computed F_Closed, the Received/Closed
"Today vs Older" buckets, Updated Status, TAT Days, SLAB, and M_Category
with live formulas (`=TODAY()`, `=XLOOKUP(...)` against the LIST sheet).
Those formulas can't survive a raw data export, so `engine.apply_business_rules()`
recreates the exact same logic in Python — verified field-for-field against
the original workbook's formula outputs. This runs automatically after every
upload and again whenever the Category mapping changes, so these fields are
never stale copies.

**3. Manage Lists (admin screen).** A new "Manage Lists" tab lets an admin
view/edit the Project, Month, and Year dropdown lists and the Category →
M_Category mapping table used throughout the app, or upload a replacement
`LIST.xlsx`. Access is gated by a lightweight local passcode (see
`engine.CONFIG["admin_passcode"]`, default `m3madmin` — change it there and
rebuild). This is intentionally simple local-app access control, not
enterprise authentication; anyone running the app on their own machine can
see the passcode in the source. Viewers can see the current lists read-only
at any time.

## Why plain JS instead of a React build (Vite/webpack)?

The frontend **is** React — real `React.createElement` calls, real component
tree, real hooks (`useState`, `useEffect`, etc.) — just written with
[htm](https://github.com/developit/htm) tagged templates instead of JSX, so
no compiler is needed. `frontend/static/vendor/` contains the production
UMD builds of React, ReactDOM, htm, and Chart.js, checked into the repo.
This means:

- The shipped `m3m_mis_app.py` never needs Node.js/npm on the end user's
  machine — only Python.
- Editing `frontend/static/src/*.js` and refreshing the browser is enough;
  there's no `npm run build` step in the loop during development either.
- The whole frontend is small enough (~450 KB unminified across all files)
  to embed directly inside the single-file build.

## Local development

```bash
python -m venv .venv

# activate it:
source .venv/bin/activate          # Mac/Linux
.\.venv\Scripts\Activate.ps1        # Windows PowerShell (VS Code's default terminal)
.venv\Scripts\activate.bat          # Windows Command Prompt

pip install -r requirements.txt

cd backend
python dev_server.py
# -> opens http://127.0.0.1:8000, frontend served straight from ../frontend
```

> **Windows PowerShell note:** if `.\.venv\Scripts\Activate.ps1` fails with
> *"running scripts is disabled on this system"*, your execution policy is
> blocking it. Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
> first (this only relaxes the restriction for the current terminal window,
> not system-wide), then retry. And note the leading `.\` and the `.ps1`
> extension are both required — leaving either out produces a confusing
> *"The module '.venv' could not be loaded"* error, because PowerShell tries
> to interpret `.venv` as a module name instead of a folder.

Edit any file under `frontend/static/src/` or `backend/*.py` and refresh the
browser (backend changes need the server restarted; `dev_server.py` doesn't
run with `--reload` by default — add `reload=True` in `uvicorn.run(...)` in
`dev_server.py` if you want that during a long editing session).

### Running tests

```bash
# Fast: exercises the data pipeline directly, no browser/server
python tests/test_backend.py /path/to/M3M_Sample_Template.xlsx

# Full: real headless-browser test of the whole app (needs Playwright)
pip install playwright && playwright install chromium
python tests/test_e2e.py /path/to/M3M_Sample_Template.xlsx

# Manage Lists admin screen (viewer read-only, wrong/right passcode, edit+save)
python tests/test_manage_lists.py
```

## Building the single-file deliverable

After changing anything in `backend/` or `frontend/`, regenerate the
shippable file:

```bash
cd build
python build_launcher.py
# -> writes ../dist/m3m_mis_app.py
```

The build script works by base64-encoding each backend module's source and
a zip of the whole `frontend/` folder, and embedding all of it as string
constants inside one `.py` file. At runtime, `m3m_mis_app.py` decodes those
strings, registers each backend module in `sys.modules` under its own name
(so `import engine`, `import analytics`, etc. inside the other modules keep
working unmodified), unzips the frontend into a local `m3m_mis_appdata/`
folder next to the script, and starts a normal FastAPI/Uvicorn server. See
the comments at the top of `build/build_launcher.py` for the full mechanics.

## Regenerating the Word reference document

```bash
npm install docx
node docs-generator/build_doc.js
# -> writes M3M_MIS_Field_Mapping_Reference.docx in the current folder
```

## Architecture notes

- **Column detection is alias-based, not positional** (`engine.py`,
  `FIELD_ALIASES`). Each canonical field (Case Number, Priority, SLAB, ...)
  is matched against a list of accepted header variants in a single
  left-to-right pass, so a workbook with reordered, renamed (within reason),
  or extra columns still processes correctly. See `detect_columns()`.
- **All business rules (RAG thresholds, SLA target, ageing buckets, alias
  lists, the OPEN-status set, SLAB thresholds, admin passcode) live in one
  `CONFIG` dict and `FIELD_ALIASES` list** at the top of `engine.py` —
  nothing is hard-coded inline in the calculation functions.
- **Two-stage pipeline**: `engine.load_and_process()` handles column
  detection, cleaning, and date-independent derived fields (calendar
  breakdown, escalation flag, ageing bucket). `engine.apply_business_rules()`
  is a separate second stage for everything that depends on "today" or the
  LIST mapping (Updated Status, TAT Days, SLAB, M_Category, the Received/
  Closed buckets) — kept separate so it can be re-run on its own whenever
  the Category mapping changes, without re-uploading the source workbook.
  `api_app.py`'s `SESSION.raw_df` / `SESSION.df` hold the before/after.
- **The daily trend calculation is fully vectorized** (`analytics.daily_trend`)
  — no per-row or per-day Python loop — so it stays fast at 500,000+ records,
  per the performance requirement. Group-by reports (`_group_report`) are
  similarly built from whole-frame `groupby` aggregations rather than
  iterating groups in Python. Date parsing uses the same philosophy: a fast
  vectorized pass first, falling back to a slower element-by-element parse
  only for the values that didn't match (see `engine._parse_dates`).
- **Session state is in-memory only** (`api_app.py`, module-level `Session`
  object) — there is no database, and no uploaded data is ever written to
  disk, matching the "local, no database" requirement. This now also holds
  `list_state` (the current Project/Month/Year/Category lists) and
  `is_admin` (the Manage Lists access flag).
- **Filters are OR-within-dimension, AND-across-dimensions**
  (`analytics.apply_filters`): each dimension's selected values are combined
  with `.isin()` (OR), and the per-dimension masks are combined with `&`
  (AND).
