# Smartworld Customer Complaint MIS — Source Project

This is the full source code behind `sw_mis_app.py` — a Customer Complaint
Management MIS / Dashboard for Smartworld, built as a Python (FastAPI)
backend and a plain-JS React frontend, shipped to end users as a single
runnable file.

This project was adapted from an equivalent M3M application built on the
same architecture. The application logic, UI, and features are the same;
what changed is the set of fields the backend recognizes (Smartworld's
"Compile SW Data" export uses different column names and a few different
fields than M3M's did) and the default Project/Category data loaded from
Smartworld's own `SW_List.xlsx`. See "What's different from the M3M
version" below for the specifics.

If you just want to **run the app**, you don't need anything in this folder —
use the standalone `sw_mis_app.py` instead. This project is for **developing
or modifying** the application in an editor like VS Code.

```
sw-mis-source/
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
│   └── build_launcher.py     Assembles backend/ + frontend/ into one sw_mis_app.py
├── tests/
│   ├── test_backend.py       Fast smoke test of engine/analytics/exports (no server)
│   ├── test_e2e.py           Full browser test via Playwright (upload → export)
│   └── test_manage_lists.py  Browser test of the admin/Manage Lists screen
├── requirements.txt          Python dependencies
├── package.json               Reference manifest for the frontend vendor bundles
└── README.md                  This file
```

## What's different from the M3M version

Smartworld's SFDC export ("Compile SW Data") uses a genuinely different
schema from M3M's "Compile M3M Data" - some fields are simply named
differently, some M3M fields don't exist at all for Smartworld, and
Smartworld has two fields of its own. All of this was reverse-engineered
from the actual `SW_Data.xlsx` / `SW_List.xlsx` files, including reading the
real Excel formulas behind the computed fields, not guessed.

- **Sheet name**: `Compile SW Data` (`engine.REQUIRED_SHEET`).
- **Renamed fields recognized via new aliases** (`engine.FIELD_ALIASES`):
  Opened Date also matches "Date/Time Opened"; Case Status also matches
  "Status"; Case Ageing also matches "Age"; Project Name also matches
  "Project"; Project Unit also matches "Property"; Client Category also
  matches "HNI Customer" (a boolean tier flag rather than a text category,
  but the same role).
- **Two new fields with no M3M equivalent**: `area` and `sub_area` (Smartworld's
  "Area" / "Sub Area" columns), with their own filter dimension, Analysis-tab
  report, and case-detail display, layered on top of the existing Service
  Category / Sub Category fields (which stay in the schema but are blank in
  Smartworld's export).
- **M_Category is looked up against Area, not Service Category** - confirmed
  from Compile_SW_Data.xlsx's own formula:
  `=XLOOKUP(Area, LIST!Category, LIST!M_Category, "Others/Misc")`. This is
  configurable: `engine.CONFIG["m_category_lookup_field"]` (set to `"area"`
  here; set it back to `"service_category"` if adapting this engine again for
  a workbook that uses that field instead).
- **A different OPEN-status list** - Smartworld's own "Updated Status" formula
  is `=IF(OR(Status={"In Progress","Re-Open","New","Pending for
  Clarification"}),"OPEN","Closed")` - note "Pending for Clarification"
  replaces M3M's "Submit For Approval". See `engine.CONFIG["open_case_statuses"]`.
- **Fields Smartworld's export doesn't have at all**: Escalation, Team
  Leader, HOD, IA Status, IA Remarks. The app degrades gracefully for these
  exactly as it does for any optional field the source workbook lacks -
  the related KPIs/filters/reports simply show empty/zero rather than
  erroring, and `meta.missing_fields` reports them after upload.
- **Overview tab and Top 5/Bottom 5 cards** automatically show Area instead
  of Service Category when Service Category carries no data (`analytics.py`
  and `tabs.js` both check which field is actually populated before
  choosing what to group by), so the dashboard is meaningful out of the box
  rather than showing a blank "Service Category Split" chart.
- **Default LIST data** (`engine._DEFAULT_PROJECTS`, `_DEFAULT_CATEGORY_ROWS`)
  is Smartworld's actual 9-project list and 22-Area list from `SW_List.xlsx`.
  That file's M_Category column was empty as provided; each Area is defaulted
  to map to itself (the one populated data sample confirmed this matches
  what the workbook actually produces, e.g. Area="Possessions" ->
  M_Category="Possessions") - edit the mapping from Manage Lists, or upload a
  filled-in LIST.xlsx, to group Areas under coarser M_Categories instead.
- **Admin passcode** for Manage Lists defaults to `swadmin` (was `m3madmin`).

Everything else - the KPI set, the RAG thresholds, the daily-trend
calculation, the Excel/PDF exports, the Manage Lists screen itself, the
filter drawer, the case table and drill-down - is identical to the M3M
application; only the data model adapts to Smartworld's actual file.

## Why plain JS instead of a React build (Vite/webpack)?

The frontend **is** React — real `React.createElement` calls, real component
tree, real hooks (`useState`, `useEffect`, etc.) — just written with
[htm](https://github.com/developit/htm) tagged templates instead of JSX, so
no compiler is needed. `frontend/static/vendor/` contains the production
UMD builds of React, ReactDOM, htm, and Chart.js, checked into the repo.
This means:

- The shipped `sw_mis_app.py` never needs Node.js/npm on the end user's
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
python tests/test_backend.py /path/to/SW_Data.xlsx

# Full: real headless-browser test of the whole app (needs Playwright)
pip install playwright && playwright install chromium
python tests/test_e2e.py /path/to/SW_Data.xlsx

# Manage Lists admin screen (viewer read-only, wrong/right passcode, edit+save)
python tests/test_manage_lists.py /path/to/SW_Data.xlsx
```

## Building the single-file deliverable

After changing anything in `backend/` or `frontend/`, regenerate the
shippable file:

```bash
cd build
python build_launcher.py
# -> writes ../dist/sw_mis_app.py
```

The build script works by base64-encoding each backend module's source and
a zip of the whole `frontend/` folder, and embedding all of it as string
constants inside one `.py` file. At runtime, `sw_mis_app.py` decodes those
strings, registers each backend module in `sys.modules` under its own name
(so `import engine`, `import analytics`, etc. inside the other modules keep
working unmodified), unzips the frontend into a local `sw_mis_appdata/`
folder next to the script, and starts a normal FastAPI/Uvicorn server. See
the comments at the top of `build/build_launcher.py` for the full mechanics.

## Architecture notes

- **Column detection is alias-based, not positional** (`engine.py`,
  `FIELD_ALIASES`). Each canonical field (Case Number, Priority, SLAB, ...)
  is matched against a list of accepted header variants in a single
  left-to-right pass, so a workbook with reordered, renamed (within reason),
  or extra columns still processes correctly. See `detect_columns()`.
- **All business rules (RAG thresholds, SLA target, ageing buckets, alias
  lists, the OPEN-status set, SLAB thresholds, admin passcode, the M_Category
  lookup field) live in one `CONFIG` dict and `FIELD_ALIASES` list** at the
  top of `engine.py` — nothing is hard-coded inline in the calculation
  functions. This is exactly what made adapting the M3M engine for
  Smartworld's different schema a config/alias change rather than a rewrite.
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
