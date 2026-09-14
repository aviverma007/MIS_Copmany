# NBH Customer Complaint Management Dashboard

A dynamic Management Information System (MIS) for NoBrokerHood (NBH) customer
complaint / facility-management data, built for M3M India. Upload an NBH
export, get a one-page executive dashboard, drill-down reports, Excel/PDF
export, and a management action tracker — no manual spreadsheet work, and no
hard-coded business values: every number is recomputed from whatever data you
upload.

This was built directly against a real 105,994-row NBH export (the supplied
`NBH Template.xlsx`, which — as delivered — had its `Compile NBH Data` sheet
trimmed to a couple of example rows but still carried the full dataset in its
pivot cache). The backend's business logic was reverse-engineered from that
workbook's actual formulas and validated to reconcile exactly against its
`Open Cases`, `Project Wise` and `Category Wise` reports. See
**`docs/DATA_REPORT_MAPPING.md`** for the full write-up — read that first if
you want to understand *why* a number is computed the way it is.

## What's in this repository

```
NBH-MIS/
├── backend/          FastAPI service: upload, cleaning, analytics, reports, exports
│   └── static/       Pre-built frontend (from frontend/dist) — served directly, see Option A below
├── frontend/         React + Vite executive dashboard & reports UI (source)
├── sample_data/      A ready-to-upload test dataset (see below) + a blank template
├── docs/             DATA_REPORT_MAPPING.md — the reverse-engineered business logic
├── exports/          Excel/PDF files land here if you save server-side copies
└── README.md         This file
```

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm

## Quick start — Option A: single process, no Node/npm required (recommended on locked-down machines)

`backend/static/` already contains a pre-built copy of the frontend. The
backend serves it directly, so this is the whole setup:

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser — that's the full
application (upload screen, dashboard, everything), served from the one
Python process. No npm install, no separate frontend server, nothing that
needs admin rights or hits the npm registry. This is the path to use if
`npm install` fails on your machine due to a corporate firewall/proxy or
antivirus locking files (a common combination on managed corporate laptops).

If you later change frontend source code and want your edits reflected here,
rebuild it and re-copy the output:
```bash
cd frontend && npm install && npm run build
# then copy the contents of frontend/dist/ into backend/static/
```

## Quick start — Option B: separate dev servers (for active frontend development)

**1. Backend**

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`). It
holds the current dataset in memory (see `app/store.py`) — restarting the
backend clears it, by design, until you wire in a real database.

**2. Frontend**

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_BASE_URL, defaults to http://localhost:8000
npm run dev
```

Open the printed local URL (typically `http://localhost:5173`) — this runs
Vite's dev server with hot-reload, separate from the backend. Use this only
when you're actively editing frontend code; otherwise Option A is simpler.

**3. Upload data**

Either upload your own NBH export, or use the bundled test file:
`sample_data/NBH_Sample_Data_Full.csv` — this is the real 105,994-row dataset
recovered from the supplied `NBH Template.xlsx`'s pivot cache (see below). On
successful upload you're redirected straight to the Executive Dashboard.

You can also click **Download Sample Template** on the Upload screen at any
time to get a blank `.xlsx` with the exact expected headers.

## About the sample data (important for a fair first look)

`NBH_Sample_Data_Full.csv` is real historical data whose most recent ticket
was created 06-Aug-2026. Ageing is always computed against **today's actual
date** (exactly like the source workbook's own `TODAY()` formula — see
`docs/DATA_REPORT_MAPPING.md` §3). If you open the dashboard with this sample
file well after that date, every open ticket will look artificially old and
the RAG scorecard will skew red — that's correct behavior given stale data,
not a bug. For a representative demo, either upload a current export, or keep
in mind the open-case *ageing distribution* will look worse than it did on
06-Aug-2026 while the *totals* (3,629 open / 102,365 closed, per-project and
per-category counts) remain exactly as documented and reconciled.

## Configuration — nothing is hard-coded

Every business rule lives in `backend/app/config.py`, not in the frontend and
not scattered across services:

- `COLUMN_ALIASES` / `REQUIRED_COLUMNS` — which header spellings map to which
  logical field, and which are mandatory.
- `CLOSED_STATUSES` — which raw `Status` values count as closed; anything
  else (including a brand-new status your next export introduces) defaults
  to OPEN so it doesn't silently vanish from the backlog.
- `AGEING_BUCKETS` — the five ageing slabs, reproduced exactly from the
  workbook's own SLAB formula.
- `RAG_RULES` / `CRITICAL_AGEING_THRESHOLD_DAYS` — Red/Amber/Green thresholds.
- `CATEGORY_MAPPING` / `DEFAULT_MANAGEMENT_CATEGORY` — the 46-entry raw
  category → management category table reproduced from the workbook's `LIST`
  sheet, with `Others/Misc` as the default for anything unmapped (flagged in
  Data Quality, not silently dropped).
- `PRIORITY_ALIASES`, `MAX_UPLOAD_SIZE_MB`, `ALLOWED_UPLOAD_EXTENSIONS`,
  `EXPORT_SHEET_ORDER`.

Uploading a new NBH file with different projects/categories/assignees "just
works" without touching code — the frontend populates every filter dropdown
from `/api/master/*`, which is derived live from whatever you uploaded.

## API endpoints

All endpoints are prefixed `/api` and documented interactively at
`/docs` once the backend is running. Every dashboard/report GET accepts the
same filter query params: `year, month, project, status, priority, category,
management_category, source, assignee, ageing_slab, escalation_level,
management_status (OPEN|CLOSED), date_from, date_to, search`.

| Group | Endpoints |
|---|---|
| Upload | `POST /api/upload`, `GET /api/upload/template`, `GET /api/data-quality` |
| Dashboard | `GET /api/dashboard/summary`, `/trends`, `/ageing`, `/insights` |
| Reports | `GET /api/reports/open-cases`, `/project-wise`, `/category-wise`, `/management-category-wise`, `/assignee-wise`, `/priority-wise`, `/escalation-wise`, `/source-wise`, `/rating` |
| Tickets | `GET /api/tickets` (paginated, sortable, filterable), `GET /api/tickets/{ticket_id}` |
| Master data | `GET /api/master/{projects,categories,management-categories,assignees,statuses,sources,priorities,ageing-slabs,years}` |
| Export | `GET /api/export/excel`, `GET /api/export/pdf` (both honor active filters) |
| Actions | `GET/POST /api/actions`, `PUT/DELETE /api/actions/{id}` |

## Report logic validation

`backend/tests/test_reconciliation.py` recomputes the entire pipeline from
raw data (pinned to the source workbook's actual last-refresh date) and
asserts an exact match against every number visible in the supplied
`NBH Template.xlsx`: total records, open/closed counts, the full ageing-slab
split, and per-project/per-category totals for the top entries. Run it with:

```bash
cd backend
python3 -m pytest tests/ -v
```

All 18 tests (reconciliation + API smoke tests covering upload validation,
filters, exports, drill-down, and the action tracker) pass against the
bundled sample dataset.

## Troubleshooting

- **`npm install` fails with `ECONNRESET` / EPERM cleanup errors on
  `node_modules`** — this is a corporate network (proxy/firewall blocking the
  npm registry) and/or antivirus file-locking issue, not a project bug. If
  you can't get IT to allow it, you don't need npm at all: use **Option A**
  above — the frontend is already pre-built into `backend/static/`, so the
  whole app runs from the Python backend alone.
- **`uvicorn` not recognized as a command** — Windows doesn't put Python's
  script folder on PATH by default. Always run it as `python -m uvicorn ...`
  (or `py -m uvicorn ...`) instead of the bare `uvicorn` command.
- **"No dataset has been uploaded yet" (409)** — the backend's in-memory
  store is empty (fresh start or restart). Upload a file again.
- **"Missing required column(s)..." (422) on upload** — your file is missing
  one of `Society Name, Ticket ID, Created On, Status, Category` (or a
  recognized alias of one). Check headers against
  `sample_data/NBH_Upload_Template.xlsx`.
- **Numbers look "too red"/too old** — see *About the sample data* above;
  ageing is always relative to today, not to when the file was generated.
- **CORS errors in the browser** — confirm `VITE_API_BASE_URL` in
  `frontend/.env` matches where uvicorn is actually running.

## Known assumptions (documented per spec, not silent)

- Closure timestamp priority when a ticket is Closed: `Closed Time` →
  `Resolved Time` → `Last updated on`, first non-blank wins. If none exist,
  ageing keeps accruing from Created On to today and the ticket is flagged
  `closure_date_missing` internally.
- An unrecognized/future `Status` value defaults to management status OPEN
  rather than CLOSED (safer for visibility) — configurable in
  `CLOSED_STATUSES`.
- Rows with a duplicate `Ticket ID` are **kept, not deduplicated**, for
  count-based reporting — this matches how the source workbook's own pivot
  tables count rows (verified during reconciliation), and duplicates are
  separately reported under Data Quality rather than silently collapsed.
