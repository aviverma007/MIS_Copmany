"""
End-to-end test: starts the FastAPI backend (with the frontend mounted) in a
background thread, drives it with a real headless browser via Playwright,
and checks the whole upload -> dashboard -> filter -> export flow works with
zero console errors.

Usage:
    pip install -r ../requirements.txt
    pip install playwright && playwright install chromium
    python test_e2e.py /path/to/SW_Data.xlsx
"""
import sys
import threading
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import api_app  # noqa: E402

PORT = 8811


def start_server():
    import uvicorn
    api_app.mount_frontend(str(PROJECT_ROOT / "frontend"))
    config = uvicorn.Config(api_app.app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status", timeout=1)
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("Server did not start in time")


def main(sample_file: str):
    start_server()
    from playwright.sync_api import sync_playwright

    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 950})
        page.on("console", lambda m: errors.append((m.type, m.text)) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))

        page.goto(f"http://127.0.0.1:{PORT}/", wait_until="load", timeout=15000)
        page.set_input_files('input[type="file"]', sample_file)
        page.wait_for_selector(".kpi-card", timeout=45000)
        page.wait_for_timeout(500)
        print("Overview loaded OK.")

        for tab in ["Analysis", "Trends", "Case Table", "Data Quality"]:
            page.click(f'button.tab-btn:has-text("{tab}")')
            page.wait_for_timeout(400)
            print(f"{tab} tab OK.")

        page.click('button.tab-btn:has-text("Case Table")')
        page.wait_for_timeout(600)
        page.click(".case-link >> nth=0")
        page.wait_for_selector(".modal", timeout=5000)
        page.click(".modal-close")
        print("Case drill-down modal OK.")

        page.click('button.tab-btn:has-text("Overview")')
        page.wait_for_timeout(300)
        page.click('button:has-text("⚙ Filters")')
        page.wait_for_selector(".drawer", timeout=5000)
        page.click('button:has-text("Reset All Filters")')
        print("Filter drawer OK.")

        with page.expect_download(timeout=20000):
            page.click('button:has-text("Excel")')
        print("Excel export download OK.")

        browser.close()

    if errors:
        print("FAILED - console/page errors:", errors)
        sys.exit(1)
    print("ALL CHECKS PASSED - zero console errors.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_e2e.py /path/to/SW_Data.xlsx")
        sys.exit(1)
    main(sys.argv[1])
