# MIS Company — One Python Application

**One link. One screen. Login → Home → any of the three original applications.**
Pure Python (FastAPI). No Node required.

The original M3M, Smartworld and NBH applications run **completely unchanged**
inside this app — every tab, chart, filter drawer, report and Excel/PDF export
is the source projects' own code. The only functional differences: the upload
feature is hidden (data comes from Excel files in folders) and the
Viewer/Admin toggle in the header is hidden.

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:8000** — the console also prints your LAN IP as a
shareable link for other users.

Flow: **Sign in → Home page → choose an application** (switch any time via
the "Home" chip at the bottom-right of every page).

Single account (default): **`admin` / `admin`** — change it in `app.py`
(ACCOUNTS at the top).

## The Excel data (replaces the upload feature)

| Application    | Folder             | Expected sheet     |
| -------------- | ------------------ | ------------------ |
| M3M MIS        | `data/m3m/`        | `Compile M3M Data` |
| Smartworld MIS | `data/smartworld/` | `Compile SW Data`  |
| NBH MIS        | `data/nbh/`        | `Compile NBH Data` |

- Drop the new Excel into the folder → wait a few seconds → refresh the
  browser. The **newest** `.xlsx` in each folder is always the one loaded.
- No restart, no rebuild. The engines apply their full original processing
  (column detection, day-first SFDC dates, business-rule formulas).
- If an engine rejects a file (wrong sheet/columns), the reason prints in
  the `python app.py` console.
- Current tracked files are **generated sample data** — regenerate with
  `python scripts/make_sample_data.py`.
- **Real company excels are git-ignored on purpose** (this repo is public).
  Place them in the data folders directly on the server machine; the newest
  file in each folder always wins, so a real export automatically outranks
  the older test file sitting next to it.

## How it works

```
Browser ──► app.py (FastAPI gateway, :8000)
             ├─ no session          → login page
             ├─ signed in, no app   → home page (3 application cards)
             └─ app selected        → reverse-proxy everything to that app
                  ├─ M3M engine        127.0.0.1:9101  (original, unchanged)
                  ├─ Smartworld engine 127.0.0.1:9102  (original, unchanged)
                  └─ NBH engine        127.0.0.1:9103  (original, unchanged)
```

- `app.py` starts the three engines itself and watches the data folders,
  auto-loading the newest Excel into each engine at startup and on change.
- Engines bind to 127.0.0.1 only — the gateway is the single front door.
- Upload UI is hidden by the gateway at proxy time (a small injected
  style/script); **no application file is modified**.
- Sessions are signed HttpOnly cookies (12h). Bottom-right chip on every
  page: Home · Sign out.

## Structure

```
├── app.py                        The whole gateway (login, home, proxy, engines, folder watch)
├── apps/
│   ├── m3m-mis/                  Original M3M application (unmodified)
│   ├── sw-mis/                   Original Smartworld application (unmodified)
│   └── nbh-mis/                  Original NBH application (unmodified)
├── data/
│   ├── m3m/  smartworld/  nbh/   ← drop each company's Excel here
├── scripts/make_sample_data.py   Sample-data generator
└── requirements.txt
```
