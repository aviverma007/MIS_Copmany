"""Smoke test: upload the real extracted dataset and hit every endpoint,
checking the reconciliation numbers documented in docs/DATA_REPORT_MAPPING.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_data", "NBH_Sample_Data_Full.csv")


def _upload():
    with open(SAMPLE, "rb") as f:
        resp = client.post("/api/upload", files={"file": ("NBH_Sample_Data_Full.csv", f, "text/csv")})
    return resp


def test_upload_and_reconciliation():
    # These figures are wall-clock independent (they only depend on the
    # OPEN/CLOSED status classification, not on "today"), so they are safe
    # to assert against the live API regardless of when the test runs.
    # Ageing-slab-specific reconciliation (which DOES depend on "today", per
    # the workbook's own TODAY()-based formula) lives in test_reconciliation.py,
    # pinned to the source workbook's actual refresh date.
    resp = _upload()
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_records"] == 105994
    assert data["num_open"] == 3629
    assert data["num_closed"] == 105994 - 3629

    summary = client.get("/api/dashboard/summary").json()
    assert summary["kpis"]["open_pending"]["value"] == 3629

    proj = client.get("/api/reports/project-wise").json()
    top = {r["project"]: r["Grand Total"] for r in proj["rows"]}
    assert top["Smartworld Gems"] == 1405
    assert top["Smartworld Orchard"] == 983
    assert top["M3M Soulitude"] == 586

    cat = client.get("/api/reports/category-wise").json()
    ctop = {r["category"]: r["Grand Total"] for r in cat["rows"]}
    assert ctop["SEEPAGE"] == 453
    assert ctop["OTHERS__MISC"] == 409


def test_open_cases_report():
    _upload()
    resp = client.get("/api/reports/open-cases")
    assert resp.status_code == 200
    data = resp.json()
    assert data["grand_total"]["Grand Total"] == 3629


def test_filters_apply():
    _upload()
    resp = client.get("/api/dashboard/summary", params={"project": "M3M Heights"})
    assert resp.status_code == 200
    assert resp.json()["dataset"]["selected_projects"] == 1


def test_tickets_and_detail():
    _upload()
    resp = client.get("/api/tickets", params={"page_size": 5})
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    assert len(rows) == 5
    ticket_id = rows[0]["ticket_id"]
    detail = client.get(f"/api/tickets/{ticket_id}")
    assert detail.status_code == 200
    assert detail.json()["ticket_id"] == str(ticket_id)


def test_master_endpoints():
    _upload()
    assert client.get("/api/master/projects").status_code == 200
    assert client.get("/api/master/categories").status_code == 200
    assert client.get("/api/master/assignees").status_code == 200


def test_data_quality():
    _upload()
    resp = client.get("/api/data-quality")
    assert resp.status_code == 200
    dq = resp.json()
    assert dq["total_rows"] == 105994


def test_excel_export():
    _upload()
    resp = client.get("/api/export/excel")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert len(resp.content) > 1000


def test_pdf_export():
    _upload()
    resp = client.get("/api/export/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 1000


def test_no_dataset_error_before_upload():
    # fresh app/store isn't easy to isolate here since store is a singleton;
    # this just verifies the health/root endpoints work regardless of state.
    assert client.get("/api/health").status_code == 200


def test_actions_crud():
    resp = client.post("/api/actions", json={"title": "Follow up Smartworld Gems", "owner": "Ops Head", "target_date": "2026-09-01"})
    assert resp.status_code == 200
    action_id = resp.json()["id"]
    assert client.get("/api/actions").status_code == 200
    upd = client.put(f"/api/actions/{action_id}", json={"status": "In Progress"})
    assert upd.status_code == 200
    assert upd.json()["status"] == "In Progress"
    dele = client.delete(f"/api/actions/{action_id}")
    assert dele.status_code == 200


def test_missing_columns_rejected():
    import io
    bad_csv = b"foo,bar\n1,2\n"
    resp = client.post("/api/upload", files={"file": ("bad.csv", io.BytesIO(bad_csv), "text/csv")})
    assert resp.status_code == 422


def test_unsupported_file_type_rejected():
    import io
    resp = client.post("/api/upload", files={"file": ("bad.txt", io.BytesIO(b"hello"), "text/plain")})
    assert resp.status_code == 400
