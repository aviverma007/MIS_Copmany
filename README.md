# MIS Company — Single Fullstack Complaint MIS

**One application. One link. Three logins. Three companies. Three Excel folders.**

Node.js/Express backend + React frontend. Your login decides which company's
dashboard and which company's Excel data you see — same look, feel and
functionality for every company.

| Login (default)         | Company    | Excel folder       |
| ----------------------- | ---------- | ------------------ |
| `m3m` / `M3M@123`       | M3M        | `data/m3m/`        |
| `smartworld` / `SW@123` | Smartworld | `data/smartworld/` |
| `nbh` / `NBH@123`       | NBH        | `data/nbh/`        |

Change passwords in `server/companies.js`.

## Run it

Prerequisite: Node.js 18+ (zip/portable install works fine).

```bash
npm install
npm start
```

Open **http://localhost:8000** — the startup log also prints your LAN IP as a
shareable link for other users on the network.

## Updating the data (the whole point)

1. Drop the new Excel into that company's folder, e.g. `data/m3m/M3M_Sept.xlsx`
2. Refresh the browser — that's it.

- The **newest** `.xlsx` in the folder is always used (shown in the header).
- No restart, no rebuild — the server checks the file's timestamp on every
  request; there's also a **Reload data** button in the header to force it.
- Sheet selection: a sheet whose name contains "data" (e.g. `Compile M3M
  Data`) is preferred, else the first sheet.
- Column headers are matched through per-company alias lists in
  `server/companies.js`, taken from the original M3M / Smartworld / NBH
  applications — so the real SFDC / NBH exports map automatically. Add
  aliases there if a header isn't recognized (a warning banner in the app
  tells you when a required column wasn't found).
- If a folder has no Excel at all, prebuilt JSON test data from
  `data/prebuilt/` is shown instead (with a banner saying so).

Current excels are **generated test data** — replace with real files anytime.
Regenerate test data with `npm run sample-data`.

## Features

- Login → company-scoped dashboard (server-side sessions, HttpOnly cookie)
- KPI cards: total, open, closed, closure rate, average TAT
- Charts: monthly opened-vs-closed trend, open/closed split, open-case
  ageing buckets, top projects, top categories
- Filters: project, category, open/closed, priority, opened date range,
  free-text search — every number recomputes from the filtered set
- Paginated complaints table
- **Export Excel** of the current filtered view
- Day-first date handling (`08/09/2026`, `08/09/2026, 11:05 am`) and Excel
  serial dates, as in the original apps

## Structure

```
├── server/
│   ├── index.js        Express app: auth, API, static client, export
│   ├── companies.js    3 logins, 3 companies, column aliases  ← edit here
│   ├── loader.js       Excel reading, normalization, hot reload
│   └── analytics.js    Filters, KPIs, breakdowns, trend, paging
├── client/             React (Vite) frontend — prebuilt dist/ committed
├── data/
│   ├── m3m/ smartworld/ nbh/     ← drop each company's Excel here
│   └── prebuilt/                 JSON test-data fallback
└── scripts/make-sample-data.js   test-data generator
```

## Developing the frontend

```bash
cd client && npm install && npm run dev   # dev server on :5173, proxies /api to :8000
npm run build                             # refresh client/dist used by npm start
```
