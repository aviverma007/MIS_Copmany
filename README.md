# MIS Company — Unified Complaint-MIS Suite

One React portal, three logins, three applications. Each username signs you
into exactly one dashboard:

| Login (default)         | Opens                              | Port |
| ----------------------- | ---------------------------------- | ---- |
| `m3m` / `M3M@123`       | M3M Customer Complaint MIS         | 8001 |
| `smartworld` / `SW@123` | Smartworld Customer Complaint MIS  | 8002 |
| `nbh` / `NBH@123`       | NBH Complaint Management Dashboard | 8003 |

The portal itself runs on **http://localhost:8000**. After signing in, the
matching application is shown inside the portal shell (with an
"Open in new tab" option and sign-out).

Change usernames/passwords in `portal/src/accounts.js` (then rebuild the
portal with `npm run build`).

## Repository layout

```
MIS_Copmany/
├── portal/              React (Vite) login portal — source in src/, prebuilt copy in dist/
├── apps/
│   ├── m3m-mis/         FastAPI + plain-JS React  (M3M SFDC complaint data)
│   ├── sw-mis/          FastAPI + plain-JS React  (Smartworld "Compile SW Data" schema)
│   └── nbh-mis/         FastAPI + React/Vite      (NoBrokerHood facility data)
├── start_all.py         Launches portal + all 3 backends together
├── requirements-all.txt Combined Python dependencies for the 3 backends
└── README.md
```

Each app folder keeps its own original README with full architecture notes,
tests and per-app run instructions.

## Quick start (one command)

Prerequisites: **Python 3.10+**. Node is *not* required to run — the portal
and the NBH frontend ship prebuilt.

```bash
pip install -r requirements-all.txt
python start_all.py
```

Then open **http://localhost:8000** and sign in. `Ctrl+C` stops all four
services.

## Developing

- **Portal**: `cd portal && npm install && npm run dev` (edit `src/`, then
  `npm run build` to refresh `dist/` used by `start_all.py`).
- **M3M / Smartworld**: plain-JS React, no build step — edit
  `apps/<app>/frontend/static/src/*.js` and refresh the browser.
- **NBH**: `cd apps/nbh-mis/frontend && npm install && npm run dev`; after
  changes, `npm run build` and copy `dist/` into `apps/nbh-mis/backend/static/`.

## Notes

- Ports are configurable via env vars `PORTAL_PORT`, `M3M_PORT`, `SW_PORT`,
  `NBH_PORT` — keep `portal/src/accounts.js` in sync if you change them.
- `apps/nbh-mis/sample_data/NBH_Sample_Data_Full.csv.gz` is the 106k-row test
  dataset, gzipped to keep the repo small — `gunzip` it before uploading.
- The portal login is a front-door/routing convenience for the suite, not a
  security boundary: the individual apps remain reachable on their own ports
  on the local network, and the M3M/SW apps keep their own separate admin
  password for their "Manage Lists" screens.
