import sys, threading, time, urllib.request
from pathlib import Path

PROJECT_ROOT = Path("/home/claude/m3m_source_v2")
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
import api_app

PORT = 8833

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

start_server()

from playwright.sync_api import sync_playwright
errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    page.on("console", lambda m: errors.append((m.type, m.text)) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
    page.goto(f"http://127.0.0.1:{PORT}/", wait_until="load", timeout=15000)
    page.set_input_files('input[type="file"]', "/mnt/user-data/uploads/M3M_Sample_Template.xlsx")
    page.wait_for_selector(".kpi-card", timeout=45000)
    print("Data loaded.")

    # go to Manage Lists tab (as Viewer - should be read-only)
    page.click('button.tab-btn:has-text("Manage Lists")')
    page.wait_for_timeout(600)
    page.screenshot(path="/home/claude/m3m_source_v2/tests/shot_lists_viewer.png", full_page=True)
    viewer_note = page.inner_text(".viewer-note")
    print("Viewer note present:", "Unlock admin" in viewer_note)
    # inputs should be disabled in viewer mode
    disabled = page.eval_on_selector('table.editable-table input[type="text"]', 'el => el.disabled')
    print("Category input disabled in viewer mode:", disabled)

    # unlock admin with WRONG passcode
    page.click('button:has-text("Unlock Admin to Edit")')
    page.wait_for_selector('.passcode-modal', timeout=5000)
    page.fill('.passcode-modal input[type="password"]', 'wrongpass')
    page.click('.passcode-modal button[type="submit"]')
    page.wait_for_timeout(500)
    err_text = page.inner_text('.passcode-modal .upload-error')
    print("Wrong passcode error shown:", "Incorrect" in err_text)

    # unlock with CORRECT passcode
    page.fill('.passcode-modal input[type="password"]', 'm3madmin')
    page.click('.passcode-modal button[type="submit"]')
    page.wait_for_timeout(800)
    role_badge = page.inner_text('.role-badge')
    print("Role badge after unlock:", role_badge)

    # now in admin mode - edit a category mapping cell
    page.wait_for_timeout(300)
    first_mcat_input = page.locator('table.editable-table tbody tr:first-child td:nth-child(2) input')
    first_mcat_input.fill('TEST_CATEGORY_VALUE')
    page.click('button:has-text("💾 Save Changes")')
    page.wait_for_timeout(1000)
    saved_banner = page.inner_text('.save-banner')
    print("Save banner shown:", "Saved" in saved_banner)
    page.screenshot(path="/home/claude/m3m_source_v2/tests/shot_lists_admin.png", full_page=True)

    # verify KPIs still fine after list change (dashboard refreshed)
    page.click('button.tab-btn:has-text("Overview")')
    page.wait_for_timeout(800)
    total = page.inner_text('.kpi-card:first-child .val')
    print("Total cases KPI after list edit:", total)

    print("ERRORS:", errors)
    b.close()

# A 401 from the intentional wrong-passcode check above is expected, not a bug.
real_errors = [e for e in errors if "401" not in e[1]]
print("DONE - PASS" if not real_errors else "DONE - FAIL")
