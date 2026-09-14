# MIS Company — One Link, Three Logins, the Original Apps

A Node.js/Express gateway in front of the **original, unmodified** M3M,
Smartworld and NBH MIS applications — so the look, feel and functionality
are exactly the source projects', screen for screen (all tabs, reports,
Excel/PDF exports, Manage Lists, everything).

Everyone opens the **same link**. Your login decides which company's
application you see:

| Login (default)         | Application                        | Excel folder       |
| ----------------------- | ---------------------------------- | ------------------ |
| `m3m` / `M3M@123`       | M3M Customer Complaint MIS         | `data/m3m/`        |
| `smartworld` / `SW@123` | Smartworld Customer Complaint MIS  | `data/smartworld/` |
| `nbh` / `NBH@123`       | NBH Complaint Management Dashboard | `data/nbh/`        |

Change passwords in `server/index.js` (ACCOUNTS at the top).

## Run it

Prerequisites: **Node.js 18+** and **Python 3.10+** (the original app
engines are Python). Portable/zip installs of both work fine.

```bash
pip install -r requirements-all.txt   # once
npm install                            # once
npm start
```

Open **http://localhost:8000** — the startup log also prints your LAN IP as
the link to share with other users. If your python isn't on PATH, set the
`PYTHON` env var to its full path before `npm start`.

## Updating the data

1. Drop the new Excel into that company's folder, e.g. `data/m3m/M3M_Sept.xlsx`
2. Wait a few seconds, refresh the browser. Done.

The gateway watches the three folders and auto-uploads the **newest** `.xlsx`
into that company's engine — at startup and whenever the file changes. No
restart, no rebuild. The engines apply their own full processing exactly as
before (column detection, SFDC day-first dates, business-rule formulas).
If an engine rejects a file (wrong sheet/columns), the reason is printed in
the `npm start` console.

The excels currently in `data/` are **generated test data**
(`npm run sample-data` regenerates them) — replace them with the real
exports any time.

## How it works

```
Browser ──► Node gateway :8000
             ├─ no session  → login page
             └─ session     → reverse-proxy ALL traffic to that user's engine
                              (plus a small sign-out chip on every page)
                   ├─ M3M engine        127.0.0.1:9101  (original app, unchanged)
                   ├─ Smartworld engine 127.0.0.1:9102  (original app, unchanged)
                   └─ NBH engine        127.0.0.1:9103  (original app, unchanged)
```

- Engines bind to 127.0.0.1 only — not reachable from the network; the
  gateway is the single front door.
- Sessions are signed HttpOnly cookies (12h). Sign out via the bottom-right
  chip or `/__gate/logout`.
- The M3M/SW apps' own admin password for "Manage Lists" is unchanged from
  the source projects.

## Structure

```
├── server/
│   ├── index.js      Node gateway: 3 logins, proxy, engine startup, folder watch
│   └── login.html    Sign-in page
├── apps/
│   ├── m3m-mis/      Original M3M application (unmodified)
│   ├── sw-mis/       Original Smartworld application (unmodified)
│   └── nbh-mis/      Original NBH application (unmodified)
├── data/
│   ├── m3m/ smartworld/ nbh/     ← drop each company's Excel here
├── scripts/make-sample-data.js   Test-data generator
└── requirements-all.txt          Python deps for the three engines
```
