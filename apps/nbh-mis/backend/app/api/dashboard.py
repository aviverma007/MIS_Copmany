from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_filters, require_dataset
from app.services import dashboard_service
from app.services.filters import Filters

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(f: Filters = Depends(get_filters)):
    df, meta = require_dataset()
    return {
        "meta": {
            "filename": meta.filename,
            "uploaded_at": meta.uploaded_at.isoformat(),
            "total_records": meta.total_records,
            "as_of": meta.as_of,
        },
        "dataset": dashboard_service.dataset_summary(df, f),
        "kpis": dashboard_service.kpi_summary(df, f),
        "rag_scorecard": dashboard_service.rag_scorecard(df, f),
        "insights": dashboard_service.management_insights(df, f),
        "top_bottom": dashboard_service.top_bottom(df, f),
    }


@router.get("/trends")
def trends(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    from app.services import report_service
    return report_service.trend_report(df, f)


@router.get("/ageing")
def ageing(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return dashboard_service.ageing_distribution(df, f)


@router.get("/insights")
def insights(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return {"insights": dashboard_service.management_insights(df, f)}
