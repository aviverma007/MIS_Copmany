from __future__ import annotations

import os
import re
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app import config
from app.api.deps import require_dataset
from app.services import analytics_service, cleaning_service, excel_export_service, excel_service
from app.store import DatasetMeta, store

router = APIRouter(prefix="/api", tags=["upload"])


def _safe_filename(name: str) -> str:
    name = os.path.basename(name or "upload")
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
    return name[:200]


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = _safe_filename(file.filename)
    content = await file.read()

    size_mb = len(content) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File exceeds the {config.MAX_UPLOAD_SIZE_MB} MB upload limit.")
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        raw_df, sheet_used, all_sheets = excel_service.load_workbook(filename, content)
    except excel_service.UnsupportedFileError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except excel_service.EmptyDataError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except excel_service.CorruptFileError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        cleaned_df, dq_report = cleaning_service.normalize_and_clean(raw_df)
    except cleaning_service.MissingColumnsError as e:
        raise HTTPException(
            status_code=422,
            detail=(
                f"The uploaded file is missing required column(s): {', '.join(e.missing)}. "
                "Please check the sheet headers against the sample template."
            ),
        )

    try:
        enriched_df, analytics_meta = analytics_service.enrich(cleaned_df)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail="Could not process the data: invalid or inconsistent values found.")

    dq_report.unmapped_categories = analytics_meta["unmapped_categories"]
    dq_report.unmapped_statuses = analytics_meta["unmapped_statuses"]
    if dq_report.unmapped_categories:
        dq_report.notes.append(
            f"{len(dq_report.unmapped_categories)} categories were not in the management mapping table "
            "and were classified as 'Others/Misc'."
        )

    as_of = analytics_meta["as_of"]
    date_min = enriched_df["open_date"].min()
    date_max = enriched_df["open_date"].max()

    meta = DatasetMeta(
        filename=filename,
        uploaded_at=datetime.now(),
        sheet_used=sheet_used,
        all_sheets=all_sheets,
        total_records=int(len(enriched_df)),
        date_range=(
            date_min.strftime("%d-%b-%Y") if pd_notna(date_min) else None,
            date_max.strftime("%d-%b-%Y") if pd_notna(date_max) else None,
        ),
        num_projects=int(enriched_df["society_name"].nunique()) if "society_name" in enriched_df else 0,
        num_categories=int(enriched_df["category_raw"].nunique()) if "category_raw" in enriched_df else 0,
        num_open=int((enriched_df["management_status"] == "OPEN").sum()),
        num_closed=int((enriched_df["management_status"] == "CLOSED").sum()),
        data_quality=dq_report.to_dict(),
        unmapped_categories=dq_report.unmapped_categories,
        unmapped_statuses=dq_report.unmapped_statuses,
        as_of=as_of.strftime("%d-%b-%Y"),
    )
    store.set(enriched_df, meta)

    return {
        "message": "File uploaded and processed successfully.",
        "filename": meta.filename,
        "uploaded_at": meta.uploaded_at.isoformat(),
        "sheet_used": meta.sheet_used,
        "all_sheets": meta.all_sheets,
        "total_records": meta.total_records,
        "date_range": {"from": meta.date_range[0], "to": meta.date_range[1]},
        "num_projects": meta.num_projects,
        "num_categories": meta.num_categories,
        "num_open": meta.num_open,
        "num_closed": meta.num_closed,
        "data_quality": meta.data_quality,
        "as_of": meta.as_of,
    }


def pd_notna(v) -> bool:
    import pandas as pd
    return pd.notna(v)


@router.get("/data-quality")
def get_data_quality():
    _, meta = require_dataset()
    return meta.data_quality


@router.get("/upload/template")
def download_template():
    content = excel_export_service.build_sample_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=NBH_Sample_Template.xlsx"},
    )
