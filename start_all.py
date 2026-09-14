"""
MIS Company - unified launcher.

Starts all four services:

    http://localhost:8000   Portal (login page - start here)
    http://localhost:8001   M3M Customer Complaint MIS
    http://localhost:8002   Smartworld Customer Complaint MIS
    http://localhost:8003   NBH Complaint Management Dashboard

Usage:
    pip install -r requirements-all.txt
    python start_all.py

Ports can be overridden with env vars PORTAL_PORT, M3M_PORT, SW_PORT,
NBH_PORT (if you change them, update portal/src/accounts.js and rebuild
the portal, or edit the built JS accordingly).

Ctrl+C stops everything.
"""
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PORTAL_PORT = int(os.environ.get("PORTAL_PORT", 8000))
M3M_PORT = int(os.environ.get("M3M_PORT", 8001))
SW_PORT = int(os.environ.get("SW_PORT", 8002))
NBH_PORT = int(os.environ.get("NBH_PORT", 8003))

PY = sys.executable

# Small bootstrap run inside each M3M/SW backend dir: import its api_app,
# mount its plain-JS frontend, serve on the given port.
MIS_BOOT = (
    "import sys, uvicorn; sys.path.insert(0, '.'); import api_app; "
    "api_app.mount_frontend('../frontend'); "
    "uvicorn.run(api_app.app, host='0.0.0.0', port={port}, log_level='warning')"
)

SERVICES = [
    {
        "name": f"Portal        http://localhost:{PORTAL_PORT}",
        "cwd": ROOT / "portal" / "dist",
        "cmd": [PY, "-m", "http.server", str(PORTAL_PORT), "--bind", "0.0.0.0"],
    },
    {
        "name": f"M3M MIS       http://localhost:{M3M_PORT}",
        "cwd": ROOT / "apps" / "m3m-mis" / "backend",
        "cmd": [PY, "-c", MIS_BOOT.format(port=M3M_PORT)],
    },
    {
        "name": f"Smartworld    http://localhost:{SW_PORT}",
        "cwd": ROOT / "apps" / "sw-mis" / "backend",
        "cmd": [PY, "-c", MIS_BOOT.format(port=SW_PORT)],
    },
    {
        "name": f"NBH MIS       http://localhost:{NBH_PORT}",
        "cwd": ROOT / "apps" / "nbh-mis" / "backend",
        "cmd": [
            PY, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", str(NBH_PORT),
            "--log-level", "warning",
        ],
    },
]


def main():
    if not (ROOT / "portal" / "dist" / "index.html").exists():
        print("portal/dist is missing - build it first:")
        print("    cd portal && npm install && npm run build")
        sys.exit(1)

    procs = []
    print("Starting MIS Company suite...\n")
    for svc in SERVICES:
        p = subprocess.Popen(svc["cmd"], cwd=str(svc["cwd"]))
        procs.append((svc["name"], p))
        print(f"  [{p.pid:>6}] {svc['name']}")

    print("\nOpen  http://localhost:%d  and sign in.  Ctrl+C stops everything." % PORTAL_PORT)
    try:
        webbrowser.open(f"http://localhost:{PORTAL_PORT}/")
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
            for name, p in procs:
                if p.poll() is not None:
                    print(f"\n[!] {name.strip()} exited with code {p.returncode}. "
                          f"Check its logs above; missing Python deps are the usual cause\n"
                          f"    (pip install -r requirements-all.txt).")
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        print("\nStopping all services...")
        for _, p in procs:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        for _, p in procs:
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
        print("Done.")


if __name__ == "__main__":
    main()
