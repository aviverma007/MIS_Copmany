from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_filters, require_dataset
from app.models import actions as actions_model
from app.services import excel_export_service, pdf_export_service
from app.services.filters import Filters

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/excel")
def export_excel(f: Filters = Depends(get_filters)):
    df, meta = require_dataset()
    content = excel_export_service.build_export_workbook(df, meta, f, meta.data_quality, actions_model.list_actions())
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=NBH_MIS_Export_{ts}.xlsx"},
    )


@router.get("/pdf")
def export_pdf(f: Filters = Depends(get_filters)):
    df, meta = require_dataset()
    content = pdf_export_service.build_pdf(df, meta, f)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=NBH_MIS_Dashboard_{ts}.pdf"},
    )
