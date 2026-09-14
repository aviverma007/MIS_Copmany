from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_filters, require_dataset
from app.services import report_service
from app.services.filters import Filters

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports/open-cases")
def open_cases(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return report_service.open_cases_report(df, f)


@router.get("/reports/project-wise")
def project_wise(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return report_service.project_wise_report(df, f)


@router.get("/reports/category-wise")
def category_wise(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return report_service.category_wise_report(df, f)


@router.get("/reports/management-category-wise")
def management_category_wise(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return report_service.management_category_report(df, f)


@router.get("/reports/assignee-wise")
def assignee_wise(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return report_service.assignee_report(df, f)


@router.get("/reports/priority-wise")
def priority_wise(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return report_service.priority_report(df, f)


@router.get("/reports/escalation-wise")
def escalation_wise(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return report_service.escalation_report(df, f)


@router.get("/reports/source-wise")
def source_wise(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    return report_service.source_report(df, f)


@router.get("/reports/rating")
def rating(f: Filters = Depends(get_filters)):
    df, _ = require_dataset()
    result = report_service.rating_report(df, f)
    if result is None:
        raise HTTPException(status_code=404, detail="No Rating column found in the uploaded data.")
    return result


@router.get("/tickets")
def tickets(
    f: Filters = Depends(get_filters),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("ageing_days"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
):
    df, _ = require_dataset()
    return report_service.tickets_list(df, f, page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir)


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str):
    df, _ = require_dataset()
    result = report_service.ticket_detail(df, ticket_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return result


@router.get("/master/projects")
def master_projects():
    df, _ = require_dataset()
    projects = sorted(df["society_name"].dropna().unique().tolist())
    return {"projects": ["ALL"] + projects}


@router.get("/master/categories")
def master_categories():
    df, _ = require_dataset()
    categories = sorted(df["category_raw"].dropna().unique().tolist())
    return {"categories": ["ALL"] + categories}


@router.get("/master/management-categories")
def master_management_categories():
    from app import config
    return {"management_categories": ["ALL"] + config.MANAGEMENT_CATEGORY_HEADS}


@router.get("/master/assignees")
def master_assignees():
    df, _ = require_dataset()
    if "current_assignee" not in df.columns:
        return {"assignees": ["ALL"]}
    assignees = sorted(df["current_assignee"].dropna().unique().tolist())
    return {"assignees": ["ALL"] + assignees}


@router.get("/master/statuses")
def master_statuses():
    df, _ = require_dataset()
    statuses = sorted(df["status_raw"].dropna().unique().tolist())
    return {"statuses": ["ALL"] + statuses}


@router.get("/master/sources")
def master_sources():
    df, _ = require_dataset()
    if "source" not in df.columns:
        return {"sources": ["ALL"]}
    sources = sorted(df["source"].dropna().unique().tolist())
    return {"sources": ["ALL"] + sources}


@router.get("/master/priorities")
def master_priorities():
    from app import config
    return {"priorities": ["ALL"] + config.PRIORITY_ORDER}


@router.get("/master/ageing-slabs")
def master_ageing_slabs():
    from app import config
    return {"ageing_slabs": ["ALL"] + config.AGEING_BUCKET_ORDER}


@router.get("/master/years")
def master_years():
    df, _ = require_dataset()
    years = sorted([int(y) for y in df["year"].dropna().unique().tolist()])
    return {"years": years}
