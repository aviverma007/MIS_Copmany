"""
Local development server.

Runs the FastAPI backend (backend/api_app.py) and serves the frontend
directly from ../frontend (no bundling/build step - it's plain JS + htm,
so edits to frontend/src/*.js or frontend/index.html are picked up on a
browser refresh, no rebuild needed).

Usage:
    cd backend
    pip install -r ../requirements.txt
    python dev_server.py
    # -> http://127.0.0.1:8000

This is for local development only. The shippable artifact is built by
build/build_launcher.py, which embeds this same backend code plus a
zipped copy of the frontend into one m3m_mis_app.py file.
"""
import sys
import webbrowser
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import api_app  # noqa: E402

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def _open_browser_when_ready(port):
    import urllib.request
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    webbrowser.open(f"http://127.0.0.1:{port}/")


if __name__ == "__main__":
    import uvicorn

    api_app.mount_frontend(str(FRONTEND_DIR))
    port = 8000
    threading.Thread(target=_open_browser_when_ready, args=(port,), daemon=True).start()
    print(f"Dev server starting at http://127.0.0.1:{port}  (Ctrl+C to stop)")
    uvicorn.run(api_app.app, host="127.0.0.1", port=port, log_level="info", reload=False)
