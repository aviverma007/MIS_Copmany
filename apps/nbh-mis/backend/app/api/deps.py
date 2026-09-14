from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Query

from app.services.filters import Filters
from app.store import store


def get_filters(
    year: Optional[int] = Query(None),
    month: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    management_category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    ageing_slab: Optional[str] = Query(None),
    escalation_level: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    management_status: Optional[str] = Query(None, description="OPEN or CLOSED (derived management status, not raw status)"),
) -> Filters:
    return Filters(
        year=year, month=month, project=project, status=status, priority=priority,
        category=category, management_category=management_category, source=source,
        assignee=assignee, ageing_slab=ageing_slab, escalation_level=escalation_level,
        date_from=date_from, date_to=date_to, search=search, management_status=management_status,
    )


def require_dataset():
    if not store.is_loaded():
        raise HTTPException(
            status_code=409,
            detail="No dataset has been uploaded yet. Please upload an NBH Excel file first.",
        )
    return store.get()
