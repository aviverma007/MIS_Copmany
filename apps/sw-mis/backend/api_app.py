"""
Smartworld MIS - FastAPI application.
Single-user local app: the uploaded workbook is held in a module-level
in-memory session (no database, per prompt section 21).
"""
import io
import json
import math
import threading
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import engine
import analytics
import export_excel
import export_pdf
from engine import FIELD_LABELS, DETAIL_TABLE_FIELDS

app = FastAPI(title="Smartworld Customer Complaint MIS")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Session:
    def __init__(self):
        self.lock = threading.Lock()
        self.raw_df = None    # post load_and_process, before business rules
        self.df = None        # raw_df + apply_business_rules(list_state) - what everything else reads
        self.meta = None
        self.list_state = engine.default_list_state()
        self.is_admin = False


SESSION = Session()


def _require_data():
    if SESSION.df is None:
        raise HTTPException(status_code=400, detail="No workbook has been uploaded yet.")
    return SESSION.df


def _require_admin():
    if not SESSION.is_admin:
        raise HTTPException(status_code=403, detail="Admin access is required to edit or upload lists. Unlock admin mode first.")


def _recompute_df():
    """Re-derives SESSION.df from SESSION.raw_df + the current list_state.
    Called after upload, and again whenever the LIST mapping changes, so
    M_Category (and anything else fed by the LIST) is always in sync
    without needing to re-upload the main data file."""
    if SESSION.raw_df is not None:
        SESSION.df = engine.apply_business_rules(SESSION.raw_df, SESSION.list_state)


def _clean_json(obj):
    """Recursively replace NaN/inf/NaT with None so JSONResponse never chokes
    on non-finite floats (pandas produces these constantly)."""
    if isinstance(obj, dict):
        return {k: _clean_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_json(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (pd.Timestamp,)):
        if pd.isna(obj):
            return None
        return obj.strftime("%Y-%m-%d")
    if obj is pd.NaT:
        return None
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return obj


def _json(data):
    return JSONResponse(content=_clean_json(data))


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx or .xls file.")
    content = await file.read()
    try:
        raw_df, meta = engine.load_and_process(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process workbook: {e}")

    with SESSION.lock:
        SESSION.raw_df = raw_df
        SESSION.meta = meta
        _recompute_df()
    return _json({"status": "ok", "meta": meta})


@app.get("/api/status")
def status():
    if SESSION.df is None:
        return _json({"loaded": False, "is_admin": SESSION.is_admin})
    return _json({"loaded": True, "meta": SESSION.meta, "is_admin": SESSION.is_admin})


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
@app.get("/api/filters/options")
def get_filter_options():
    df = _require_data()
    return _json(analytics.filter_options(df, SESSION.list_state))


# ---------------------------------------------------------------------------
# Dashboard (kpis + reports + trend + insights + attention + data quality)
# ---------------------------------------------------------------------------
@app.post("/api/dashboard")
def dashboard(payload: dict = Body(default={})):
    df = _require_data()
    filters = payload.get("filters") or {}
    fdf = analytics.apply_filters(df, filters)

    result = {
        "kpis": analytics.compute_kpis(fdf),
        "reports": analytics.build_reports(fdf),
        "daily_trend": analytics.daily_trend(fdf),
        "monthly_yearly": analytics.monthly_yearly_trend(fdf),
        "insights": analytics.management_insights(fdf),
        "attention": {k: {"count": v["count"]} for k, v in analytics.management_attention(fdf).items()},
        "data_quality": analytics.data_quality(fdf),
        "filtered_record_count": int(len(fdf)),
        "filtered_case_count": int(fdf["case_number"].nunique()) if "case_number" in fdf.columns else 0,
    }
    return _json(result)


@app.post("/api/attention/{area}")
def attention_detail(area: str, payload: dict = Body(default={})):
    df = _require_data()
    filters = payload.get("filters") or {}
    fdf = analytics.apply_filters(df, filters)
    attn = analytics.management_attention(fdf)
    if area not in attn:
        raise HTTPException(status_code=404, detail="Unknown attention area.")
    return _json(attn[area])


# ---------------------------------------------------------------------------
# Detail table
# ---------------------------------------------------------------------------
@app.post("/api/table")
def table(payload: dict = Body(default={})):
    df = _require_data()
    filters = payload.get("filters") or {}
    search = (payload.get("search") or "").strip().lower()
    sort_by = payload.get("sort_by") or "opened_date"
    sort_dir = payload.get("sort_dir") or "desc"
    page = int(payload.get("page") or 1)
    page_size = min(int(payload.get("page_size") or 25), 500)

    fdf = analytics.apply_filters(df, filters)
    fields = [f for f in DETAIL_TABLE_FIELDS if f in fdf.columns]
    out = fdf[fields]

    if search:
        mask = pd.Series(False, index=out.index)
        for c in out.columns:
            if out[c].dtype == object or str(out[c].dtype) == "string":
                mask |= out[c].astype(str).str.lower().str.contains(search, na=False, regex=False)
        out = out[mask]

    total = len(out)
    if sort_by in out.columns:
        out = out.sort_values(sort_by, ascending=(sort_dir == "asc"), na_position="last")

    start = (page - 1) * page_size
    page_rows = out.iloc[start:start + page_size].copy()
    for c in page_rows.columns:
        if str(page_rows[c].dtype).startswith("datetime"):
            page_rows[c] = page_rows[c].dt.strftime("%d-%b-%Y")
    records = page_rows.to_dict(orient="records")

    return _json({
        "total": total,
        "page": page,
        "page_size": page_size,
        "fields": fields,
        "labels": {f: FIELD_LABELS.get(f, f) for f in fields},
        "rows": records,
    })


@app.get("/api/case/{case_number}")
def case_detail(case_number: str):
    df = _require_data()
    sub = df[df["case_number"] == case_number]
    if sub.empty:
        raise HTTPException(status_code=404, detail="Case not found.")
    row = sub.iloc[0].to_dict()
    for k, v in list(row.items()):
        if isinstance(v, pd.Timestamp):
            row[k] = v.strftime("%d-%b-%Y") if not pd.isna(v) else None
    return _json({"case": row, "labels": FIELD_LABELS})


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
@app.post("/api/export/excel")
def export_excel_route(payload: dict = Body(default={})):
    df = _require_data()
    filters = payload.get("filters") or {}
    fdf = analytics.apply_filters(df, filters)
    xbytes = export_excel.build_excel_report(fdf, filters, SESSION.meta)
    return StreamingResponse(
        io.BytesIO(xbytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=SW_MIS_Report.xlsx"},
    )


@app.post("/api/export/pdf")
def export_pdf_route(payload: dict = Body(default={})):
    df = _require_data()
    filters = payload.get("filters") or {}
    fdf = analytics.apply_filters(df, filters)
    pbytes = export_pdf.build_full_pdf_report(fdf, filters, SESSION.meta)
    return StreamingResponse(
        io.BytesIO(pbytes), media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=SW_MIS_Full_Report.pdf"},
    )


@app.post("/api/export/pdf-onepager")
def export_pdf_onepager_route(payload: dict = Body(default={})):
    df = _require_data()
    filters = payload.get("filters") or {}
    fdf = analytics.apply_filters(df, filters)
    pbytes = export_pdf.build_executive_onepager(fdf, filters, SESSION.meta)
    return StreamingResponse(
        io.BytesIO(pbytes), media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=SW_MIS_Executive_OnePager.pdf"},
    )


# ---------------------------------------------------------------------------
# Admin auth (lightweight local-app access gate - see engine.CONFIG["admin_passcode"])
# ---------------------------------------------------------------------------
@app.get("/api/auth/status")
def auth_status():
    return _json({"is_admin": SESSION.is_admin})


@app.post("/api/auth/unlock")
def auth_unlock(payload: dict = Body(default={})):
    passcode = str(payload.get("passcode") or "")
    if passcode != engine.CONFIG.get("admin_passcode"):
        raise HTTPException(status_code=401, detail="Incorrect passcode.")
    SESSION.is_admin = True
    return _json({"is_admin": True})


@app.post("/api/auth/lock")
def auth_lock():
    SESSION.is_admin = False
    return _json({"is_admin": False})


# ---------------------------------------------------------------------------
# LIST management (Project / Month / Year dropdowns + Category -> M_Category)
# ---------------------------------------------------------------------------
def _list_state_public():
    ls = SESSION.list_state
    return {
        "projects": ls.get("projects", []),
        "months": ls.get("months", []),
        "years": ls.get("years", []),
        "category_rows": ls.get("category_rows", []),
        "source": ls.get("source", ""),
        "is_admin": SESSION.is_admin,
    }


@app.get("/api/lists")
def get_lists():
    return _json(_list_state_public())


@app.post("/api/lists/upload")
async def upload_list(file: UploadFile = File(...)):
    _require_admin()
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx or .xls file.")
    content = await file.read()
    try:
        new_state = engine.parse_list_workbook(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    with SESSION.lock:
        SESSION.list_state = new_state
        _recompute_df()
    return _json(_list_state_public())


@app.post("/api/lists/update")
def update_lists(payload: dict = Body(default={})):
    _require_admin()
    try:
        new_state = engine.list_state_from_rows(
            projects=payload.get("projects", []),
            months=payload.get("months", []),
            years=payload.get("years", []),
            category_rows=payload.get("category_rows", []),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not apply list changes: {e}")
    with SESSION.lock:
        SESSION.list_state = new_state
        _recompute_df()
    return _json(_list_state_public())


def mount_frontend(static_dir: str):
    p = Path(static_dir)
    if p.exists():
        app.mount("/", StaticFiles(directory=str(p), html=True), name="frontend")
